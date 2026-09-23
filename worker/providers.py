"""Lazy, reusable model providers for worker processes."""

from __future__ import annotations

import logging

import numpy as np

from evaluation_core.embeddings import (
    embed_gemini_batches,
    encode_sentence_transformer,
)


LOGGER = logging.getLogger(__name__)


class CachedEmbeddingProviders:
    """Keep heavyweight local models resident between evaluation jobs."""

    def __init__(
        self,
        gemini_api_key: str,
        *,
        gemini_batch_size: int = 99,
        gemini_retry_delay_seconds: int = 60,
        gemini_retries_per_job: int = 2,
    ):
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required.")
        self._gemini_api_key = gemini_api_key
        self._gemini_batch_size = gemini_batch_size
        self._gemini_retry_delay_seconds = gemini_retry_delay_seconds
        self._gemini_retries_per_job = gemini_retries_per_job
        self._gemini_client = None
        self._sentence_models: dict[str, object] = {}

    def _get_gemini_client(self):
        if self._gemini_client is None:
            from google import genai

            self._gemini_client = genai.Client(api_key=self._gemini_api_key)
        return self._gemini_client

    def _get_sentence_model(self, model_id: str):
        if model_id not in self._sentence_models:
            from sentence_transformers import SentenceTransformer

            LOGGER.info("Loading sentence-transformer model %s", model_id)
            self._sentence_models[model_id] = SentenceTransformer(model_id)
        return self._sentence_models[model_id]

    def embed_gemini(self, texts: list[str]) -> np.ndarray:
        return embed_gemini_batches(
            self._get_gemini_client(),
            texts,
            batch_size=self._gemini_batch_size,
            retry_delay_seconds=self._gemini_retry_delay_seconds,
            max_retries=self._gemini_retries_per_job,
            on_retry_countdown=lambda remaining, error: LOGGER.warning(
                "Gemini quota retry in %s seconds: %s",
                remaining,
                error,
            ),
        )

    def embed_sentence_transformer(
        self,
        model_id: str,
        texts: list[str],
    ) -> np.ndarray:
        return encode_sentence_transformer(
            self._get_sentence_model(model_id),
            texts,
            show_progress_bar=False,
        )
