"""Retrieval ranking and evaluation metrics with no UI dependencies."""

from __future__ import annotations

import numpy as np


AVAILABLE_METRICS = ("Recall@1", "Recall@3", "Mean Rank", "MRR")


def _matrix(values: np.ndarray, label: str) -> np.ndarray:
    matrix = np.asarray(values)
    if matrix.ndim != 2:
        raise ValueError(f"{label} must be a two-dimensional matrix.")
    if matrix.shape[0] == 0:
        raise ValueError(f"{label} must contain at least one row.")
    return matrix


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = matrix.astype(np.float64, copy=False)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe_norms = np.where(norms == 0, 1.0, norms)
    return matrix / safe_norms


def rank_by_cosine_similarity(
    question_embeddings: np.ndarray,
    context_embeddings: np.ndarray,
) -> np.ndarray:
    """Return context indices ordered from most to least similar per question."""

    questions = _matrix(question_embeddings, "question_embeddings")
    contexts = _matrix(context_embeddings, "context_embeddings")
    if questions.shape[1] != contexts.shape[1]:
        raise ValueError(
            "Question and context embeddings must have the same vector dimension."
        )

    similarities = _normalize_rows(questions) @ _normalize_rows(contexts).T
    return np.argsort(-similarities, axis=1).astype(np.int32, copy=False)


def relevant_positions_from_embeddings(
    question_embeddings: np.ndarray,
    context_embeddings: np.ndarray,
    most_relevant: np.ndarray,
    *,
    chunk_size: int = 128,
) -> np.ndarray:
    """Return relevant ranks without allocating the full similarity matrix."""

    questions = _matrix(question_embeddings, "question_embeddings")
    contexts = _matrix(context_embeddings, "context_embeddings")
    truth = np.asarray(most_relevant)
    if questions.shape[1] != contexts.shape[1]:
        raise ValueError(
            "Question and context embeddings must have the same vector dimension."
        )
    if truth.ndim != 1:
        raise ValueError("most_relevant must be a one-dimensional array.")
    if questions.shape[0] != truth.shape[0]:
        raise ValueError(
            "question_embeddings and most_relevant must contain the same questions."
        )
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1.")

    normalized_contexts = _normalize_rows(contexts)
    positions = np.empty(truth.size, dtype=np.int32)
    for start in range(0, questions.shape[0], chunk_size):
        end = min(start + chunk_size, questions.shape[0])
        similarities = _normalize_rows(questions[start:end]) @ normalized_contexts.T
        rankings = np.argsort(-similarities, axis=1).astype(np.int32, copy=False)
        positions[start:end] = relevant_positions(rankings, truth[start:end])
    return positions


def _validated_truth(
    rankings: np.ndarray,
    most_relevant: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rankings = np.asarray(rankings)
    truth = np.asarray(most_relevant)
    if rankings.ndim != 2:
        raise ValueError("rankings must be a two-dimensional matrix.")
    if truth.ndim != 1:
        raise ValueError("most_relevant must be a one-dimensional array.")
    if rankings.shape[0] != truth.shape[0]:
        raise ValueError("rankings and most_relevant must contain the same questions.")
    if truth.size == 0:
        raise ValueError("At least one question is required.")
    return rankings, truth


def relevant_positions(
    rankings: np.ndarray,
    most_relevant: np.ndarray,
) -> np.ndarray:
    """Return the one-indexed rank of each question's correct context."""

    rankings, truth = _validated_truth(rankings, most_relevant)
    positions = np.empty(truth.size, dtype=np.int32)
    for question_index, relevant_context in enumerate(truth):
        matches = np.flatnonzero(rankings[question_index] == relevant_context)
        if matches.size != 1:
            raise ValueError(
                f"Question {question_index} does not rank its relevant context exactly once."
            )
        positions[question_index] = int(matches[0]) + 1
    return positions


def metrics_from_positions(positions: np.ndarray) -> dict[str, float]:
    """Compute every supported metric from one-indexed relevant ranks."""

    values = np.asarray(positions)
    if values.ndim != 1:
        raise ValueError("positions must be a one-dimensional array.")
    if values.size == 0:
        raise ValueError("At least one relevant position is required.")
    if np.any(values < 1):
        raise ValueError("Relevant positions must be one-indexed positive values.")

    return {
        "Recall@1": float(np.mean(values <= 1)),
        "Recall@3": float(np.mean(values <= 3)),
        "Mean Rank": float(np.mean(values)),
        "MRR": float(np.mean(1.0 / values)),
    }


def recall_at_k(
    rankings: np.ndarray,
    most_relevant: np.ndarray,
    k: int,
) -> float:
    if k < 1:
        raise ValueError("k must be at least 1.")
    positions = relevant_positions(rankings, most_relevant)
    return float(np.mean(positions <= k))


def mean_reciprocal_rank(
    rankings: np.ndarray,
    most_relevant: np.ndarray,
) -> float:
    positions = relevant_positions(rankings, most_relevant)
    return float(np.mean(1.0 / positions))


def mean_rank(
    rankings: np.ndarray,
    most_relevant: np.ndarray,
) -> float:
    positions = relevant_positions(rankings, most_relevant)
    return float(np.mean(positions))


def compute_metric(
    metric_name: str,
    rankings: np.ndarray,
    most_relevant: np.ndarray,
) -> float:
    metric_functions = {
        "Recall@1": lambda: recall_at_k(rankings, most_relevant, 1),
        "Recall@3": lambda: recall_at_k(rankings, most_relevant, 3),
        "Mean Rank": lambda: mean_rank(rankings, most_relevant),
        "MRR": lambda: mean_reciprocal_rank(rankings, most_relevant),
    }
    try:
        return metric_functions[metric_name]()
    except KeyError as exc:
        raise ValueError(f"Unknown metric: {metric_name}") from exc
