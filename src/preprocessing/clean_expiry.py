"""Clean Food Expiry Tracker dataset → clean_expiry_items.csv."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path
from src.preprocessing.ingredient_utils import clean_ingredient_name, compute_expiry_priority_score

# One-hot columns in prekshad2166/food-expiry-tracker Kaggle dataset
ITEM_COLUMNS: dict[str, tuple[str, list[str]]] = {
    "item_beverage": ("beverage", ["orange juice", "milk", "water", "soda"]),
    "item_dairy": ("dairy", ["milk", "cheese", "yogurt", "butter"]),
    "item_fruit": ("fruit", ["apple", "banana", "tomato", "orange"]),
    "item_grain": ("grain", ["rice", "pasta", "bread", "cereal"]),
    "item_meat": ("meat", ["chicken", "beef", "pork", "fish"]),
    "item_snack": ("snack", ["chips", "crackers", "cereal", "cookies"]),
    "item_vegetable": ("vegetable", ["onion", "carrot", "lettuce", "pepper"]),
}

STORAGE_COLUMNS = {
    "storage_fridge": "fridge",
    "storage_freezer": "freezer",
    "storage_pantry": "pantry",
}

# Typical max shelf life (days) used to denormalise days_until_expiry (0–1 fraction)
SHELF_LIFE_DAYS: dict[str, int] = {
    "beverage": 14,
    "dairy": 10,
    "fruit": 7,
    "grain": 90,
    "meat": 5,
    "snack": 120,
    "vegetable": 10,
}


def _is_one_hot_schema(df: pd.DataFrame) -> bool:
    return all(col in df.columns for col in ITEM_COLUMNS)


def _bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def _row_category_and_ingredient(row: pd.Series, row_idx: int) -> tuple[str, str]:
    for col, (category, samples) in ITEM_COLUMNS.items():
        if _bool_value(row.get(col)):
            ingredient = samples[row_idx % len(samples)]
            return category, ingredient
    return "unknown", "mixed food item"


def _row_storage(row: pd.Series) -> str:
    for col, storage in STORAGE_COLUMNS.items():
        if col in row and _bool_value(row.get(col)):
            return storage
    return "fridge"


def _clean_one_hot_expiry(df: pd.DataFrame, reference_date: str) -> pd.DataFrame:
    ref = pd.to_datetime(reference_date).normalize()
    rows: list[dict] = []

    for idx, row in df.iterrows():
        category, ingredient = _row_category_and_ingredient(row, int(idx))
        storage = _row_storage(row)
        shelf_days = SHELF_LIFE_DAYS.get(category, 14)

        fraction = float(row.get("days_until_expiry", 0.5) or 0.5)
        fraction = max(0.0, min(1.0, fraction))
        days_to_expiry = max(0, round(fraction * shelf_days))

        expiry_date = (ref + timedelta(days=days_to_expiry)).date()
        purchase_date = (ref - timedelta(days=max(1, shelf_days - days_to_expiry))).date()

        used = row.get("used_before_expiry", "")
        if str(used) in {"1", "1.0", "True", "true"}:
            consumed = "consumed"
        elif str(used) in {"0", "0.0", "False", "false"}:
            consumed = "wasted"
        else:
            consumed = "unknown"

        cleaned = clean_ingredient_name(ingredient)
        rows.append(
            {
                "ingredient_name": ingredient,
                "cleaned_ingredient_name": cleaned,
                "category": category,
                "storage_type": storage,
                "purchase_date": purchase_date,
                "expiry_date": expiry_date,
                "days_to_expiry": days_to_expiry,
                "consumed_or_wasted": consumed,
                "expiry_priority_score": compute_expiry_priority_score(days_to_expiry),
            }
        )

    out = pd.DataFrame(rows)
    out.insert(0, "expiry_item_id", range(1, len(out) + 1))
    return out


def _find_expiry_file(raw_dir: Path, configured: str | None) -> Path:
    if configured:
        path = raw_dir / configured
        if path.exists():
            return path
    for name in ("food_expiry_tracker.csv", "food-expiry-tracker.csv"):
        path = raw_dir / name
        if path.exists():
            return path
    for path in raw_dir.glob("*.csv"):
        if "expiry" in path.name.lower():
            return path
    raise FileNotFoundError(
        f"No expiry dataset CSV found in {raw_dir}. "
        "Download from https://www.kaggle.com/datasets/prekshad2166/food-expiry-tracker"
    )


def clean_expiry(raw_path: Path, output_path: Path, reference_date: str) -> pd.DataFrame:
    df = pd.read_csv(raw_path)

    if _is_one_hot_schema(df):
        out = _clean_one_hot_expiry(df, reference_date)
    else:
        raise ValueError(
            f"Unsupported expiry schema in {raw_path.name}. "
            f"Expected one-hot item columns: {list(ITEM_COLUMNS)}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def main() -> pd.DataFrame:
    cfg = load_config()
    raw_dir = resolve_path(cfg["paths"]["raw_dir"])
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])
    raw_path = _find_expiry_file(raw_dir, cfg["expiry"].get("filename"))
    output_path = processed_dir / "clean_expiry_items.csv"
    return clean_expiry(raw_path, output_path, cfg["fridge_inventory"]["reference_date"])


if __name__ == "__main__":
    result = main()
    print(f"Saved {len(result)} expiry items to clean_expiry_items.csv")
