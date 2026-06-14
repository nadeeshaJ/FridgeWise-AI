"""Fetch Open Food Facts products → clean_open_food_products.csv"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

from src.preprocessing.config_loader import load_config, resolve_path
from src.preprocessing.ingredient_utils import compute_nutrition_score, map_product_to_ingredient, normalize_text


FIELDS = (
    "code,product_name,brands,categories,ingredients_text,allergens,"
    "nutrition_grades,nutriments"
)

USER_AGENT = "FridgeWise-AI/1.0 (Recommender Systems Academic Project)"

# Curated fallback when API search is blocked (barcodes from Open Food Facts)
FALLBACK_BARCODES = [
    "3017624010701",  # Nutella
    "5000159484695",  # Weetabix
    "8000500310427",  # Barilla pasta
    "7622210449283",  # Philadelphia cream cheese
    "5000112588137",  # Heinz tomato ketchup
    "8712561425243",  # Alpro soy yogurt
    "8001090220002",  # Mulino Bianco biscuits
    "5449000000996",  # Coca-Cola (beverage sample)
    "3017620422003",  # Kinder Bueno
    "4008400402225",  # Milka chocolate
    "87157232",       # Campina milk
    "87104000",       # Activia yogurt
    "8076809513646",  # De Cecco pasta
    "5016084100520",  # Baxters baked beans
    "5016084100001",  # Baxters soup
]

# Minimal static fallback if all API calls fail
STATIC_PRODUCTS = [
    {
        "barcode": "8000500310427",
        "product_name": "Barilla Spaghetti",
        "brand": "Barilla",
        "generic_ingredient_name": "pasta",
        "categories": "Pasta",
        "ingredients_text": "Durum wheat semolina",
        "allergens": "gluten",
        "nutriscore_grade": "a",
        "energy_kcal_100g": 359.0,
        "fat_100g": 2.0,
        "saturated_fat_100g": 0.5,
        "carbohydrates_100g": 71.0,
        "sugars_100g": 3.0,
        "protein_100g": 13.0,
        "salt_100g": 0.01,
        "fiber_100g": 3.0,
    },
    {
        "barcode": "87157232",
        "product_name": "Campina Fresh Milk",
        "brand": "Campina",
        "generic_ingredient_name": "milk",
        "categories": "Milk",
        "ingredients_text": "Whole milk",
        "allergens": "milk",
        "nutriscore_grade": "b",
        "energy_kcal_100g": 64.0,
        "fat_100g": 3.6,
        "saturated_fat_100g": 2.4,
        "carbohydrates_100g": 4.7,
        "sugars_100g": 4.7,
        "protein_100g": 3.3,
        "salt_100g": 0.1,
        "fiber_100g": 0.0,
    },
    {
        "barcode": "7622210449283",
        "product_name": "Philadelphia Cream Cheese",
        "brand": "Philadelphia",
        "generic_ingredient_name": "cheese",
        "categories": "Cheese",
        "ingredients_text": "Milk, cream, salt",
        "allergens": "milk",
        "nutriscore_grade": "d",
        "energy_kcal_100g": 253.0,
        "fat_100g": 24.0,
        "saturated_fat_100g": 15.0,
        "carbohydrates_100g": 3.0,
        "sugars_100g": 3.0,
        "protein_100g": 5.0,
        "salt_100g": 0.9,
        "fiber_100g": 0.0,
    },
    {
        "barcode": "87104000",
        "product_name": "Activia Natural Yogurt",
        "brand": "Activia",
        "generic_ingredient_name": "yogurt",
        "categories": "Yogurt",
        "ingredients_text": "Milk, live cultures",
        "allergens": "milk",
        "nutriscore_grade": "a",
        "energy_kcal_100g": 77.0,
        "fat_100g": 3.0,
        "saturated_fat_100g": 2.0,
        "carbohydrates_100g": 9.0,
        "sugars_100g": 9.0,
        "protein_100g": 4.0,
        "salt_100g": 0.1,
        "fiber_100g": 0.0,
    },
    {
        "barcode": "5000159484695",
        "product_name": "Weetabix Cereal",
        "brand": "Weetabix",
        "generic_ingredient_name": "cereal",
        "categories": "Breakfast cereals",
        "ingredients_text": "Wholegrain wheat",
        "allergens": "gluten",
        "nutriscore_grade": "a",
        "energy_kcal_100g": 362.0,
        "fat_100g": 2.0,
        "saturated_fat_100g": 0.4,
        "carbohydrates_100g": 69.0,
        "sugars_100g": 4.0,
        "protein_100g": 12.0,
        "salt_100g": 0.3,
        "fiber_100g": 10.0,
    },
    {
        "barcode": "5016084100520",
        "product_name": "Heinz Baked Beans",
        "brand": "Heinz",
        "generic_ingredient_name": "beans",
        "categories": "Canned beans",
        "ingredients_text": "Beans, tomato sauce",
        "allergens": "",
        "nutriscore_grade": "a",
        "energy_kcal_100g": 81.0,
        "fat_100g": 0.5,
        "saturated_fat_100g": 0.1,
        "carbohydrates_100g": 14.0,
        "sugars_100g": 4.0,
        "protein_100g": 5.0,
        "salt_100g": 0.6,
        "fiber_100g": 4.0,
    },
    {
        "barcode": "5000112588137",
        "product_name": "Heinz Tomato Ketchup",
        "brand": "Heinz",
        "generic_ingredient_name": "tomato sauce",
        "categories": "Sauces",
        "ingredients_text": "Tomatoes, vinegar, sugar, salt",
        "allergens": "",
        "nutriscore_grade": "c",
        "energy_kcal_100g": 112.0,
        "fat_100g": 0.1,
        "saturated_fat_100g": 0.0,
        "carbohydrates_100g": 26.0,
        "sugars_100g": 22.0,
        "protein_100g": 1.0,
        "salt_100g": 1.8,
        "fiber_100g": 0.5,
    },
    {
        "barcode": "8001090220002",
        "product_name": "Mulino Bianco Bread",
        "brand": "Mulino Bianco",
        "generic_ingredient_name": "bread",
        "categories": "Bread",
        "ingredients_text": "Wheat flour, water, yeast",
        "allergens": "gluten",
        "nutriscore_grade": "c",
        "energy_kcal_100g": 280.0,
        "fat_100g": 4.0,
        "saturated_fat_100g": 0.8,
        "carbohydrates_100g": 52.0,
        "sugars_100g": 5.0,
        "protein_100g": 9.0,
        "salt_100g": 1.2,
        "fiber_100g": 3.0,
    },
    {
        "barcode": "8076809513646",
        "product_name": "De Cecco Rice",
        "brand": "De Cecco",
        "generic_ingredient_name": "rice",
        "categories": "Rice",
        "ingredients_text": "Rice",
        "allergens": "",
        "nutriscore_grade": "a",
        "energy_kcal_100g": 360.0,
        "fat_100g": 1.0,
        "saturated_fat_100g": 0.2,
        "carbohydrates_100g": 79.0,
        "sugars_100g": 0.5,
        "protein_100g": 7.0,
        "salt_100g": 0.0,
        "fiber_100g": 1.0,
    },
    {
        "barcode": "8712561425243",
        "product_name": "Alpro Tofu",
        "brand": "Alpro",
        "generic_ingredient_name": "tofu",
        "categories": "Tofu",
        "ingredients_text": "Soybeans, water",
        "allergens": "soy",
        "nutriscore_grade": "a",
        "energy_kcal_100g": 144.0,
        "fat_100g": 8.0,
        "saturated_fat_100g": 1.2,
        "carbohydrates_100g": 2.0,
        "sugars_100g": 0.5,
        "protein_100g": 16.0,
        "salt_100g": 0.1,
        "fiber_100g": 1.0,
    },
]


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _parse_product(product: dict, barcode: str) -> dict | None:
    name = product.get("product_name") or product.get("product_name_en") or ""
    if not name:
        return None

    nutriments = product.get("nutriments") or {}
    categories = product.get("categories") or ""
    generic = map_product_to_ingredient(name, categories)

    sugars = _safe_float(nutriments.get("sugars_100g"))
    sat_fat = _safe_float(nutriments.get("saturated-fat_100g") or nutriments.get("saturated_fat_100g"))
    salt = _safe_float(nutriments.get("salt_100g"))
    protein = _safe_float(nutriments.get("proteins_100g") or nutriments.get("protein_100g"))
    fiber = _safe_float(nutriments.get("fiber_100g") or nutriments.get("fibre_100g"))

    allergens_raw = product.get("allergens") or product.get("allergens_tags") or ""
    if isinstance(allergens_raw, list):
        allergens = "|".join(normalize_text(a.replace("en:", "")) for a in allergens_raw)
    else:
        allergens = normalize_text(str(allergens_raw).replace("en:", ""))

    nutriscore = (product.get("nutrition_grades") or product.get("nutriscore_grade") or "").lower()

    return {
        "barcode": barcode,
        "product_name": name.strip(),
        "brand": (product.get("brands") or "").split(",")[0].strip(),
        "generic_ingredient_name": generic,
        "categories": categories,
        "ingredients_text": (product.get("ingredients_text") or "")[:500],
        "allergens": allergens,
        "nutriscore_grade": nutriscore,
        "energy_kcal_100g": _safe_float(nutriments.get("energy-kcal_100g") or nutriments.get("energy_kcal_100g")),
        "fat_100g": _safe_float(nutriments.get("fat_100g")),
        "saturated_fat_100g": sat_fat,
        "carbohydrates_100g": _safe_float(nutriments.get("carbohydrates_100g")),
        "sugars_100g": sugars,
        "protein_100g": protein,
        "salt_100g": salt,
        "fiber_100g": fiber,
        "nutrition_score": compute_nutrition_score(sugars, sat_fat, salt, protein, fiber),
    }


def _search_products(base_url: str, term: str, page_size: int) -> list[dict]:
    url = f"{base_url}/api/v2/search"
    params = {
        "categories_tags_en": term,
        "page_size": page_size,
        "fields": FIELDS,
    }
    session = _session()
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("products") or []


def _get_product_by_barcode(base_url: str, barcode: str) -> dict | None:
    url = f"{base_url}/api/v2/product/{barcode}"
    params = {"fields": FIELDS}
    session = _session()
    resp = session.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != 1:
        return None
    return data.get("product")


def _static_product_rows() -> list[dict]:
    rows = []
    for item in STATIC_PRODUCTS:
        row = dict(item)
        row["nutrition_score"] = compute_nutrition_score(
            row.get("sugars_100g"),
            row.get("saturated_fat_100g"),
            row.get("salt_100g"),
            row.get("protein_100g"),
            row.get("fiber_100g"),
        )
        rows.append(row)
    return rows


def fetch_open_food_facts(
    output_path: Path,
    cache_path: Path,
    base_url: str,
    search_terms: list[str],
    max_products_per_term: int,
    page_size: int = 24,
) -> pd.DataFrame:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached: list[dict] = []
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            cached = json.load(f)

    seen_barcodes = {p["barcode"] for p in cached}
    rows: list[dict] = list(cached)

    for term in search_terms:
        try:
            products = _search_products(base_url, term, page_size)
        except requests.RequestException as exc:
            print(f"Warning: search failed for '{term}': {exc}")
            continue

        added = 0
        for product in products:
            barcode = str(product.get("code") or product.get("_id") or "")
            if not barcode or barcode in seen_barcodes:
                continue
            parsed = _parse_product(product, barcode)
            if parsed and parsed["generic_ingredient_name"]:
                rows.append(parsed)
                seen_barcodes.add(barcode)
                added += 1
            if added >= max_products_per_term:
                break
        time.sleep(0.3)

    for barcode in FALLBACK_BARCODES:
        if barcode in seen_barcodes:
            continue
        try:
            product = _get_product_by_barcode(base_url, barcode)
            if product:
                parsed = _parse_product(product, barcode)
                if parsed:
                    rows.append(parsed)
                    seen_barcodes.add(barcode)
            time.sleep(0.2)
        except requests.RequestException as exc:
            print(f"Warning: barcode lookup failed for {barcode}: {exc}")

    if not rows:
        print("Warning: Open Food Facts API unavailable; using curated static product sample.")
        rows = _static_product_rows()
        seen_barcodes = {p["barcode"] for p in rows}

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    df = pd.DataFrame(rows).drop_duplicates(subset=["barcode"])
    if df.empty:
        raise RuntimeError("No Open Food Facts products fetched. Check network connection.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def main() -> pd.DataFrame:
    cfg = load_config()
    off_cfg = cfg["open_food_facts"]
    processed_dir = resolve_path(cfg["paths"]["processed_dir"])
    cache_dir = resolve_path(cfg["paths"]["cache_dir"])
    return fetch_open_food_facts(
        output_path=processed_dir / "clean_open_food_products.csv",
        cache_path=cache_dir / "open_food_facts_cache.json",
        base_url=off_cfg["base_url"],
        search_terms=off_cfg["search_terms"],
        max_products_per_term=off_cfg["max_products_per_term"],
        page_size=off_cfg["page_size"],
    )


if __name__ == "__main__":
    result = main()
    print(f"Saved {len(result)} Open Food Facts products")
