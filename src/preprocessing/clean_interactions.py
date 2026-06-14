"""Clean Food.com RAW_interactions.csv → clean_interactions.csv"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path


def clean_interactions(
    raw_path: Path,
    recipes_df: pd.DataFrame,
    output_path: Path,
    max_interactions: int | None = None,
) -> pd.DataFrame:
    valid_recipe_ids = set(recipes_df["recipe_id"].astype(int))
    df = pd.read_csv(raw_path)

    if max_interactions:
        df = df.head(max_interactions)

    df = df.dropna(subset=["user_id", "recipe_id", "rating"])
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df[(df["rating"] >= 1) & (df["rating"] <= 5)]
    df["recipe_id"] = df["recipe_id"].astype(int)
    df["user_id"] = df["user_id"].astype(int)
    df = df[df["recipe_id"].isin(valid_recipe_ids)]

    df["interaction_date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["review"] = df.get("review", pd.Series([""] * len(df))).fillna("").astype(str)
    df = df.reset_index(drop=True)
    df["interaction_id"] = df.index + 1

    out = df[["interaction_id", "user_id", "recipe_id", "rating", "review", "interaction_date"]]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def main(recipes_df: pd.DataFrame | None = None) -> pd.DataFrame:
    cfg = load_config()
    raw_dir = resolve_path(cfg["paths"]["raw_dir"])
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])

    if recipes_df is None:
        recipes_df = pd.read_csv(processed_dir / "clean_recipes.csv")

    raw_path = raw_dir / cfg["food_com"]["interactions_file"]
    output_path = processed_dir / "clean_interactions.csv"
    return clean_interactions(
        raw_path,
        recipes_df,
        output_path,
        cfg["food_com"].get("max_interactions"),
    )


if __name__ == "__main__":
    result = main()
    print(f"Saved {len(result)} interactions to clean_interactions.csv")
