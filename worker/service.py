"""Polling worker with job leases, heartbeats, retries, and cleanup."""

from __future__ import annotations

import logging
import threading

from evaluation_core.datasets import DatasetValidationError
from worker.domain import CleanupLease, JobLease, JobRepository, LeaseLostError
from worker.processor import EvaluationProcessor
from worker.storage import BlobSizeLimitError


LOGGER = logging.getLogger(__name__)



class LeaseHeartbeat:
    def __init__(
        self,
        repository: JobRepository,
        job: JobLease,
        lease_seconds: int,
    ):
        self._repository = repository
        self._job = job
        self._lease_seconds = lease_seconds
        self._interval = max(1.0, lease_seconds / 3)
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        self._thread = threading.Thread(
            target=self._run,
            name=f"lease-heartbeat-{self._job.job_id}",
            daemon=True,
        )
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                if not self._repository.heartbeat(
                    self._job,
                    self._lease_seconds,
                ):
                    self._lost.set()
                    return
            except Exception:
                LOGGER.exception("Job heartbeat failed")
                self._lost.set()
                return

    def ensure_owned(self) -> None:
        if self._lost.is_set():
            raise LeaseLostError(f"Lease lost for job {self._job.job_id}")

    def __exit__(self, _exc_type, _exc, _traceback):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)


class WorkerService:
    def __init__(
        self,
        repository: JobRepository,
        processor: EvaluationProcessor,
        blob_store,
        *,
        lease_seconds: int = 900,
        retry_delay_seconds: int = 60,
        cleanup_batch_size: int = 100,
    ):
        self._repository = repository
        self._processor = processor
        self._blob_store = blob_store
        self._lease_seconds = lease_seconds
        self._retry_delay_seconds = retry_delay_seconds
        self._cleanup_batch_size = cleanup_batch_size

    def _process_job(self, job: JobLease) -> None:
        try:
            with LeaseHeartbeat(
                self._repository,
                job,
                self._lease_seconds,
            ) as heartbeat:
                results = self._processor.process(job)
                heartbeat.ensure_owned()
                self._repository.complete_job(job, results)
        except LeaseLostError:
            LOGGER.warning("Stopped work after lease loss for job %s", job.job_id)
        except Exception as exc:
            non_retryable = isinstance(
                exc,
                (DatasetValidationError, BlobSizeLimitError),
            )
            LOGGER.exception("Evaluation job %s failed", job.job_id)
            self._repository.fail_job(
                job,
                error_code=type(exc).__name__,
                error_message=str(exc)[:2000],
                retryable=not non_retryable,
                retry_delay_seconds=self._retry_delay_seconds,
            )

    def _process_cleanup(self, cleanup: CleanupLease) -> None:
        try:
            self._blob_store.delete(cleanup.blob_url)
            self._repository.complete_cleanup(cleanup)
        except Exception as exc:
            LOGGER.exception("Blob cleanup %s failed", cleanup.cleanup_id)
            self._repository.fail_cleanup(
                cleanup,
                str(exc)[:2000],
                self._retry_delay_seconds,
            )

    def run_once(self) -> bool:
        self._repository.queue_expired_cleanup(self._cleanup_batch_size)

        job = self._repository.claim_job(self._lease_seconds)
        if job is not None:
            self._process_job(job)
            return True

        cleanup = self._repository.claim_cleanup(self._lease_seconds)
        if cleanup is not None:
            self._process_cleanup(cleanup)
            return True

        return False

    def run_until_idle(self, max_items: int = 10) -> int:
        processed = 0
        while processed < max_items and self.run_once():
            processed += 1
        return processed

    def run_forever(
        self,
        stop_event: threading.Event,
        poll_seconds: float = 2.0,
    ) -> None:
        while not stop_event.is_set():
            worked = self.run_once()
            if not worked:
                stop_event.wait(poll_seconds)
