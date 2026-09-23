"""Reusable embedding helpers with progress and retry callbacks."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import time
from typing import Any

import numpy as np


RetryCallback = Callable[[int, Exception], None]
RetryPredicate = Callable[[Exception], bool]
SleepFunction = Callable[[float], None]


def embed_gemini_batches(
    client: Any,
    texts: Sequence[str],
    *,
    model: str = "gemini-embedding-001",
    batch_size: int = 99,
    retry_delay_seconds: int = 60,
    is_retryable: RetryPredicate | None = None,
    on_retry_countdown: RetryCallback | None = None,
    sleep: SleepFunction = time.sleep,
    max_retries: int | None = None,
) -> np.ndarray:
    """Embed text batches while allowing the caller to control retry presentation."""

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    retryable = is_retryable or (
        lambda error: "RESOURCE_EXHAUSTED" in str(error)
    )
    batches: list[np.ndarray] = []

    for start in range(0, len(texts), batch_size):
        batch = list(texts[start : start + batch_size])
        retry_count = 0
        while True:
            try:
                result = client.models.embed_content(model=model, contents=batch)
                break
            except Exception as exc:
                if not retryable(exc):
                    raise
                retry_count += 1
                if max_retries is not None and retry_count > max_retries:
                    raise
                for remaining in range(retry_delay_seconds, 0, -1):
                    if on_retry_countdown is not None:
                        on_retry_countdown(remaining, exc)
                    sleep(1)

        values = np.asarray([embedding.values for embedding in result.embeddings])
        if values.shape[0] != len(batch):
            raise ValueError(
                "The embedding provider returned a different number of vectors than inputs."
            )
        batches.append(values)

    return np.concatenate(batches, axis=0)


def encode_sentence_transformer(
    model: Any,
    texts: Sequence[str],
    *,
    show_progress_bar: bool = True,
) -> np.ndarray:
    """Encode texts using an already-loaded SentenceTransformer-compatible model."""

    return np.asarray(
        model.encode(
            list(texts),
            convert_to_numpy=True,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=True,
        )
    )
