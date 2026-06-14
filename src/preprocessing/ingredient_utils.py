"""Ingredient name cleaning, normalisation, and cold-start mapping."""

from __future__ import annotations

import ast
import re
import unicodedata
from typing import Iterable

# Common plural → singular and synonym standardisation
SYNONYM_MAP: dict[str, str] = {
    "tomatoes": "tomato",
    "onions": "onion",
    "potatoes": "potato",
    "eggs": "egg",
    "carrots": "carrot",
    "peppers": "pepper",
    "cloves": "clove",
    "mushrooms": "mushroom",
    "scallions": "scallion",
    "green onions": "onion",
    "cheddar cheese": "cheese",
    "cheddar": "cheese",
    "mozzarella cheese": "cheese",
    "mozzarella": "cheese",
    "parmesan cheese": "cheese",
    "parmesan": "cheese",
    "feta cheese": "cheese",
    "cream cheese": "cheese",
    "whole wheat pasta": "pasta",
    "spaghetti": "pasta",
    "penne": "pasta",
    "macaroni": "pasta",
    "greek yogurt": "yogurt",
    "plain yogurt": "yogurt",
    "natural yogurt": "yogurt",
    "tomato sauce": "tomato sauce",
    "marinara sauce": "tomato sauce",
    "pasta sauce": "tomato sauce",
    "canned beans": "beans",
    "black beans": "beans",
    "kidney beans": "beans",
    "chickpeas": "beans",
    "garbanzo beans": "beans",
    "whole milk": "milk",
    "skim milk": "milk",
    "almond milk": "milk",
    "soy milk": "milk",
    "brown rice": "rice",
    "white rice": "rice",
    "jasmine rice": "rice",
    "whole wheat bread": "bread",
    "white bread": "bread",
    "sourdough bread": "bread",
    "extra firm tofu": "tofu",
    "firm tofu": "tofu",
    "silken tofu": "tofu",
    "corn flakes": "cereal",
    "oatmeal": "cereal",
    "oats": "cereal",
}

# Cold-start: unfamiliar ingredient → similar known ingredients
COLD_START_MAPPINGS: dict[str, list[str]] = {
    "cassava": ["potato", "yam"],
    "tempeh": ["tofu"],
    "jackfruit": ["mushroom", "vegetable"],
    "miso": ["soy sauce", "fermented seasoning"],
    "pandan": ["vanilla", "coconut"],
    "kimchi": ["cabbage", "fermented vegetable"],
    "plantain": ["banana", "potato"],
}

# Product name keywords → generic ingredient
PRODUCT_INGREDIENT_MAP: dict[str, str] = {
    "pasta": "pasta",
    "spaghetti": "pasta",
    "penne": "pasta",
    "macaroni": "pasta",
    "cheese": "cheese",
    "cheddar": "cheese",
    "mozzarella": "cheese",
    "milk": "milk",
    "yogurt": "yogurt",
    "yoghurt": "yogurt",
    "cereal": "cereal",
    "corn flakes": "cereal",
    "oats": "cereal",
    "rice": "rice",
    "bread": "bread",
    "tofu": "tofu",
    "tomato sauce": "tomato sauce",
    "passata": "tomato sauce",
    "beans": "beans",
    "chickpea": "beans",
    "kidney bean": "beans",
}

DIETARY_TAG_KEYWORDS: dict[str, list[str]] = {
    "vegetarian": ["vegetarian", "lacto-vegetarian", "ovo-vegetarian"],
    "vegan": ["vegan"],
    "gluten-free": ["gluten-free", "gluten free"],
    "dairy-free": ["dairy-free", "dairy free"],
    "low-calorie": ["low-calorie", "low calorie", "low fat", "light"],
    "healthy": ["healthy", "clean eating", "whole30", "keto"],
    "quick": ["quick", "15-minutes-or-less", "30-minutes-or-less", "easy"],
    "breakfast": ["breakfast"],
    "lunch": ["lunch"],
    "dinner": ["dinner"],
    "dessert": ["dessert"],
}

CUISINE_TAG_KEYWORDS: dict[str, list[str]] = {
    "italian": ["italian"],
    "mexican": ["mexican"],
    "chinese": ["chinese"],
    "indian": ["indian"],
    "japanese": ["japanese"],
    "thai": ["thai"],
    "french": ["french"],
    "american": ["american"],
    "mediterranean": ["mediterranean", "greek"],
    "korean": ["korean"],
}


def normalize_text(value: str) -> str:
    """Lowercase, strip accents, remove punctuation, collapse whitespace."""
    if not value or not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def apply_synonyms(text: str) -> str:
    """Map ingredient to canonical synonym if known."""
    if not text:
        return ""
    if text in SYNONYM_MAP:
        return SYNONYM_MAP[text]
    for phrase, canonical in sorted(SYNONYM_MAP.items(), key=lambda x: -len(x[0])):
        if phrase in text:
            return canonical
    return text


