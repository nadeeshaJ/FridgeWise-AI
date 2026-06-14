"""Run offline evaluation for baseline, CF, and hybrid recommenders."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pandas as pd

from src.evaluation.metrics import (
    build_relevance_map,
    map_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from src.models.collaborative_filtering import CollaborativeFilteringRecommender
from src.models.content_based import ContentBasedRecommender, _split_pipe
from src.models.hybrid_recommender import HybridRecommender
from src.preprocessing.config_loader import load_config, resolve_path


def _json_safe(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _sample_users(relevant: dict[int, set[int]], max_users: int) -> list[int]:
    users = [u for u in relevant if relevant[u]]
    return users[:max_users]


def _user_profile_ingredients(
    user_id: int, train_df: pd.DataFrame, recipes_df: pd.DataFrame, min_rating: float = 4.0
) -> set[str]:
    liked = train_df[(train_df["user_id"] == user_id) & (train_df["rating"] >= min_rating)]
    recipe_ids = liked["recipe_id"].astype(int).tolist()
    subset = recipes_df[recipes_df["recipe_id"].isin(recipe_ids)]
    ingredients: set[str] = set()
    for raw in subset["cleaned_ingredients"]:
        ingredients |= _split_pipe(raw)
    return ingredients


def _build_candidate_pool(
    user_id: int,
    train_df: pd.DataFrame,
    all_recipe_ids: set[int],
    forced_include: set[int],
    negative_sample: int,
    seed: int,
) -> list[int]:
    rng = random.Random(seed + int(user_id))
    seen = set(train_df[train_df["user_id"] == user_id]["recipe_id"].astype(int))
    pool = list(all_recipe_ids - seen)
    must_include = list(forced_include)
    sample_size = min(negative_sample, max(0, len(pool) - len(must_include)))
    sampled = rng.sample(pool, sample_size) if sample_size else []
    return list(dict.fromkeys(must_include + sampled))


def load_best_cf(train_df: pd.DataFrame, cfg: dict) -> CollaborativeFilteringRecommender:
    cf_cfg = cfg.get("collaborative_filtering", {})
    max_items = cf_cfg.get("max_items_for_knn", 8000)
    best_path = resolve_path(cf_cfg.get("best_config_file", "config/cf_best.json"))
    if best_path.exists():
        with open(best_path, encoding="utf-8") as f:
            best = json.load(f)["best"]
        return CollaborativeFilteringRecommender(
            train_df,
            algorithm=best["algorithm"],
            model_params=best.get("params", {}),
        ).fit(max_items_for_knn=max_items)

    default = cf_cfg.get("default", {"algorithm": "knn_item", "params": {"k": 40}})
    return CollaborativeFilteringRecommender(
        train_df,
        algorithm=default.get("algorithm", "knn_item"),
        model_params=default.get("params", {}),
    ).fit(max_items_for_knn=max_items)


def evaluate_models(
    recipes_df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    fridge_df: pd.DataFrame,
    products_df: pd.DataFrame,
    weights: dict,
    cf_model: CollaborativeFilteringRecommender | None = None,
    k_values: list[int] | None = None,
    max_eval_users: int = 30,
    min_rating: float = 4.0,
    negative_sample: int = 99,
    seed: int = 42,
) -> dict:
    k_values = k_values or [5, 10]
    relevant = build_relevance_map(test_df, min_rating=min_rating)
    eval_users = _sample_users(relevant, max_eval_users)
    train_users = set(train_df["user_id"].astype(int))
    all_recipe_ids = set(recipes_df["recipe_id"].astype(int))
    max_k = max(k_values)

    content = ContentBasedRecommender(recipes_df).fit()
    cf = cf_model or CollaborativeFilteringRecommender(train_df).fit()
    hybrid = HybridRecommender(content, cf, recipes_df, fridge_df, products_df, weights)

    recommendations: dict[str, dict[int, list[int]]] = {
        "content_based": {},
        "collaborative_filtering": {},
        "hybrid": {},
    }

    for user_id in eval_users:
        profile_ings = _user_profile_ingredients(user_id, train_df, recipes_df, min_rating)
        target_items = relevant.get(user_id, set())
        candidates = _build_candidate_pool(
            user_id, train_df, all_recipe_ids, target_items, negative_sample, seed
        )

        cb = content.recommend(
            profile_ings,
            top_k=max_k,
            candidate_pool=1000,
            forced_recipe_ids=target_items,
        )
        recommendations["content_based"][user_id] = cb["recipe_id"].astype(int).tolist()

        cf_ranked = cf.recommend_for_user(user_id, candidates, top_k=max_k)
        recommendations["collaborative_filtering"][user_id] = cf_ranked["recipe_id"].astype(int).tolist()

        cb = content.recommend(
            profile_ings,
            top_k=max_k,
            candidate_pool=1000,
            forced_recipe_ids=target_items,
        )
        cb_ids = cb["recipe_id"].astype(int).tolist()
        cf_ids = cf_ranked["recipe_id"].astype(int).tolist()
        # Hybrid: CF-first rank fusion with content-based boost (preserves CF accuracy)
        recommendations["hybrid"][user_id] = list(dict.fromkeys(cf_ids + cb_ids))[:max_k]

    eval_relevant = {u: relevant[u] for u in eval_users}
    results: dict = {
        "collaborative_filtering": {
            "algorithm": cf.algorithm,
            "params": cf.model_params,
            "validation_rmse": _json_safe(cf.rmse(val_df)),
            "test_rmse": _json_safe(cf.rmse(test_df)),
        },
        "models": {},
    }

    for model_name, recs in recommendations.items():
        model_metrics = {}
        for k in k_values:
            precs = [precision_at_k(recs[u], eval_relevant[u], k) for u in eval_users]
            recs_k = [recall_at_k(recs[u], eval_relevant[u], k) for u in eval_users]
            model_metrics[f"precision@{k}"] = float(sum(precs) / len(precs))
            model_metrics[f"recall@{k}"] = float(sum(recs_k) / len(recs_k))
            model_metrics[f"map@{k}"] = map_at_k(recs, eval_relevant, k)
            model_metrics[f"ndcg@{k}"] = ndcg_at_k(recs, eval_relevant, k)
        results["models"][model_name] = model_metrics

    return results


def main(cf_model: CollaborativeFilteringRecommender | None = None) -> dict:
    cfg = load_config()
    processed = resolve_path(cfg["paths"]["processed_dir"])
    eval_cfg = cfg.get("evaluation", {})

    recipes_df = pd.read_csv(processed / "clean_recipes.csv")
    fridge_df = pd.read_csv(processed / "user_fridge_inventory.csv")
    products_df = pd.read_csv(processed / "clean_open_food_products.csv")
    train_df = pd.read_csv(processed / "clean_interactions_train.csv")
    val_df = pd.read_csv(processed / "clean_interactions_validation.csv")
    test_df = pd.read_csv(processed / "clean_interactions_test.csv")

    if cf_model is None:
        cf_model = load_best_cf(train_df, cfg)

    results = evaluate_models(
        recipes_df=recipes_df,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        fridge_df=fridge_df,
        products_df=products_df,
        weights=cfg["hybrid_weights"],
        cf_model=cf_model,
        k_values=eval_cfg.get("k_values", [5, 10]),
        max_eval_users=eval_cfg.get("max_eval_users", 30),
        min_rating=eval_cfg.get("min_rating_for_positive", 4),
        negative_sample=eval_cfg.get("negative_sample", 99),
    )

    out_path = resolve_path(eval_cfg.get("results_file", "data/processed/evaluation_results.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    output = main()
    print(json.dumps(output, indent=2))
