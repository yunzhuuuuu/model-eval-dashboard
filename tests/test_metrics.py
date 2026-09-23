from __future__ import annotations

import unittest

import numpy as np

from evaluation_core.metrics import compute_metric, rank_by_cosine_similarity, relevant_positions


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.rankings = np.array([[0, 1, 2], [2, 0, 1], [1, 2, 0]])
        self.truth = np.array([0, 0, 0])

    def test_metric_values(self):
        self.assertAlmostEqual(compute_metric("Recall@1", self.rankings, self.truth), 1 / 3)
        self.assertAlmostEqual(compute_metric("Recall@3", self.rankings, self.truth), 1.0)
        self.assertAlmostEqual(compute_metric("Mean Rank", self.rankings, self.truth), 2.0)
        self.assertAlmostEqual(
            compute_metric("MRR", self.rankings, self.truth), (1 + 0.5 + 1 / 3) / 3
        )

    def test_cosine_ranking(self):
        questions = np.array([[1.0, 0.0], [0.0, 1.0]])
        contexts = np.array([[0.0, 1.0], [1.0, 0.0]])
        rankings = rank_by_cosine_similarity(questions, contexts)
        np.testing.assert_array_equal(rankings, np.array([[1, 0], [0, 1]]))

    def test_missing_relevant_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly once"):
            relevant_positions(np.array([[0, 1]]), np.array([2]))

    def test_unknown_metric_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown metric"):
            compute_metric("NDCG", self.rankings, self.truth)


if __name__ == "__main__":
    unittest.main()
