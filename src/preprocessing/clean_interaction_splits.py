"""Clean Food.com pre-split interaction files for evaluation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path

SPLIT_FILES = {
    "train": "interactions_train.csv",
    "validation": "interactions_validation.csv",
    "test": "interactions_test.csv",
}


def clean_split_file(raw_path: Path, valid_recipe_ids: set[int], output_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    df = df.dropna(subset=["user_id", "recipe_id", "rating"])
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df[(df["rating"] >= 1) & (df["rating"] <= 5)]
    df["recipe_id"] = df["recipe_id"].astype(int)
    df["user_id"] = df["user_id"].astype(int)
    df = df[df["recipe_id"].isin(valid_recipe_ids)]
    df["interaction_date"] = pd.to_datetime(df.get("date"), errors="coerce").dt.date
    df["review"] = ""
    df = df.reset_index(drop=True)
    df["interaction_id"] = df.index + 1
    out = df[["interaction_id", "user_id", "recipe_id", "rating", "review", "interaction_date"]]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def main(recipes_df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    cfg = load_config()
    raw_dir = resolve_path(cfg["paths"]["raw_dir"])
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])

    if recipes_df is None:
        recipes_df = pd.read_csv(processed_dir / "clean_recipes.csv")

    valid_recipe_ids = set(recipes_df["recipe_id"].astype(int))
    outputs: dict[str, pd.DataFrame] = {}

    for split, filename in SPLIT_FILES.items():
        raw_path = raw_dir / filename
        if not raw_path.exists():
            continue
        out_path = processed_dir / f"clean_interactions_{split}.csv"
        outputs[split] = clean_split_file(raw_path, valid_recipe_ids, out_path)

    return outputs


if __name__ == "__main__":
    results = main()
    for split, df in results.items():
        print(f"{split}: {len(df)} interactions")
