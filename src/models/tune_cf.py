"""Tune collaborative filtering hyperparameters on the validation split."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

from src.models.collaborative_filtering import CollaborativeFilteringRecommender, build_cf_model
from src.preprocessing.config_loader import load_config, resolve_path


def _hit_rate_at_k(
    model: CollaborativeFilteringRecommender,
    val_df: pd.DataFrame,
    recipes_df: pd.DataFrame,
    k: int = 10,
    negative_sample: int = 99,
    max_users: int = 50,
    min_rating: float = 4.0,
    seed: int = 42,
) -> float:
    """Leave-one-out style hit rate: is the held-out item in top-K?"""
    positives = val_df[val_df["rating"] >= min_rating]
    users = positives["user_id"].astype(int).unique()[:max_users]
    all_recipe_ids = set(recipes_df["recipe_id"].astype(int))
    hits = 0
    total = 0

    for user_id in users:
        user_rows = positives[positives["user_id"] == user_id]
        if user_rows.empty:
            continue
        target = int(user_rows.iloc[0]["recipe_id"])
        seen = set(
            model.train_df[model.train_df["user_id"] == user_id]["recipe_id"].astype(int)
        )
        pool = list(all_recipe_ids - seen)
        rng = random.Random(seed + int(user_id))
        sample_size = min(negative_sample, len(pool))
        candidates = [target] + rng.sample(pool, sample_size) if sample_size else [target]

        ranked = model.recommend_for_user(user_id, candidates, top_k=k)
        if ranked.empty:
            continue
        total += 1
        if target in ranked["recipe_id"].astype(int).tolist():
            hits += 1

    return hits / total if total else 0.0


def tune_collaborative_filtering(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    recipes_df: pd.DataFrame,
    cf_cfg: dict,
) -> dict:
    """Search CF configs; return best by validation hit rate@10 (tie-break: lower RMSE)."""
    candidates = cf_cfg.get("candidates", [])
    if not candidates:
        candidates = [
            {"algorithm": "knn_item", "params": {"k": 40}},
            {"algorithm": "knn_item", "params": {"k": 20}},
            {"algorithm": "svd", "params": {"n_factors": 50, "n_epochs": 15, "reg_all": 0.05}},
            {"algorithm": "svd", "params": {"n_factors": 80, "n_epochs": 20, "reg_all": 0.02}},
        ]

    tune_cfg = cf_cfg.get("tuning", {})
    k = tune_cfg.get("hit_rate_k", 10)
    max_users = tune_cfg.get("max_tune_users", 40)
    negative_sample = tune_cfg.get("negative_sample", 99)

    results = []
    best: dict | None = None

    for spec in candidates:
        algo = spec["algorithm"]
        params = spec.get("params", {})
        model = CollaborativeFilteringRecommender(train_df, algorithm=algo, model_params=params).fit(
            max_items_for_knn=cf_cfg.get("tuning", {}).get("max_items_for_knn", 8000)
        )
        rmse = model.rmse(val_df)
        hit = _hit_rate_at_k(
            model,
            val_df,
            recipes_df,
            k=k,
            negative_sample=negative_sample,
            max_users=max_users,
        )
        entry = {
            "algorithm": algo,
            "params": params,
            "validation_rmse": rmse,
            f"validation_hit_rate@{k}": hit,
        }
        results.append(entry)

        if best is None:
            best = entry
        else:
            best_hit = best[f"validation_hit_rate@{k}"]
            if hit > best_hit or (hit == best_hit and rmse < best["validation_rmse"]):
                best = entry

    assert best is not None
    return {
        "best": {
            "algorithm": best["algorithm"],
            "params": best["params"],
            "validation_rmse": best["validation_rmse"],
            f"validation_hit_rate@{k}": best[f"validation_hit_rate@{k}"],
        },
        "all_results": results,
    }


def main() -> dict:
    cfg = load_config()
    processed = resolve_path(cfg["paths"]["processed_dir"])
    cf_cfg = cfg.get("collaborative_filtering", {})

    train_df = pd.read_csv(processed / "clean_interactions_train.csv")
    val_df = pd.read_csv(processed / "clean_interactions_validation.csv")
    recipes_df = pd.read_csv(processed / "clean_recipes.csv")

    output = tune_collaborative_filtering(train_df, val_df, recipes_df, cf_cfg)

    out_path = resolve_path(cf_cfg.get("best_config_file", "config/cf_best.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return output


if __name__ == "__main__":
    result = main()
    print(json.dumps(result["best"], indent=2))
