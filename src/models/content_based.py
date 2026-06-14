"""Baseline content-based recommender using ingredient overlap and TF-IDF."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def _split_pipe(value: str) -> set[str]:
    if not value or (isinstance(value, float) and np.isnan(value)):
        return set()
    return {x for x in str(value).split("|") if x}


@dataclass
class ContentBasedRecommender:
    recipes_df: pd.DataFrame
    vectorizer: TfidfVectorizer | None = None
    tfidf_matrix: np.ndarray | None = None
    recipe_ids: np.ndarray | None = None

    def fit(self) -> ContentBasedRecommender:
        corpus = self.recipes_df["cleaned_ingredients"].fillna("").astype(str)
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.recipe_ids = self.recipes_df["recipe_id"].to_numpy()
        return self

    def ingredient_match_scores(self, fridge_ingredients: set[str]) -> pd.DataFrame:
        if not fridge_ingredients:
            return pd.DataFrame(columns=["recipe_id", "score"])

        rows = []
        for _, recipe in self.recipes_df.iterrows():
            recipe_ings = _split_pipe(recipe["cleaned_ingredients"])
            if not recipe_ings:
                continue
            matched = recipe_ings & fridge_ingredients
            rows.append(
                {
                    "recipe_id": int(recipe["recipe_id"]),
                    "score": len(matched) / len(recipe_ings),
                }
            )
        return pd.DataFrame(rows)

    def tfidf_scores(self, fridge_ingredients: set[str], top_n: int = 500) -> pd.DataFrame:
        if not fridge_ingredients or self.vectorizer is None or self.tfidf_matrix is None:
            return pd.DataFrame(columns=["recipe_id", "score"])

        query = " ".join(sorted(fridge_ingredients))
        query_vec = self.vectorizer.transform([query])
        sims = linear_kernel(query_vec, self.tfidf_matrix).flatten()
        order = np.argsort(-sims)[:top_n]
        return pd.DataFrame(
            {
                "recipe_id": self.recipe_ids[order],
                "score": sims[order],
            }
        )

    def recommend(
        self,
        fridge_ingredients: set[str],
        top_k: int = 10,
        tfidf_weight: float = 0.4,
        candidate_pool: int = 500,
    ) -> pd.DataFrame:
        if not fridge_ingredients:
            return pd.DataFrame(columns=["recipe_id", "score"])

        tfidf = self.tfidf_scores(fridge_ingredients, top_n=candidate_pool)
        if tfidf.empty:
            return tfidf

        candidate_ids = set(tfidf["recipe_id"].astype(int))
        subset = self.recipes_df[self.recipes_df["recipe_id"].isin(candidate_ids)]
        rows = []
        for _, recipe in subset.iterrows():
            recipe_ings = _split_pipe(recipe["cleaned_ingredients"])
            if not recipe_ings:
                continue
            matched = recipe_ings & fridge_ingredients
            rows.append(
                {
                    "recipe_id": int(recipe["recipe_id"]),
                    "score_overlap": len(matched) / len(recipe_ings),
                }
            )
        overlap = pd.DataFrame(rows)
        merged = overlap.merge(tfidf.rename(columns={"score": "score_tfidf"}), on="recipe_id", how="inner")
        max_tfidf = merged["score_tfidf"].max() or 1.0
        merged["score"] = (1 - tfidf_weight) * merged["score_overlap"] + tfidf_weight * (
            merged["score_tfidf"] / max_tfidf
        )
        return merged.sort_values("score", ascending=False).head(top_k)[["recipe_id", "score"]]
