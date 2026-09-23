from __future__ import annotations

import unittest
from uuid import uuid4

from evaluation_core.datasets import DatasetValidationError
from worker.domain import CleanupLease, JobLease, ModelResult
from worker.service import WorkerService


def make_job():
    return JobLease(
        job_id=uuid4(),
        dataset_id=uuid4(),
        lease_token=uuid4(),
        dataset_name="demo",
        context_blob_url="context",
        qanda_blob_url="qanda",
        attempt_count=1,
        max_attempts=3,
    )


class FakeRepository:
    def __init__(self, job=None, cleanup=None):
        self.job = job
        self.cleanup = cleanup
        self.completed = None
        self.failed = None
        self.cleanup_completed = None

    def queue_expired_cleanup(self, batch_size):
        self.cleanup_batch_size = batch_size
        return 0

    def claim_job(self, lease_seconds):
        job, self.job = self.job, None
        return job

    def heartbeat(self, job, lease_seconds):
        return True

    def complete_job(self, job, results):
        self.completed = (job, results)

    def fail_job(self, job, **options):
        self.failed = (job, options)

    def claim_cleanup(self, lease_seconds):
        cleanup, self.cleanup = self.cleanup, None
        return cleanup

    def complete_cleanup(self, cleanup):
        self.cleanup_completed = cleanup

    def fail_cleanup(self, cleanup, error_message, retry_delay_seconds):
        self.cleanup_failed = (cleanup, error_message, retry_delay_seconds)


class FakeProcessor:
    def __init__(self, error=None):
        self.error = error

    def process(self, job):
        if self.error:
            raise self.error
        return [ModelResult("model", {"Recall@1": 1.0})]


class FakeBlobStore:
    def __init__(self, delete_error=None):
        self.deleted = []
        self.delete_error = delete_error

    def delete(self, url):
        if self.delete_error:
            raise self.delete_error
        self.deleted.append(url)


class WorkerServiceTests(unittest.TestCase):
    def test_completes_successful_job(self):
        repository = FakeRepository(job=make_job())
        service = WorkerService(
            repository,
            FakeProcessor(),
            FakeBlobStore(),
            lease_seconds=30,
        )

        self.assertTrue(service.run_once())
        self.assertIsNotNone(repository.completed)
        self.assertIsNone(repository.failed)

    def test_validation_failure_is_not_retried(self):
        repository = FakeRepository(job=make_job())
        service = WorkerService(
            repository,
            FakeProcessor(DatasetValidationError("bad csv")),
            FakeBlobStore(),
            lease_seconds=30,
        )

        self.assertTrue(service.run_once())
        self.assertFalse(repository.failed[1]["retryable"])

    def test_unexpected_failure_is_retried(self):
        repository = FakeRepository(job=make_job())
        service = WorkerService(
            repository,
            FakeProcessor(RuntimeError("temporary")),
            FakeBlobStore(),
            lease_seconds=30,
        )

        self.assertTrue(service.run_once())
        self.assertTrue(repository.failed[1]["retryable"])

    def test_deletes_claimed_blob(self):
        cleanup = CleanupLease(
            cleanup_id=uuid4(),
            dataset_id=uuid4(),
            lease_token=uuid4(),
            blob_url="private-blob",
            attempt_count=1,
            max_attempts=5,
        )
        repository = FakeRepository(cleanup=cleanup)
        storage = FakeBlobStore()
        service = WorkerService(
            repository,
            FakeProcessor(),
            storage,
            lease_seconds=30,
        )

        self.assertTrue(service.run_once())
        self.assertEqual(storage.deleted, ["private-blob"])
        self.assertEqual(repository.cleanup_completed, cleanup)

    def test_drain_stops_when_queue_is_empty(self):
        repository = FakeRepository(job=make_job())
        service = WorkerService(
            repository,
            FakeProcessor(),
            FakeBlobStore(),
            lease_seconds=30,
        )

        self.assertEqual(service.run_until_idle(max_items=5), 1)
        self.assertIsNotNone(repository.completed)
        self.assertIsNone(repository.job)


if __name__ == "__main__":
    unittest.main()
