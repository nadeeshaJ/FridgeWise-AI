"""Run the full dataset build pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.download_data import download_all
from src.preprocessing.clean_interaction_splits import main as clean_splits
from src.preprocessing.build_database import main as build_db
from src.preprocessing.build_fridge_inventory import main as build_fridge
from src.preprocessing.build_integrated_dataset import main as build_integrated
from src.preprocessing.clean_expiry import main as clean_expiry
from src.preprocessing.clean_interactions import main as clean_interactions
from src.preprocessing.clean_recipes import main as clean_recipes
from src.preprocessing.config_loader import load_config, resolve_path


from src.preprocessing.fetch_open_food_facts import main as fetch_off


def main() -> None:
    cfg = load_config()
    raw_dir = resolve_path(cfg["paths"]["raw_dir"])
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FridgeWise AI - Dataset Build Pipeline")
    print("=" * 60)

    print("\n[1/8] Checking / downloading raw datasets...")
    download_all(raw_dir)

    recipes_path = raw_dir / cfg["food_com"]["recipes_file"]
    interactions_path = raw_dir / cfg["food_com"]["interactions_file"]
    if not recipes_path.exists() or not interactions_path.exists():
        raise FileNotFoundError(
            f"Missing Food.com files in {raw_dir}.\n"
            "Download from https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions"
        )

    print("\n[2/9] Cleaning recipes...")
    recipes_df = clean_recipes()
    print(f"      -> {len(recipes_df)} recipes")

    print("\n[3/9] Cleaning interactions...")
    interactions_df = clean_interactions(recipes_df)
    print(f"      -> {len(interactions_df)} interactions")

    print("\n[3b/9] Cleaning train/validation/test interaction splits...")
    splits = clean_splits(recipes_df)
    for name, sdf in splits.items():
        print(f"      -> {name}: {len(sdf)} interactions")

    print("\n[4/9] Cleaning expiry items...")
    expiry_df = clean_expiry()
    print(f"      -> {len(expiry_df)} expiry items")

    print("\n[5/9] Fetching Open Food Facts products...")
    products_df = fetch_off()
    print(f"      -> {len(products_df)} products")

    print("\n[6/9] Building user fridge inventories...")
    fridge_df = build_fridge(recipes_df, products_df)
    print(f"      -> {len(fridge_df)} inventory rows ({fridge_df['user_id'].nunique()} users)")

    print("\n[7/9] Building integrated datasets...")
    features_df, final_df = build_integrated()
    print(f"      -> {len(features_df)} recipe-ingredient features")
    print(f"      -> {len(final_df)} final recommendation rows")

    print("\n[8/9] Writing SQLite database...")
    db_path = build_db()
    print(f"      -> {db_path}")

    print("\n" + "=" * 60)
    print("Done! Output files:")
    for name in [
        "clean_recipes.csv",
        "clean_interactions.csv",
        "clean_expiry_items.csv",
        "clean_open_food_products.csv",
        "user_fridge_inventory.csv",
        "recipe_ingredient_features.csv",
        "final_recommendation_dataset.csv",
    ]:
        path = processed_dir / name
        size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        print(f"  {path} ({size_mb:.2f} MB)")
    print(f"  {db_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
