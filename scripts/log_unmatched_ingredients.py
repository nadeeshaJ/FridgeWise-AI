"""Log ingredients that fail to match across datasets."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cold_start import get_cold_start_substitutes, is_cold_start_ingredient
from src.preprocessing.config_loader import load_config, resolve_path
from src.preprocessing.ingredient_utils import clean_ingredient_name


def _recipe_ingredient_set(recipes_df: pd.DataFrame) -> set[str]:
    ingredients: set[str] = set()
    for raw in recipes_df["cleaned_ingredients"]:
        for ing in str(raw).split("|"):
            if ing:
                ingredients.add(ing)
    return ingredients


def build_unmatched_report(processed_dir: Path) -> pd.DataFrame:
    recipes = pd.read_csv(processed_dir / "clean_recipes.csv")
    products = pd.read_csv(processed_dir / "clean_open_food_products.csv")
    inventory = pd.read_csv(processed_dir / "user_fridge_inventory.csv")

    recipe_ings = _recipe_ingredient_set(recipes)
    product_ings = set(products["generic_ingredient_name"].dropna().astype(str))

    rows: list[dict] = []
    seen: set[str] = set()

    for raw in inventory["cleaned_ingredient_name"].dropna().astype(str).unique():
        if raw in seen:
            continue
        seen.add(raw)

        in_recipes = raw in recipe_ings
        in_products = raw in product_ings
        cold_start = is_cold_start_ingredient(raw)
        substitutes = get_cold_start_substitutes(raw)
        substitute_hits = [s for s in substitutes if s in recipe_ings]

        if in_recipes and in_products:
            status = "matched"
        elif cold_start and substitute_hits:
            status = "cold_start_resolved"
        elif in_recipes:
            status = "recipe_only"
        elif in_products:
            status = "product_only"
        else:
            status = "unmatched"

        rows.append(
            {
                "ingredient": raw,
                "status": status,
                "in_recipes": in_recipes,
                "in_products": in_products,
                "is_cold_start": cold_start,
                "substitutes": "|".join(substitutes),
                "substitute_recipe_hits": "|".join(substitute_hits),
            }
        )

    report = pd.DataFrame(rows).sort_values(["status", "ingredient"])
    return report


def main() -> None:
    cfg = load_config()
    processed = resolve_path(cfg["paths"]["processed_dir"])
    report = build_unmatched_report(processed)

    output = processed / "unmatched_ingredients_report.csv"
    report.to_csv(output, index=False)

    summary = report["status"].value_counts()
    print(f"Saved {len(report)} rows to {output}")
    print("\nStatus summary:")
    for status, count in summary.items():
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
