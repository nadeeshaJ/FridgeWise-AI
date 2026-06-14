"""Offline ranking and rating evaluation metrics."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np


def _dedupe_preserve_order(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def precision_at_k(recommended: list, relevant: set, k: int) -> float:
    if k <= 0:
        return 0.0
    rec_k = _dedupe_preserve_order(recommended)[:k]
    if not rec_k:
        return 0.0
    hits = sum(1 for item in rec_k if item in relevant)
    return hits / k


def recall_at_k(recommended: list, relevant: set, k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    rec_k = _dedupe_preserve_order(recommended)[:k]
    hits = sum(1 for item in rec_k if item in relevant)
    return hits / len(relevant)


def average_precision(recommended: list, relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    rec_k = _dedupe_preserve_order(recommended)[:k]
    hits = 0
    score = 0.0
    for i, item in enumerate(rec_k, start=1):
        if item in relevant:
            hits += 1
            score += hits / i
    return score / min(len(relevant), k)


def map_at_k(all_recommended: dict[int, list], all_relevant: dict[int, set], k: int) -> float:
    users = [u for u in all_relevant if all_relevant[u]]
    if not users:
        return 0.0
    return float(np.mean([average_precision(all_recommended.get(u, []), all_relevant[u], k) for u in users]))


def dcg_at_k(recommended: list, relevant: set, k: int) -> float:
    rec_k = _dedupe_preserve_order(recommended)[:k]
    dcg = 0.0
    for i, item in enumerate(rec_k, start=1):
        rel = 1.0 if item in relevant else 0.0
        dcg += rel / math.log2(i + 1)
    return dcg


def ndcg_at_k(all_recommended: dict[int, list], all_relevant: dict[int, set], k: int) -> float:
    users = [u for u in all_relevant if all_relevant[u]]
    if not users:
        return 0.0

    scores = []
    for user in users:
        recommended = all_recommended.get(user, [])
        relevant = all_relevant[user]
        dcg = dcg_at_k(recommended, relevant, k)
        ideal = dcg_at_k(list(relevant), relevant, min(k, len(relevant)))
        scores.append(dcg / ideal if ideal > 0 else 0.0)
    return float(np.mean(scores))


def build_relevance_map(interactions_df, min_rating: float = 4.0) -> dict[int, set[int]]:
    relevant: dict[int, set[int]] = defaultdict(set)
    for row in interactions_df.itertuples(index=False):
        if float(row.rating) >= min_rating:
            relevant[int(row.user_id)].add(int(row.recipe_id))
    return dict(relevant)
