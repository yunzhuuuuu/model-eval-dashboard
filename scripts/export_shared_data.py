"""Export the existing example datasets as static assets for the Next.js app."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np

from evaluation_core.metrics import (
    AVAILABLE_METRICS,
    compute_metric,
    rank_by_cosine_similarity,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets"
EMBEDDING_DIR = ROOT / "embeddings"
OUTPUT_DIR = ROOT / "public" / "data"
EXAMPLE_DIR = ROOT / "public" / "examples"
MODELS = (
    "gemini_3072",
    "all-mpnet-base-v2",
    "multi-qa-MiniLM-L6-dot-v1",
)


def model_results(dataset_name: str, truth: np.ndarray) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for model in MODELS:
        question_path = EMBEDDING_DIR / f"{dataset_name}_questions_{model}.npz"
        context_path = EMBEDDING_DIR / f"{dataset_name}_contexts_{model}.npz"
        if not question_path.exists() or not context_path.exists():
            continue
        question_embeddings = np.load(question_path)["embeddings"]
        context_embeddings = np.load(context_path)["embeddings"]
        rankings = rank_by_cosine_similarity(
            question_embeddings,
            context_embeddings,
        )
        results.append(
            {
                "modelName": model,
                "metrics": {
                    metric: round(compute_metric(metric, rankings, truth), 4)
                    for metric in AVAILABLE_METRICS
                },
            }
        )
    return results


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, list[dict[str, object]]] = {}

    for dataset_path in sorted(DATASET_DIR.glob("*.npz")):
        dataset_name = dataset_path.stem
        dataset = np.load(dataset_path)
        truth = dataset["most_relevant_context"]
        payload = {
            "questions": dataset["questions"].tolist(),
            "contexts": dataset["contexts"].tolist(),
            "mostRelevant": truth.astype(int).tolist(),
        }
        output_path = OUTPUT_DIR / f"{dataset_name}.json"
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        all_results[dataset_name] = model_results(dataset_name, truth)

    (OUTPUT_DIR / "shared-results.json").write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.copyfile(ROOT / "assets" / "contexts.png", EXAMPLE_DIR / "contexts.png")
    shutil.copyfile(ROOT / "assets" / "qanda.png", EXAMPLE_DIR / "qanda.png")


if __name__ == "__main__":
    main()
