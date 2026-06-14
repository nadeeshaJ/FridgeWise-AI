"""Hybrid recommender combining content, CF, expiry, and nutrition signals."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.models.collaborative_filtering import CollaborativeFilteringRecommender
from src.models.content_based import ContentBasedRecommender, _split_pipe


def _normalize_rating(rating: float) -> float:
    return (float(rating) - 1.0) / 4.0


@dataclass
class HybridRecommender:
    content_model: ContentBasedRecommender
    cf_model: CollaborativeFilteringRecommender | None
    recipes_df: pd.DataFrame
    fridge_df: pd.DataFrame
    products_df: pd.DataFrame
    weights: dict

    def _fridge_context(self, user_id: int) -> tuple[set[str], dict[str, float]]:
        items = self.fridge_df[self.fridge_df["user_id"] == user_id]
        ingredients = set(items["cleaned_ingredient_name"].astype(str))
        expiry_map = dict(
            zip(items["cleaned_ingredient_name"], items["expiry_priority_score"])
        )
        return ingredients, expiry_map

    def _nutrition_score(self, recipe_id: int) -> float:
        recipe = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id]
        if recipe.empty:
            return 0.5
        ings = _split_pipe(recipe.iloc[0]["cleaned_ingredients"])
        if not ings:
            return 0.5
        lookup = self.products_df.groupby("generic_ingredient_name")["nutrition_score"].mean().to_dict()
        scores = [lookup[i] for i in ings if i in lookup]
        return float(sum(scores) / len(scores)) if scores else 0.5

    def _expiry_score(self, recipe_id: int, expiry_map: dict[str, float], fridge_ings: set[str]) -> float:
        recipe = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id]
        if recipe.empty:
            return 0.0
        matched = _split_pipe(recipe.iloc[0]["cleaned_ingredients"]) & fridge_ings
        values = [expiry_map[i] for i in matched if i in expiry_map]
        return float(max(values)) if values else 0.0

    def recommend(
        self,
        user_id: int,
        top_k: int = 10,
        train_user_ids: set[int] | None = None,
        fridge_ingredients: set[str] | None = None,
    ) -> pd.DataFrame:
        if fridge_ingredients is not None:
            fridge_ings = fridge_ingredients
            expiry_map = {}
        else:
            fridge_ings, expiry_map = self._fridge_context(user_id)
        is_cold_start = train_user_ids is not None and user_id not in train_user_ids

        content_scores = self.content_model.recommend(fridge_ings, top_k=500)
        if content_scores.empty:
            return content_scores

        rows = []
        for _, row in content_scores.iterrows():
            recipe_id = int(row["recipe_id"])
            ingredient_match = float(row["score"])

            if is_cold_start or self.cf_model is None:
                expiry = self._expiry_score(recipe_id, expiry_map, fridge_ings)
                nutrition = self._nutrition_score(recipe_id)
                final = (
                    self.weights["cold_start_ingredient_match"] * ingredient_match
                    + self.weights["cold_start_expiry"] * expiry
                    + self.weights["cold_start_nutrition"] * nutrition
                )
            else:
                pred = self.cf_model.predict_rating(user_id, recipe_id)
                expiry = self._expiry_score(recipe_id, expiry_map, fridge_ings)
                nutrition = self._nutrition_score(recipe_id)
                final = (
                    self.weights["ingredient_match"] * ingredient_match
                    + self.weights["predicted_rating"] * _normalize_rating(pred)
                    + self.weights["expiry_priority"] * expiry
                    + self.weights["nutrition"] * nutrition
                )

            recipe_row = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id].iloc[0]
            recipe_ings = _split_pipe(recipe_row["cleaned_ingredients"])
            matched = recipe_ings & fridge_ings

            rows.append(
                {
                    "recipe_id": recipe_id,
                    "recipe_name": recipe_row["recipe_name"],
                    "score": final,
                    "ingredient_match_score": ingredient_match,
                    "expiry_priority_score": self._expiry_score(recipe_id, expiry_map, fridge_ings),
                    "nutrition_score": self._nutrition_score(recipe_id),
                    "matched_ingredients": "|".join(sorted(matched)),
                    "missing_ingredients": "|".join(sorted(recipe_ings - fridge_ings)),
                    "minutes": int(recipe_row["minutes"]),
                    "cold_start": is_cold_start,
                }
            )

        return pd.DataFrame(rows).sort_values("score", ascending=False).head(top_k)
