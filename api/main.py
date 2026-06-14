"""FastAPI backend for FridgeWise Flutter prototype."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.collaborative_filtering import CollaborativeFilteringRecommender
from src.models.content_based import ContentBasedRecommender
from src.models.hybrid_recommender import HybridRecommender
from src.preprocessing.config_loader import load_config, resolve_path

app = FastAPI(title="FridgeWise AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    cf = CollaborativeFilteringRecommender(train).fit()
    hybrid = HybridRecommender(content, cf, recipes, fridge, products, cfg["hybrid_weights"])
    train_users = set(train["user_id"].astype(int))

    return {
        "recipes": recipes,
        "fridge": fridge,
        "products": products,
        "hybrid": hybrid,
        "train_users": train_users,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "FridgeWise AI"}


@app.get("/users/{user_id}/fridge")
def get_fridge(user_id: int):
    data = _load_models()
    items = data["fridge"][data["fridge"]["user_id"] == user_id]
    if items.empty:
        raise HTTPException(404, f"No fridge inventory for user {user_id}")
    return items.to_dict(orient="records")


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
    row = recipe.iloc[0].to_dict()
    return row


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
    users = sorted(data["fridge"]["user_id"].unique().tolist())
    return {"users": users[:10]}


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
