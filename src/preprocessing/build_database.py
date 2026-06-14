"""Load processed CSVs into SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path

TABLE_FILES = [
    ("recipes", "clean_recipes.csv"),
    ("interactions", "clean_interactions.csv"),
    ("expiry_items", "clean_expiry_items.csv"),
    ("open_food_products", "clean_open_food_products.csv"),
    ("user_fridge_inventory", "user_fridge_inventory.csv"),
    ("recipe_ingredient_features", "recipe_ingredient_features.csv"),
    ("final_recommendation_dataset", "final_recommendation_dataset.csv"),
]


def build_database(processed_dir: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        for table_name, filename in TABLE_FILES:
            csv_path = processed_dir / filename
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing processed file: {csv_path}")
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, conn, index=False, if_exists="replace")

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_recipes_id ON recipes(recipe_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_recipe ON interactions(recipe_id);
            CREATE INDEX IF NOT EXISTS idx_expiry_ingredient ON expiry_items(cleaned_ingredient_name);
            CREATE INDEX IF NOT EXISTS idx_products_ingredient ON open_food_products(generic_ingredient_name);
            CREATE INDEX IF NOT EXISTS idx_fridge_user ON user_fridge_inventory(user_id);
            CREATE INDEX IF NOT EXISTS idx_features_recipe ON recipe_ingredient_features(recipe_id);
            CREATE INDEX IF NOT EXISTS idx_final_user ON final_recommendation_dataset(user_id);
            CREATE INDEX IF NOT EXISTS idx_final_recipe ON final_recommendation_dataset(recipe_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


def main() -> Path:
    cfg = load_config()
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])
    db_path = resolve_path(cfg["paths"]["db_path"])
    build_database(processed_dir, db_path)
    return db_path


if __name__ == "__main__":
    path = main()
    print(f"SQLite database saved to {path}")
