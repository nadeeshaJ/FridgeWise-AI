"""Clean Food.com RAW_recipes.csv → clean_recipes.csv"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.preprocessing.config_loader import load_config, resolve_path
from src.preprocessing.ingredient_utils import (
    clean_ingredient_list,
    extract_tags_from_list,
    infer_difficulty,
    ingredients_to_string,
    parse_ingredient_list,
    DIETARY_TAG_KEYWORDS,
    CUISINE_TAG_KEYWORDS,
)


def clean_recipes(raw_path: Path, output_path: Path, max_recipes: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    if max_recipes:
        df = df.head(max_recipes)

    df = df.rename(columns={"id": "recipe_id", "name": "recipe_name", "submitted": "submitted_date"})

    cleaned_lists = df["ingredients"].apply(clean_ingredient_list)
    raw_lists = df["ingredients"].apply(parse_ingredient_list)

    out = pd.DataFrame(
        {
            "recipe_id": df["recipe_id"],
            "recipe_name": df["recipe_name"],
            "minutes": pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int),
            "contributor_id": df["contributor_id"],
            "submitted_date": pd.to_datetime(df["submitted_date"], errors="coerce").dt.date,
            "tags": df["tags"].astype(str),
            "nutrition_raw": df["nutrition"].astype(str),
            "n_steps": pd.to_numeric(df["n_steps"], errors="coerce").fillna(0).astype(int),
            "steps": df["steps"].astype(str),
            "description": df["description"].fillna("").astype(str),
            "ingredients": raw_lists.apply(ingredients_to_string),
            "n_ingredients": cleaned_lists.apply(len),
            "cleaned_ingredients": cleaned_lists.apply(ingredients_to_string),
            "dietary_tags": df["tags"].apply(lambda t: "|".join(extract_tags_from_list(t, DIETARY_TAG_KEYWORDS))),
            "cuisine_tags": df["tags"].apply(lambda t: "|".join(extract_tags_from_list(t, CUISINE_TAG_KEYWORDS))),
            "difficulty_level": [
                infer_difficulty(m, s) for m, s in zip(df["minutes"], df["n_steps"])
            ],
        }
    )

    out = out[out["n_ingredients"] > 0].drop_duplicates(subset=["recipe_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def main() -> pd.DataFrame:
    cfg = load_config()
    raw_dir = resolve_path(cfg["paths"]["raw_dir"])
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])
    raw_path = raw_dir / cfg["food_com"]["recipes_file"]
    output_path = processed_dir / "clean_recipes.csv"
    return clean_recipes(raw_path, output_path, cfg["food_com"].get("max_recipes"))


if __name__ == "__main__":
    result = main()
    print(f"Saved {len(result)} recipes to clean_recipes.csv")
