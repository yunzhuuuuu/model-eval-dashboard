"""Evaluation job processing independent of queue and database implementations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from evaluation_core.datasets import parse_csv_dataset
from evaluation_core.metrics import (
    metrics_from_positions,
    relevant_positions_from_embeddings,
)
from worker.domain import (
    BlobStore,
    EmbeddingProviders,
    JobLease,
    JobRepository,
    ModelResult,
)


@dataclass(frozen=True)
class ProcessorLimits:
    max_upload_bytes: int = 10 * 1024 * 1024
    max_contexts: int = 10_000
    max_questions: int = 10_000


class EvaluationProcessor:
    LOCAL_MODELS = (
        ("all-mpnet-base-v2", "all-mpnet-base-v2"),
        ("multi-qa-MiniLM-L6-dot-v1", "multi-qa-MiniLM-L6-dot-v1"),
    )

    def __init__(
        self,
        repository: JobRepository,
        blob_store: BlobStore,
        providers: EmbeddingProviders,
        *,
        lease_seconds: int,
        limits: ProcessorLimits | None = None,
    ):
        self._repository = repository
        self._blob_store = blob_store
        self._providers = providers
        self._lease_seconds = lease_seconds
        self._limits = limits or ProcessorLimits()

    def _progress(
        self,
        job: JobLease,
        stage: str,
        completed: int,
        total: int,
    ) -> None:
        self._repository.set_progress(
            job,
            stage,
            completed,
            total,
            self._lease_seconds,
        )

    @staticmethod
    def _result(
        model_name: str,
        question_embeddings: np.ndarray,
        context_embeddings: np.ndarray,
        most_relevant: np.ndarray,
    ) -> ModelResult:
        positions = relevant_positions_from_embeddings(
            question_embeddings,
            context_embeddings,
            most_relevant,
        )
        metrics = {
            name: round(value, 4)
            for name, value in metrics_from_positions(positions).items()
        }
        return ModelResult(model_name=model_name, metrics=metrics)

    def process(self, job: JobLease) -> list[ModelResult]:
        total_steps = 8
        self._progress(job, "downloading_uploads", 0, total_steps)
        context_csv = self._blob_store.read_bytes(
            job.context_blob_url,
            self._limits.max_upload_bytes,
        )
        qanda_csv = self._blob_store.read_bytes(
            job.qanda_blob_url,
            self._limits.max_upload_bytes,
        )

        self._progress(job, "validating_dataset", 1, total_steps)
        dataset = parse_csv_dataset(
            context_csv,
            qanda_csv,
            max_contexts=self._limits.max_contexts,
            max_questions=self._limits.max_questions,
        )
        questions = list(dataset.questions)
        contexts = list(dataset.contexts)
        truth = np.asarray(dataset.most_relevant)
        self._repository.set_dataset_counts(
            job,
            context_count=len(contexts),
            question_count=len(questions),
        )

        results: list[ModelResult] = []

        self._progress(job, "embedding_gemini", 2, total_steps)
        gemini_questions = np.asarray(self._providers.embed_gemini(questions))
        gemini_contexts = np.asarray(self._providers.embed_gemini(contexts))
        results.append(
            self._result(
                "gemini_3072",
                gemini_questions,
                gemini_contexts,
                truth,
            )
        )
        self._progress(job, "evaluated_gemini", 4, total_steps)

        completed = 4
        for result_name, model_id in self.LOCAL_MODELS:
            self._progress(
                job,
                f"embedding_{result_name}",
                completed,
                total_steps,
            )
            question_embeddings = np.asarray(
                self._providers.embed_sentence_transformer(model_id, questions)
            )
            context_embeddings = np.asarray(
                self._providers.embed_sentence_transformer(model_id, contexts)
            )
            results.append(
                self._result(
                    result_name,
                    question_embeddings,
                    context_embeddings,
                    truth,
                )
            )
            completed += 2
            self._progress(
                job,
                f"evaluated_{result_name}",
                completed,
                total_steps,
            )

        return results
