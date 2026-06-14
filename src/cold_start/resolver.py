"""Cold-start resolution helpers."""

from __future__ import annotations

from src.cold_start.mappings import COLD_START_MAPPINGS
from src.preprocessing.ingredient_utils import clean_ingredient_name


def is_cold_start_ingredient(ingredient: str) -> bool:
    key = clean_ingredient_name(ingredient)
    return key in COLD_START_MAPPINGS


def get_cold_start_substitutes(ingredient: str) -> list[str]:
    """Return substitute ingredients for cold-start unfamiliar items."""
    key = clean_ingredient_name(ingredient)
    return list(COLD_START_MAPPINGS.get(key, []))


def expand_fridge_ingredients(ingredients: set[str]) -> set[str]:
    """Expand fridge ingredients with cold-start substitutes for matching."""
    expanded = set(ingredients)
    for ing in ingredients:
        expanded.update(get_cold_start_substitutes(ing))
    return expanded
