"""Unit tests for ingredient cleaning and mapping."""

from src.cold_start import get_cold_start_substitutes
from src.preprocessing.ingredient_utils import (
    apply_synonyms,
    clean_ingredient_name,
    clean_ingredient_list,
    compute_expiry_priority_score,
    map_product_to_ingredient,
    normalize_text,
)


def test_normalize_text_strips_accents_and_punctuation():
    assert normalize_text("  Crème Fraîche!  ") == "creme fraiche"


def test_apply_synonyms_maps_cheese_variants():
    assert apply_synonyms("mozzarella cheese") == "cheese"
    assert apply_synonyms("cheddar") == "cheese"


def test_clean_ingredient_name_removes_quantity_prefix():
    assert clean_ingredient_name("2 cups chopped tomatoes") == "tomato"


def test_clean_ingredient_name_maps_proteins():
    assert clean_ingredient_name("boneless chicken breasts") == "chicken"
    assert clean_ingredient_name("ground beef") == "beef"


def test_clean_ingredient_name_maps_oils():
    assert clean_ingredient_name("extra virgin olive oil") == "oil"


def test_clean_ingredient_list_deduplicates():
    items = clean_ingredient_list(["Tomatoes", "tomato", "2 tomatoes"])
    assert items == ["tomato"]


def test_map_product_to_ingredient():
    assert map_product_to_ingredient("Barilla Spaghetti Pasta 500g") == "pasta"
    assert map_product_to_ingredient("Organic Whole Milk 1L", "dairy") == "milk"


def test_cold_start_substitutes():
    assert get_cold_start_substitutes("tempeh") == ["tofu"]
    assert "rice" in get_cold_start_substitutes("quinoa")


def test_expiry_priority_score_tiers():
    assert compute_expiry_priority_score(0) == 1.0
    assert compute_expiry_priority_score(2) == 0.9
    assert compute_expiry_priority_score(5) == 0.7
    assert compute_expiry_priority_score(30) == 0.2
