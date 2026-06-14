"""Collaborative filtering with Surprise (SVD or item-based KNN)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from surprise import KNNBasic, SVD, Dataset, Reader
from surprise.trainset import Trainset


def build_cf_model(algorithm: str = "knn_item", **params: Any):
    """Create a Surprise model from algorithm name and parameters."""
    algorithm = algorithm.lower()
    if algorithm == "svd":
        return SVD(
            n_factors=params.get("n_factors", 50),
            n_epochs=params.get("n_epochs", 20),
            lr_all=params.get("lr_all", 0.005),
            reg_all=params.get("reg_all", 0.02),
            random_state=params.get("random_state", 42),
        )
    if algorithm in {"knn_item", "knn"}:
        return KNNBasic(
            k=params.get("k", 40),
            min_k=params.get("min_k", 5),
            sim_options={
                "name": params.get("sim_name", "cosine"),
                "user_based": False,
            },
        )
    if algorithm == "knn_user":
        return KNNBasic(
            k=params.get("k", 40),
            min_k=params.get("min_k", 5),
            sim_options={
                "name": params.get("sim_name", "cosine"),
                "user_based": True,
            },
        )
    raise ValueError(f"Unknown CF algorithm: {algorithm}")


@dataclass
class CollaborativeFilteringRecommender:
    train_df: pd.DataFrame
    algorithm: str = "knn_item"
    model_params: dict = field(default_factory=dict)
    model: Any = None
    trainset: Trainset | None = None
    recipe_ids: set[int] = field(default_factory=set)
    train_users: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.model is None:
            self.model = build_cf_model(self.algorithm, **self.model_params)

    def fit(self, max_items_for_knn: int | None = 8000) -> CollaborativeFilteringRecommender:
        train_df = self.train_df
        if "knn" in self.algorithm.lower() and max_items_for_knn:
            top_items = (
                train_df["recipe_id"].value_counts().head(max_items_for_knn).index.astype(int)
            )
            train_df = train_df[train_df["recipe_id"].isin(top_items)]

        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(
            train_df[["user_id", "recipe_id", "rating"]],
            reader,
        )
        self.trainset = data.build_full_trainset()
        self.model.fit(self.trainset)
        self.recipe_ids = set(train_df["recipe_id"].astype(int))
        self.train_users = set(train_df["user_id"].astype(int))
        return self

    def predict_rating(self, user_id: int, recipe_id: int) -> float:
        if int(user_id) not in self.train_users:
            return 3.0
        try:
            pred = self.model.predict(int(user_id), int(recipe_id)).est
            return float(max(1.0, min(5.0, pred))) if pred is not None else 3.0
        except Exception:
            return 3.0

    def rmse(self, eval_df: pd.DataFrame, require_known_user: bool = True) -> float:
        """RMSE on held-out ratings. CF can predict unseen items for known users."""
        df = eval_df.copy()
        df["user_id"] = df["user_id"].astype(int)
        df["recipe_id"] = df["recipe_id"].astype(int)
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

        if require_known_user:
            df = df[df["user_id"].isin(self.train_users)]

        df = df.dropna(subset=["rating"])
        if df.empty:
            return float("nan")

        sq_errors = []
        for row in df.itertuples(index=False):
            est = self.predict_rating(int(row.user_id), int(row.recipe_id))
            sq_errors.append((float(row.rating) - est) ** 2)

        if not sq_errors:
            return float("nan")
        return float(sum(sq_errors) / len(sq_errors)) ** 0.5

    def recommend_for_user(
        self,
        user_id: int,
        candidate_recipe_ids: list[int] | None = None,
        top_k: int = 10,
    ) -> pd.DataFrame:
        if int(user_id) not in self.train_users:
            return pd.DataFrame(columns=["recipe_id", "score"])

        if candidate_recipe_ids is None:
            candidate_recipe_ids = list(self.recipe_ids)

        rows = [
            {"recipe_id": int(rid), "score": self.predict_rating(user_id, int(rid))}
            for rid in candidate_recipe_ids
        ]
        if not rows:
            return pd.DataFrame(columns=["recipe_id", "score"])
        return pd.DataFrame(rows).sort_values("score", ascending=False).head(top_k)
