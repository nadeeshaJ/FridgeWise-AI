"""Generate synthetic user fridge inventories → user_fridge_inventory.csv"""

from __future__ import annotations

import random
from datetime import timedelta
from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path
from src.cold_start.mappings import COLD_START_MAPPINGS
from src.preprocessing.ingredient_utils import clean_ingredient_name, compute_expiry_priority_score


def _top_recipe_ingredients(recipes_df: pd.DataFrame, limit: int = 200) -> list[str]:
    counts: dict[str, int] = {}
    for raw in recipes_df["cleaned_ingredients"]:
        for ing in str(raw).split("|"):
            if ing:
                counts[ing] = counts.get(ing, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])[:limit]]


def build_fridge_inventory(
    recipes_df: pd.DataFrame,
    products_df: pd.DataFrame,
    output_path: Path,
    num_users: int,
    min_items: int,
    max_items: int,
    reference_date: str,
    seed: int = 42,
) -> pd.DataFrame:
    random.seed(seed)
    ref = pd.to_datetime(reference_date).normalize()
    common = _top_recipe_ingredients(recipes_df)
    cold_start = list(COLD_START_MAPPINGS.keys())

    barcode_products = products_df.dropna(subset=["barcode", "generic_ingredient_name"]).to_dict("records")
    rows: list[dict] = []
    inventory_id = 1

    user_ids = list(range(10001, 10001 + num_users))

    for user_id in user_ids:
        n_items = random.randint(min_items, max_items)
        pool = list(common)
        random.shuffle(pool)
        chosen = pool[: max(0, n_items - 3)]

        # Ensure some cold-start ingredients
        chosen.extend(random.sample(cold_start, k=min(2, len(cold_start))))
        chosen = list(dict.fromkeys(chosen))[:n_items]

        for ingredient in chosen:
            cleaned = clean_ingredient_name(ingredient)
            days = random.choice([0, 1, 2, 3, 5, 7, 10, 14, 21, 30])
            purchase = ref - timedelta(days=random.randint(1, 14))
            expiry = ref + timedelta(days=days)
            barcode = ""
            storage = random.choice(["fridge", "pantry", "freezer"])

            # Link ~30% of items to barcode products when ingredient matches
            matching_products = [
                p for p in barcode_products if p.get("generic_ingredient_name") == cleaned
            ]
            if matching_products and random.random() < 0.3:
                product = random.choice(matching_products)
                barcode = str(product["barcode"])
                ingredient = product.get("product_name") or ingredient

            rows.append(
                {
                    "inventory_id": inventory_id,
                    "user_id": user_id,
                    "ingredient_name": ingredient,
                    "cleaned_ingredient_name": cleaned,
                    "quantity": round(random.uniform(0.5, 3.0), 1),
                    "unit": random.choice(["cup", "g", "piece", "pack", "bottle"]),
                    "storage_type": storage,
                    "purchase_date": purchase.date(),
                    "expiry_date": expiry.date(),
                    "days_to_expiry": days,
                    "barcode": barcode,
                    "expiry_priority_score": compute_expiry_priority_score(days),
                }
            )
            inventory_id += 1

    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def main(
    recipes_df: pd.DataFrame | None = None,
    products_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    cfg = load_config()
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])
    inv_cfg = cfg["fridge_inventory"]

    if recipes_df is None:
        recipes_df = pd.read_csv(processed_dir / "clean_recipes.csv")
    if products_df is None:
        products_df = pd.read_csv(processed_dir / "clean_open_food_products.csv")

    return build_fridge_inventory(
        recipes_df=recipes_df,
        products_df=products_df,
        output_path=processed_dir / "user_fridge_inventory.csv",
        num_users=inv_cfg["num_users"],
        min_items=inv_cfg["min_items_per_user"],
        max_items=inv_cfg["max_items_per_user"],
        reference_date=inv_cfg["reference_date"],
    )


if __name__ == "__main__":
    result = main()
    print(f"Saved {len(result)} fridge inventory rows for {result['user_id'].nunique()} users")
