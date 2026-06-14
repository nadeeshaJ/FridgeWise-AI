"""Collaborative filtering with Surprise SVD."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from surprise import SVD, Dataset, Reader, accuracy
from surprise.trainset import Trainset


@dataclass
class CollaborativeFilteringRecommender:
    train_df: pd.DataFrame
    model: SVD = field(default_factory=lambda: SVD(
        n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.02, random_state=42
    ))
    trainset: Trainset | None = None
    recipe_ids: set[int] = field(default_factory=set)

    def fit(self) -> CollaborativeFilteringRecommender:
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(
            self.train_df[["user_id", "recipe_id", "rating"]],
            reader,
        )
        self.trainset = data.build_full_trainset()
        self.model.fit(self.trainset)
        self.recipe_ids = set(self.train_df["recipe_id"].astype(int))
        return self

    def predict_rating(self, user_id: int, recipe_id: int) -> float:
        try:
            pred = self.model.predict(int(user_id), int(recipe_id)).est
            return float(pred) if pred is not None else 3.0
        except Exception:
            return 3.0

    def rmse(self, test_df: pd.DataFrame) -> float:
        train_users = set(self.train_df["user_id"].astype(int))
        train_recipes = set(self.train_df["recipe_id"].astype(int))
        filtered = test_df[
            test_df["user_id"].astype(int).isin(train_users)
            & test_df["recipe_id"].astype(int).isin(train_recipes)
        ]
        if filtered.empty:
            return float("nan")
        predictions = [
            self.model.predict(int(r.user_id), int(r.recipe_id))
            for r in filtered.itertuples(index=False)
        ]
        predictions = [p for p in predictions if p.est is not None]
        if not predictions:
            return float("nan")
        return float(accuracy.rmse(predictions, verbose=False))

    def recommend_for_user(
        self,
        user_id: int,
        candidate_recipe_ids: list[int] | None = None,
        top_k: int = 10,
    ) -> pd.DataFrame:
        if candidate_recipe_ids is None:
            candidate_recipe_ids = list(self.recipe_ids)

        rows = [
            {"recipe_id": rid, "score": self.predict_rating(user_id, rid)}
            for rid in candidate_recipe_ids
        ]
        df = pd.DataFrame(rows)
        return df.sort_values("score", ascending=False).head(top_k)
