"""FastAPI backend for FridgeWise Flutter prototype."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal
import math

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.fridge_store import FridgeStore
from src.evaluation.evaluate import load_best_cf
from src.models.content_based import ContentBasedRecommender
from src.models.hybrid_recommender import HybridRecommender
from src.preprocessing.config_loader import load_config, resolve_path

app = FastAPI(title="FridgeWise AI API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FridgeItemCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1)
    quantity: float = Field(1.0, gt=0)
    unit: str = "piece"
    storage_type: Literal["fridge", "freezer", "pantry"] = "fridge"
    days_to_expiry: int = Field(7, ge=0, le=365)
    barcode: str = ""


class FridgeItemUpdate(BaseModel):
    ingredient_name: str | None = None
    quantity: float | None = Field(None, gt=0)
    unit: str | None = None
    storage_type: Literal["fridge", "freezer", "pantry"] | None = None
    days_to_expiry: int | None = Field(None, ge=0, le=365)
    barcode: str | None = None


class BarcodeAddRequest(BaseModel):
    barcode: str = Field(..., min_length=4)
    quantity: float = Field(1.0, gt=0)
    unit: str = "piece"
    storage_type: Literal["fridge", "freezer", "pantry"] = "fridge"
    days_to_expiry: int = Field(7, ge=0, le=365)


def _serialize_item(item: dict) -> dict:
    out = dict(item)
    for key in ("purchase_date", "expiry_date"):
        value = out.get(key)
        if value is not None and not isinstance(value, str):
            out[key] = str(value)[:10]
    for key in ("quantity", "expiry_priority_score"):
        if key in out and out[key] is not None:
            val = float(out[key])
            out[key] = None if math.isnan(val) else val
    for key in ("inventory_id", "user_id", "days_to_expiry"):
        if key in out and out[key] is not None:
            try:
                out[key] = int(out[key])
            except (TypeError, ValueError):
                out[key] = None
    if out.get("barcode") is None or (isinstance(out["barcode"], float) and math.isnan(out["barcode"])):
        out["barcode"] = ""
    else:
        out["barcode"] = str(out["barcode"])
    return out


@lru_cache(maxsize=1)
def _load_models():
    cfg = load_config()
    processed = resolve_path(cfg["paths"]["processed_dir"])

    recipes = pd.read_csv(processed / "clean_recipes.csv")
    fridge = pd.read_csv(processed / "user_fridge_inventory.csv")
    products = pd.read_csv(processed / "clean_open_food_products.csv")

    train_path = processed / "clean_interactions_train.csv"
    if train_path.exists():
        train = pd.read_csv(train_path)
    else:
        train = pd.read_csv(processed / "clean_interactions.csv")

    content = ContentBasedRecommender(recipes).fit()
    cf = load_best_cf(train, cfg)
    ref_date = cfg.get("fridge_inventory", {}).get("reference_date", "2026-06-14")
    store = FridgeStore(fridge, ref_date)
    hybrid = HybridRecommender(
        content, cf, recipes, store.dataframe, products, cfg["hybrid_weights"]
    )
    train_users = set(train["user_id"].astype(int))

    return {
        "recipes": recipes,
        "products": products,
        "hybrid": hybrid,
        "store": store,
        "train_users": train_users,
    }


def _sync_fridge(data: dict) -> None:
    data["store"].sync_hybrid(data["hybrid"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "FridgeWise AI"}


@app.get("/users/{user_id}/fridge")
def get_fridge(user_id: int):
    data = _load_models()
    items = data["store"].get_user_items(user_id)
    return [_serialize_item(item) for item in items]


@app.post("/users/{user_id}/fridge/items", status_code=201)
def add_fridge_item(user_id: int, body: FridgeItemCreate):
    data = _load_models()
    item = data["store"].add_item(
        user_id=user_id,
        ingredient_name=body.ingredient_name,
        quantity=body.quantity,
        unit=body.unit,
        storage_type=body.storage_type,
        days_to_expiry=body.days_to_expiry,
        barcode=body.barcode,
    )
    _sync_fridge(data)
    return _serialize_item(item)


@app.put("/users/{user_id}/fridge/items/{inventory_id}")
def update_fridge_item(user_id: int, inventory_id: int, body: FridgeItemUpdate):
    data = _load_models()
    updates = body.model_dump(exclude_unset=True)
    item = data["store"].update_item(user_id, inventory_id, updates)
    if item is None:
        raise HTTPException(404, f"Item {inventory_id} not found for user {user_id}")
    _sync_fridge(data)
    return _serialize_item(item)


@app.delete("/users/{user_id}/fridge/items/{inventory_id}", status_code=204)
def delete_fridge_item(user_id: int, inventory_id: int):
    data = _load_models()
    if not data["store"].delete_item(user_id, inventory_id):
        raise HTTPException(404, f"Item {inventory_id} not found for user {user_id}")
    _sync_fridge(data)


@app.post("/users/{user_id}/fridge/from-barcode", status_code=201)
def add_fridge_item_from_barcode(user_id: int, body: BarcodeAddRequest):
    data = _load_models()
    product = data["products"][data["products"]["barcode"].astype(str) == str(body.barcode)]
    if product.empty:
        raise HTTPException(404, f"Product {body.barcode} not found")
    row = product.iloc[0]
    name = row.get("product_name") or row.get("generic_ingredient_name") or "Unknown product"
    item = data["store"].add_item(
        user_id=user_id,
        ingredient_name=str(name),
        quantity=body.quantity,
        unit=body.unit,
        storage_type=body.storage_type,
        days_to_expiry=body.days_to_expiry,
        barcode=str(body.barcode),
    )
    _sync_fridge(data)
    return _serialize_item(item)


@app.get("/users/{user_id}/recommendations")
def get_recommendations(user_id: int, top_k: int = 10):
    data = _load_models()
    recs = data["hybrid"].recommend(user_id, top_k=top_k, train_user_ids=data["train_users"])
    if recs.empty:
        raise HTTPException(404, f"No recommendations for user {user_id}")
    return recs.to_dict(orient="records")


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    data = _load_models()
    recipe = data["recipes"][data["recipes"]["recipe_id"] == recipe_id]
    if recipe.empty:
        raise HTTPException(404, f"Recipe {recipe_id} not found")
    return recipe.iloc[0].to_dict()


@app.get("/products/{barcode}")
def get_product(barcode: str):
    data = _load_models()
    product = data["products"][data["products"]["barcode"].astype(str) == str(barcode)]
    if product.empty:
        raise HTTPException(404, f"Product {barcode} not found")
    return product.iloc[0].to_dict()


@app.get("/demo-users")
def demo_users():
    data = _load_models()
    users = sorted(data["store"].dataframe["user_id"].unique().tolist())
    return {"users": users[:10]}


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
