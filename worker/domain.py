"""Domain models and service contracts for the evaluation worker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class LeaseLostError(RuntimeError):
    """Raised when another worker has reclaimed an expired lease."""


@dataclass(frozen=True)
class JobLease:
    job_id: UUID
    dataset_id: UUID
    lease_token: UUID
    dataset_name: str
    context_blob_url: str
    qanda_blob_url: str
    attempt_count: int
    max_attempts: int


@dataclass(frozen=True)
class ModelResult:
    model_name: str
    metrics: dict[str, float]


@dataclass(frozen=True)
class CleanupLease:
    cleanup_id: UUID
    dataset_id: UUID | None
    lease_token: UUID
    blob_url: str
    attempt_count: int
    max_attempts: int


class JobRepository(Protocol):
    def claim_job(self, lease_seconds: int) -> JobLease | None: ...

    def heartbeat(self, job: JobLease, lease_seconds: int) -> bool: ...

    def set_progress(
        self,
        job: JobLease,
        stage: str,
        completed: int,
        total: int,
        lease_seconds: int,
    ) -> None: ...

    def set_dataset_counts(
        self,
        job: JobLease,
        context_count: int,
        question_count: int,
    ) -> None: ...

    def complete_job(self, job: JobLease, results: list[ModelResult]) -> None: ...

    def fail_job(
        self,
        job: JobLease,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        retry_delay_seconds: int,
    ) -> None: ...

    def queue_expired_cleanup(self, batch_size: int) -> int: ...

    def claim_cleanup(self, lease_seconds: int) -> CleanupLease | None: ...

    def complete_cleanup(self, cleanup: CleanupLease) -> None: ...

    def fail_cleanup(
        self,
        cleanup: CleanupLease,
        error_message: str,
        retry_delay_seconds: int,
    ) -> None: ...


class BlobStore(Protocol):
    def read_bytes(self, url: str, max_bytes: int) -> bytes: ...

    def delete(self, url: str) -> None: ...


class EmbeddingProviders(Protocol):
    def embed_gemini(self, texts: list[str]) -> object: ...

    def embed_sentence_transformer(
        self,
        model_id: str,
        texts: list[str],
    ) -> object: ...
