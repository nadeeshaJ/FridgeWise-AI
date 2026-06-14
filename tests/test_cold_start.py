"""Tests for cold-start ingredient resolution."""

from src.cold_start import (
    COLD_START_MAPPINGS,
    expand_fridge_ingredients,
    get_cold_start_substitutes,
    is_cold_start_ingredient,
)


def test_cold_start_mapping_exists():
    assert "tempeh" in COLD_START_MAPPINGS
    assert COLD_START_MAPPINGS["tempeh"] == ["tofu"]


def test_is_cold_start_ingredient():
    assert is_cold_start_ingredient("Tempeh") is True
    assert is_cold_start_ingredient("tomato") is False


def test_expand_fridge_ingredients():
    expanded = expand_fridge_ingredients({"tempeh", "tomato"})
    assert "tofu" in expanded
    assert "tomato" in expanded


def test_get_cold_start_substitutes_returns_copy():
    subs = get_cold_start_substitutes("quinoa")
    assert "rice" in subs
    subs.append("extra")
    assert "extra" not in get_cold_start_substitutes("quinoa")
