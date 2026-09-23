from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from evaluation_core.metrics import compute_metric, rank_by_cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
BASELINES = json.loads((ROOT / "tests" / "fixtures" / "baseline_metrics.json").read_text())


class LocalArtifactParityTests(unittest.TestCase):
    def test_available_local_artifacts_match_recorded_baselines(self):
        compared = 0
        for dataset_name, model_results in BASELINES.items():
            dataset_path = ROOT / "datasets" / f"{dataset_name}.npz"
            if not dataset_path.exists():
                continue
            dataset = np.load(dataset_path)
            truth = dataset["most_relevant_context"]

            for model_name, expected_metrics in model_results.items():
                question_path = ROOT / "embeddings" / f"{dataset_name}_questions_{model_name}.npz"
                context_path = ROOT / "embeddings" / f"{dataset_name}_contexts_{model_name}.npz"
                if not question_path.exists() or not context_path.exists():
                    continue
                questions = np.load(question_path)["embeddings"]
                contexts = np.load(context_path)["embeddings"]
                rankings = rank_by_cosine_similarity(questions, contexts)
                for metric_name, expected in expected_metrics.items():
                    actual = round(compute_metric(metric_name, rankings, truth), 4)
                    self.assertEqual(
                        actual,
                        expected,
                        f"{dataset_name}/{model_name}/{metric_name}",
                    )
                compared += 1

        if compared == 0:
            self.skipTest("No local baseline artifacts are available.")


if __name__ == "__main__":
    unittest.main()
