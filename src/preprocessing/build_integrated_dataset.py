"""Build recipe_ingredient_features and final_recommendation_dataset."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path
from src.preprocessing.ingredient_utils import clean_ingredient_name, get_cold_start_substitutes


def _split_pipe(value: str) -> list[str]:
    if not value or (isinstance(value, float) and np.isnan(value)):
        return []
    return [x for x in str(value).split("|") if x]


def _infer_ingredient_category(name: str) -> str:
    dairy = {"milk", "cheese", "yogurt", "butter", "cream"}
    protein = {"chicken", "beef", "pork", "egg", "tofu", "tempeh", "fish", "beans"}
    grain = {"rice", "pasta", "bread", "cereal", "flour"}
    produce = {"tomato", "onion", "garlic", "potato", "carrot", "pepper", "lettuce", "banana"}
    if name in dairy:
        return "dairy"
    if name in protein:
        return "protein"
    if name in grain:
        return "grain"
    if name in produce:
        return "produce"
    return "other"


def build_recipe_ingredient_features(
    recipes_df: pd.DataFrame,
    expiry_df: pd.DataFrame,
    products_df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    expiry_lookup = (
        expiry_df.groupby("cleaned_ingredient_name")["expiry_priority_score"].mean().to_dict()
    )
    nutrition_lookup = (
        products_df.groupby("generic_ingredient_name")["nutrition_score"].mean().to_dict()
    )

    rows: list[dict] = []
    for _, recipe in recipes_df.iterrows():
        recipe_id = recipe["recipe_id"]
        for ing in _split_pipe(recipe["cleaned_ingredients"]):
            substitutes = get_cold_start_substitutes(ing)
            match_keys = [ing] + substitutes
            expiry_scores = [expiry_lookup[k] for k in match_keys if k in expiry_lookup]
            nutrition_scores = [nutrition_lookup[k] for k in match_keys if k in nutrition_lookup]

            rows.append(
                {
                    "recipe_id": recipe_id,
                    "ingredient_name": ing,
                    "cleaned_ingredient_name": ing,
                    "ingredient_category": _infer_ingredient_category(ing),
                    "is_expiry_matched": int(bool(expiry_scores)),
                    "avg_expiry_priority_score": float(np.mean(expiry_scores)) if expiry_scores else 0.0,
                    "avg_nutrition_score": float(np.mean(nutrition_scores)) if nutrition_scores else 0.5,
                }
            )

    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def _normalize_series(s: pd.Series) -> pd.Series:
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


def build_final_recommendation_dataset(
    recipes_df: pd.DataFrame,
    interactions_df: pd.DataFrame,
    fridge_df: pd.DataFrame,
    features_df: pd.DataFrame,
    products_df: pd.DataFrame,
    output_path: Path,
    max_users: int,
    max_recipes_per_user: int,
    min_rating_for_positive: int,
    hybrid_weights: dict,
) -> pd.DataFrame:
    recipe_map = recipes_df.set_index("recipe_id")
    feature_group = features_df.groupby("recipe_id")

    # Simple CF: user mean rating as predicted_rating proxy (full SVD comes in modelling phase)
    user_mean = interactions_df.groupby("user_id")["rating"].mean().to_dict()
    global_mean = interactions_df["rating"].mean()

    user_interactions = (
        interactions_df.sort_values(["user_id", "rating"], ascending=[True, False])
        .groupby("user_id", group_keys=False)
        .head(max_recipes_per_user)
    )

    sample_users = user_interactions["user_id"].unique()[:max_users]
    user_interactions = user_interactions[user_interactions["user_id"].isin(sample_users)]

    product_allergens: dict[str, str] = {}
    for _, row in products_df.iterrows():
        product_allergens[row["generic_ingredient_name"]] = str(row.get("allergens") or "")

    rows: list[dict] = []

    for user_id in sample_users:
        fridge_items = fridge_df[fridge_df["user_id"] == user_id]
        fridge_ings = set(fridge_items["cleaned_ingredient_name"])
        fridge_expiry = dict(
            zip(fridge_items["cleaned_ingredient_name"], fridge_items["expiry_priority_score"])
        )

        user_rows = user_interactions[user_interactions["user_id"] == user_id]
        is_cold_start_user = user_id not in user_mean or len(user_rows) == 0

        for _, inter in user_rows.iterrows():
            recipe_id = int(inter["recipe_id"])
            if recipe_id not in recipe_map.index:
                continue

            recipe = recipe_map.loc[recipe_id]
            recipe_ings = set(_split_pipe(recipe["cleaned_ingredients"]))
            if not recipe_ings:
                continue

            matched = recipe_ings & fridge_ings
            missing = recipe_ings - fridge_ings
            ingredient_match_score = len(matched) / len(recipe_ings)

            expiry_scores = [fridge_expiry[i] for i in matched if i in fridge_expiry]
            expiry_priority_score = float(max(expiry_scores)) if expiry_scores else 0.0

            if recipe_id in feature_group.groups:
                feat = feature_group.get_group(recipe_id)
                nutrition_score = float(feat["avg_nutrition_score"].mean())
            else:
                nutrition_score = 0.5

            predicted_rating = user_mean.get(user_id, global_mean)
            recipe_interaction_count = int(
                interactions_df[interactions_df["recipe_id"] == recipe_id].shape[0]
            )
            cold_start_flag = "|".join(
                filter(
                    None,
                    [
                        "new_user" if is_cold_start_user else "",
                        "new_recipe" if recipe_interaction_count < 5 else "",
                    ],
                )
            ) or "none"

            w = hybrid_weights
            if is_cold_start_user:
                final_hybrid_score = (
                    w["cold_start_ingredient_match"] * ingredient_match_score
                    + w["cold_start_expiry"] * expiry_priority_score
                    + w["cold_start_nutrition"] * nutrition_score
                )
            else:
                pred_norm = (predicted_rating - 1) / 4.0
                final_hybrid_score = (
                    w["ingredient_match"] * ingredient_match_score
                    + w["predicted_rating"] * pred_norm
                    + w["expiry_priority"] * expiry_priority_score
                    + w["nutrition"] * nutrition_score
                )

            allergens = "|".join(
                sorted({product_allergens.get(i, "") for i in matched if product_allergens.get(i)})
            )

            rows.append(
                {
                    "user_id": user_id,
                    "recipe_id": recipe_id,
                    "recipe_name": recipe["recipe_name"],
                    "rating": inter["rating"],
                    "ingredients": recipe["ingredients"],
                    "cleaned_ingredients": recipe["cleaned_ingredients"],
                    "fridge_ingredients": "|".join(sorted(fridge_ings)),
                    "matched_ingredients": "|".join(sorted(matched)),
                    "missing_ingredients": "|".join(sorted(missing)),
                    "ingredient_match_score": round(ingredient_match_score, 4),
                    "expiry_priority_score": round(expiry_priority_score, 4),
                    "nutrition_score": round(nutrition_score, 4),
                    "predicted_rating": round(predicted_rating, 4),
                    "final_hybrid_score": round(final_hybrid_score, 4),
                    "tags": recipe["tags"],
                    "minutes": recipe["minutes"],
                    "dietary_tags": recipe["dietary_tags"],
                    "allergens": allergens,
                    "cold_start_flag": cold_start_flag,
                }
            )

    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = load_config()
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])

    recipes_df = pd.read_csv(processed_dir / "clean_recipes.csv")
    interactions_df = pd.read_csv(processed_dir / "clean_interactions.csv")
    expiry_df = pd.read_csv(processed_dir / "clean_expiry_items.csv")
    products_df = pd.read_csv(processed_dir / "clean_open_food_products.csv")
    fridge_df = pd.read_csv(processed_dir / "user_fridge_inventory.csv")

    features = build_recipe_ingredient_features(
        recipes_df,
        expiry_df,
        products_df,
        processed_dir / "recipe_ingredient_features.csv",
    )

    final = build_final_recommendation_dataset(
        recipes_df=recipes_df,
        interactions_df=interactions_df,
        fridge_df=fridge_df,
        features_df=features,
        products_df=products_df,
        output_path=processed_dir / "final_recommendation_dataset.csv",
        max_users=cfg["final_dataset"]["max_users"],
        max_recipes_per_user=cfg["final_dataset"]["max_recipes_per_user"],
        min_rating_for_positive=cfg["final_dataset"]["min_rating_for_positive"],
        hybrid_weights=cfg["hybrid_weights"],
    )
    return features, final


if __name__ == "__main__":
    feat, final = main()
    print(f"Saved {len(feat)} recipe-ingredient feature rows")
    print(f"Saved {len(final)} final recommendation rows")
