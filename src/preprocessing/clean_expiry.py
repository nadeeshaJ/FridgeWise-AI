"""Clean Food Expiry Tracker dataset → clean_expiry_items.csv"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path
from src.preprocessing.ingredient_utils import clean_ingredient_name, compute_expiry_priority_score


COLUMN_ALIASES: dict[str, list[str]] = {
    "ingredient_name": [
        "ingredient_name",
        "food_item",
        "item_name",
        "food_name",
        "product_name",
        "name",
        "item",
    ],
    "category": ["category", "food_category", "item_category", "type"],
    "storage_type": ["storage_type", "storage_method", "storage", "storage_location"],
    "purchase_date": ["purchase_date", "buy_date", "date_purchased", "purchase"],
    "expiry_date": ["expiry_date", "expiration_date", "expire_date", "best_before", "use_by_date"],
    "consumed_or_wasted": [
        "consumed_or_wasted",
        "used_before_expiry",
        "consumed",
        "status",
        "outcome",
        "wasted",
    ],
}


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    lower_map = {c.lower().strip(): c for c in df.columns}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    for col in df.columns:
        norm = col.lower().strip().replace(" ", "_")
        for alias in aliases:
            if alias.replace("_", "") in norm.replace("_", ""):
                return col
    return None


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for target, aliases in COLUMN_ALIASES.items():
        found = _find_column(df, aliases)
        if found and found != target:
            rename_map[found] = target
    return df.rename(columns=rename_map)


def _find_expiry_file(raw_dir: Path, configured: str | None) -> Path:
    if configured:
        path = raw_dir / configured
        if path.exists():
            return path
    candidates = list(raw_dir.glob("*.csv"))
    for path in candidates:
        name = path.name.lower()
        if "expiry" in name or "food_expiry" in name or "food-expiry" in name:
            return path
    if candidates:
        # Fallback: any csv that isn't food.com
        for path in candidates:
            if "raw_recipes" not in path.name.lower() and "raw_interactions" not in path.name.lower():
                return path
    raise FileNotFoundError(
        f"No expiry dataset CSV found in {raw_dir}. "
        "Download from https://www.kaggle.com/datasets/prekshad2166/food-expiry-tracker"
    )


def clean_expiry(
    raw_path: Path,
    output_path: Path,
    reference_date: str,
) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    df = _rename_columns(df)

    if "ingredient_name" not in df.columns:
        raise ValueError(f"Could not find ingredient column in {raw_path.name}. Columns: {list(df.columns)}")

    ref = pd.to_datetime(reference_date).normalize()

    if "purchase_date" in df.columns:
        df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce").dt.date
    else:
        df["purchase_date"] = None

    if "expiry_date" in df.columns:
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce").dt.date
    else:
        # Synthesise expiry from shelf-life if only purchase date exists
        shelf_col = _find_column(df, ["shelf_life", "shelf_life_days", "days_to_expiry"])
        if shelf_col and "purchase_date" in df.columns:
            df["expiry_date"] = (
                pd.to_datetime(df["purchase_date"], errors="coerce")
                + pd.to_timedelta(pd.to_numeric(df[shelf_col], errors="coerce").fillna(7), unit="D")
            ).dt.date
        else:
            df["expiry_date"] = None

    df["cleaned_ingredient_name"] = df["ingredient_name"].astype(str).apply(clean_ingredient_name)
    df["days_to_expiry"] = (
        pd.to_datetime(df["expiry_date"], errors="coerce") - ref
    ).dt.days
    df["days_to_expiry"] = df["days_to_expiry"].fillna(30).astype(int)
    df["expiry_priority_score"] = df["days_to_expiry"].apply(compute_expiry_priority_score)

    if "category" not in df.columns:
        df["category"] = "unknown"
    if "storage_type" not in df.columns:
        df["storage_type"] = "fridge"
    if "consumed_or_wasted" not in df.columns:
        df["consumed_or_wasted"] = "unknown"

    df = df.reset_index(drop=True)
    df["expiry_item_id"] = df.index + 1

    out = df[
        [
            "expiry_item_id",
            "ingredient_name",
            "cleaned_ingredient_name",
            "category",
            "storage_type",
            "purchase_date",
            "expiry_date",
            "days_to_expiry",
            "consumed_or_wasted",
            "expiry_priority_score",
        ]
    ]
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
