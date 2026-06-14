"""Unit tests for ranking evaluation metrics."""

from src.evaluation.metrics import (
    average_precision,
    dcg_at_k,
    map_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_k():
    assert precision_at_k([1, 2, 3, 4, 5], {2, 4}, 5) == 0.4
    assert precision_at_k([], {1}, 5) == 0.0


def test_recall_at_k():
    assert recall_at_k([1, 2, 3], {2, 5}, 3) == 0.5


def test_average_precision_perfect_ranking():
    assert average_precision([10, 20], {10, 20}, 5) == 1.0


def test_map_at_k():
    recs = {1: [10, 11, 12], 2: [20, 21, 22]}
    rel = {1: {10}, 2: {21, 22}}
    assert 0.0 < map_at_k(recs, rel, 3) <= 1.0


def test_dcg_and_ndcg():
    recs = {1: [10, 11, 12]}
    rel = {1: {10}}
    assert dcg_at_k([10, 11], {10}, 2) == 1.0
    assert ndcg_at_k(recs, rel, 3) == 1.0
