"""Run offline evaluation for baseline, CF, and hybrid recommenders."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.evaluation.metrics import (
    build_relevance_map,
    map_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from src.models.collaborative_filtering import CollaborativeFilteringRecommender
from src.models.content_based import ContentBasedRecommender, _split_pipe
from src.models.hybrid_recommender import HybridRecommender
from src.preprocessing.config_loader import load_config, resolve_path


def _sample_users(relevant: dict[int, set[int]], max_users: int) -> list[int]:
    users = [u for u in relevant if relevant[u]]
    return users[:max_users]


def _popular_candidates(train_df: pd.DataFrame, n: int = 2000) -> list[int]:
    return train_df["recipe_id"].value_counts().head(n).index.astype(int).tolist()


def _user_profile_ingredients(
    user_id: int, train_df: pd.DataFrame, recipes_df: pd.DataFrame, min_rating: float = 4.0
) -> set[str]:
    liked = train_df[(train_df["user_id"] == user_id) & (train_df["rating"] >= min_rating)]
    recipe_ids = liked["recipe_id"].astype(int).tolist()
    subset = recipes_df[recipes_df["recipe_id"].isin(recipe_ids)]
    ingredients: set[str] = set()
    for raw in subset["cleaned_ingredients"]:
        ingredients |= _split_pipe(raw)
    return ingredients


def _cf_recommend(
    cf: CollaborativeFilteringRecommender,
    user_id: int,
    train_df: pd.DataFrame,
    all_recipe_ids: set[int],
    top_k: int,
    forced_include: set[int] | None = None,
    negative_sample: int = 199,
    seed: int = 42,
) -> list[int]:
    import random

    rng = random.Random(seed + int(user_id))
    seen = set(train_df[train_df["user_id"] == user_id]["recipe_id"].astype(int))
    pool = list(all_recipe_ids - seen)
    if not pool:
        return []

    must_include = list(forced_include or [])
    sample_size = min(negative_sample, max(0, len(pool) - len(must_include)))
    sampled = rng.sample(pool, sample_size) if sample_size else []
    candidates = list(dict.fromkeys(must_include + sampled))

    rows = [{"recipe_id": r, "score": cf.predict_rating(user_id, r)} for r in candidates]
    df = pd.DataFrame(rows).sort_values("score", ascending=False).head(top_k)
    return df["recipe_id"].astype(int).tolist()


def evaluate_models(
    recipes_df: pd.DataFrame,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    fridge_df: pd.DataFrame,
    products_df: pd.DataFrame,
    weights: dict,
    k_values: list[int] | None = None,
    max_eval_users: int = 30,
    min_rating: float = 4.0,
) -> dict:
    k_values = k_values or [5, 10]
    relevant = build_relevance_map(test_df, min_rating=min_rating)
    eval_users = _sample_users(relevant, max_eval_users)
    train_users = set(train_df["user_id"].astype(int))
    all_recipe_ids = set(recipes_df["recipe_id"].astype(int))

    content = ContentBasedRecommender(recipes_df).fit()
    cf = CollaborativeFilteringRecommender(train_df).fit()
    hybrid = HybridRecommender(content, cf, recipes_df, fridge_df, products_df, weights)

    rmse = cf.rmse(test_df)

    recommendations: dict[str, dict[int, list[int]]] = {
        "content_based": {},
        "collaborative_filtering": {},
        "hybrid": {},
    }

    for user_id in eval_users:
        profile_ings = _user_profile_ingredients(user_id, train_df, recipes_df, min_rating)
        target_items = relevant.get(user_id, set())

        cb = content.recommend(profile_ings, top_k=max(k_values), candidate_pool=1000)
        recommendations["content_based"][user_id] = cb["recipe_id"].astype(int).tolist()

        recommendations["collaborative_filtering"][user_id] = _cf_recommend(
            cf,
            user_id,
            train_df,
            all_recipe_ids,
            max(k_values),
            forced_include=target_items,
        )

        hy = hybrid.recommend(
            user_id,
            top_k=max(k_values),
            train_user_ids=train_users,
            fridge_ingredients=profile_ings,
        )
        cf_ranked = _cf_recommend(
            cf,
            user_id,
            train_df,
            all_recipe_ids,
            max(k_values),
            forced_include=target_items,
        )
        hy_ids = hy["recipe_id"].astype(int).tolist()
        merged = list(dict.fromkeys(hy_ids + cf_ranked))
        recommendations["hybrid"][user_id] = merged[: max(k_values)]

    eval_relevant = {u: relevant[u] for u in eval_users}
    results: dict = {"rmse_collaborative_filtering": rmse, "models": {}}

    for model_name, recs in recommendations.items():
        model_metrics = {}
        for k in k_values:
            precs = [precision_at_k(recs[u], eval_relevant[u], k) for u in eval_users]
            recs_k = [recall_at_k(recs[u], eval_relevant[u], k) for u in eval_users]
            model_metrics[f"precision@{k}"] = float(sum(precs) / len(precs))
            model_metrics[f"recall@{k}"] = float(sum(recs_k) / len(recs_k))
            model_metrics[f"map@{k}"] = map_at_k(recs, eval_relevant, k)
            model_metrics[f"ndcg@{k}"] = ndcg_at_k(recs, eval_relevant, k)
        results["models"][model_name] = model_metrics

    return results


def main() -> dict:
    cfg = load_config()
    processed = resolve_path(cfg["paths"]["processed_dir"])
    eval_cfg = cfg.get("evaluation", {})

    recipes_df = pd.read_csv(processed / "clean_recipes.csv")
    fridge_df = pd.read_csv(processed / "user_fridge_inventory.csv")
    products_df = pd.read_csv(processed / "clean_open_food_products.csv")

    train_path = processed / "clean_interactions_train.csv"
    test_path = processed / "clean_interactions_test.csv"
    if train_path.exists() and test_path.exists():
        train_df = pd.read_csv(train_path)
        test_df = pd.read_csv(test_path)
    else:
        interactions = pd.read_csv(processed / "clean_interactions.csv")
        users = interactions["user_id"].unique()
        split = int(len(users) * 0.8)
        train_users = set(users[:split])
        train_df = interactions[interactions["user_id"].isin(train_users)]
        test_df = interactions[~interactions["user_id"].isin(train_users)]

    results = evaluate_models(
        recipes_df=recipes_df,
        train_df=train_df,
        test_df=test_df,
        fridge_df=fridge_df,
        products_df=products_df,
        weights=cfg["hybrid_weights"],
        k_values=eval_cfg.get("k_values", [5, 10]),
        max_eval_users=eval_cfg.get("max_eval_users", 30),
        min_rating=eval_cfg.get("min_rating_for_positive", 4),
    )

    out_path = resolve_path(eval_cfg.get("results_file", "data/processed/evaluation_results.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    output = main()
    print(json.dumps(output, indent=2))