def clean_ingredient_name(name: str) -> str:
    """Full cleaning pipeline for a single ingredient."""
    text = normalize_text(name)
    if not text:
        return ""
    # Remove quantity / unit prefixes common in Food.com strings
    text = re.sub(
        r"^(\d+(\.\d+)?|\d+/\d+)\s*(cup|cups|tbsp|tsp|tablespoon|teaspoon|oz|ounce|ounces|lb|lbs|pound|pounds|g|gram|grams|kg|ml|can|cans|package|packages|clove|cloves|slice|slices|piece|pieces|inch|inches)\s+",
        "",
        text,
    )
    text = re.sub(r"^(fresh|dried|chopped|diced|minced|sliced|grated|shredded|ground|large|small|medium|whole|boneless|skinless)\s+", "", text)
    text = re.sub(r"\s+(optional|to taste|as needed)$", "", text)
    text = apply_synonyms(text)
    # Simple plural removal
    if text.endswith("ies") and len(text) > 4:
        text = text[:-3] + "y"
    elif text.endswith("es") and len(text) > 3:
        text = text[:-2]
    elif text.endswith("s") and not text.endswith("ss") and len(text) > 3:
        text = text[:-1]
    return apply_synonyms(text)


def parse_ingredient_list(raw: str | list | None) -> list[str]:
    """Parse Food.com ingredient field into a list of strings."""
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (ValueError, SyntaxError):
        pass
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        parts = re.split(r"', '", inner.strip("'"))
        return [p.strip("'").strip() for p in parts if p.strip("'").strip()]
    return [text]


def clean_ingredient_list(raw: str | list | None) -> list[str]:
    """Parse and clean a list of ingredients."""
    ingredients = parse_ingredient_list(raw)
    cleaned = []
    seen = set()
    for item in ingredients:
        c = clean_ingredient_name(item)
        if c and c not in seen:
            cleaned.append(c)
            seen.add(c)
    return cleaned


def map_product_to_ingredient(product_name: str, categories: str = "") -> str:
    """Map Open Food Facts product name to generic ingredient."""
    combined = normalize_text(f"{product_name} {categories}")
    for phrase, ingredient in sorted(PRODUCT_INGREDIENT_MAP.items(), key=lambda x: -len(x[0])):
        if phrase in combined:
            return ingredient
    return clean_ingredient_name(product_name.split(",")[0])


def get_cold_start_substitutes(ingredient: str) -> list[str]:
    """Return substitute ingredients for cold-start unfamiliar items."""
    key = clean_ingredient_name(ingredient)
    return COLD_START_MAPPINGS.get(key, [])


def extract_tags_from_list(raw_tags: str | list | None, keyword_map: dict[str, list[str]]) -> list[str]:
    """Extract structured tags from Food.com tag strings."""
    if raw_tags is None:
        tags_lower: set[str] = set()
    elif isinstance(raw_tags, list):
        tags_lower = {normalize_text(t) for t in raw_tags}
    else:
        text = str(raw_tags).strip()
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                tags_lower = {normalize_text(t) for t in parsed}
            else:
                tags_lower = {normalize_text(text)}
        except (ValueError, SyntaxError):
            tags_lower = {normalize_text(t) for t in re.split(r"[,']", text) if t.strip()}

    found = []
    for label, keywords in keyword_map.items():
        for kw in keywords:
            if any(kw in t for t in tags_lower):
                found.append(label)
                break
    return sorted(set(found))


def infer_difficulty(minutes: int | float | None, n_steps: int | float | None) -> str:
    """Infer recipe difficulty from time and steps."""
    m = float(minutes or 0)
    s = float(n_steps or 0)
    if m <= 30 and s <= 5:
        return "easy"
    if m <= 60 and s <= 10:
        return "medium"
    return "hard"


def compute_expiry_priority_score(days_to_expiry: int | float) -> float:
    """Tiered expiry priority score."""
    d = int(days_to_expiry)
    if d <= 0:
        return 1.0
    if d <= 2:
        return 0.9
    if d <= 5:
        return 0.7
    if d <= 10:
        return 0.5
    return 0.2


def compute_nutrition_score(
    sugars_100g: float | None,
    saturated_fat_100g: float | None,
    salt_100g: float | None,
    protein_100g: float | None,
    fiber_100g: float | None,
    high_sugar: float = 15.0,
    high_sat_fat: float = 5.0,
    high_salt: float = 1.5,
    high_protein: float = 10.0,
    high_fiber: float = 3.0,
) -> float:
    """Simple nutrition score in [0, 1]."""
    score = 1.0

    def _val(v):
        if v is None or (isinstance(v, float) and v != v):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    sugars = _val(sugars_100g)
    sat_fat = _val(saturated_fat_100g)
    salt = _val(salt_100g)
    protein = _val(protein_100g)
    fiber = _val(fiber_100g)

    if sugars is not None and sugars >= high_sugar:
        score -= 0.2
    if sat_fat is not None and sat_fat >= high_sat_fat:
        score -= 0.2
    if salt is not None and salt >= high_salt:
        score -= 0.2
    if protein is not None and protein >= high_protein:
        score += 0.1
    if fiber is not None and fiber >= high_fiber:
        score += 0.1
    return max(0.0, min(1.0, score))


def ingredients_to_string(items: Iterable[str]) -> str:
    """Serialize ingredient list for CSV storage."""
    return "|".join(items)
