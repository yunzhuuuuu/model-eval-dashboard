"""PostgreSQL implementation of worker job and cleanup leases."""

from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

from worker.domain import CleanupLease, JobLease, LeaseLostError, ModelResult


class RepositoryError(RuntimeError):
    """Base error for persistent job state failures."""



class PostgresJobRepository:
    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL is required.")
        self._database_url = database_url

    @contextmanager
    def _connection(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RepositoryError(
                "Install psycopg[binary] to use PostgresJobRepository."
            ) from exc

        with psycopg.connect(
            self._database_url,
            row_factory=dict_row,
        ) as connection:
            yield connection

    @staticmethod
    def _job_from_row(row) -> JobLease:
        return JobLease(
            job_id=row["job_id"],
            dataset_id=row["dataset_id"],
            lease_token=row["lease_token"],
            dataset_name=row["dataset_name"],
            context_blob_url=row["context_blob_url"],
            qanda_blob_url=row["qanda_blob_url"],
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
        )

    def claim_job(self, lease_seconds: int) -> JobLease | None:
        lease_token = uuid4()
        with self._connection() as connection:
            row = connection.execute(
                """
                WITH candidate AS (
                    SELECT id
                    FROM evaluation_jobs
                    WHERE attempt_count < max_attempts
                      AND (
                          (status = 'queued' AND run_after <= now())
                          OR (
                              status = 'running'
                              AND lease_expires_at <= now()
                          )
                      )
                    ORDER BY run_after, created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                ),
                claimed AS (
                    UPDATE evaluation_jobs jobs
                    SET status = 'running',
                        stage = 'starting',
                        attempt_count = jobs.attempt_count + 1,
                        lease_token = %(lease_token)s,
                        lease_expires_at = now() + make_interval(secs => %(lease_seconds)s),
                        last_heartbeat_at = now(),
                        started_at = COALESCE(jobs.started_at, now()),
                        error_code = NULL,
                        error_message = NULL
                    FROM candidate
                    WHERE jobs.id = candidate.id
                    RETURNING jobs.*
                )
                SELECT
                    claimed.id AS job_id,
                    claimed.dataset_id,
                    claimed.lease_token,
                    claimed.attempt_count,
                    claimed.max_attempts,
                    data.name AS dataset_name,
                    data.context_blob_url,
                    data.qanda_blob_url
                FROM claimed
                JOIN datasets data ON data.id = claimed.dataset_id
                WHERE data.deleted_at IS NULL
                """,
                {
                    "lease_token": lease_token,
                    "lease_seconds": lease_seconds,
                },
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE datasets
                SET status = 'processing'
                WHERE id = %(dataset_id)s
                """,
                {"dataset_id": row["dataset_id"]},
            )
            return self._job_from_row(row)

    def heartbeat(self, job: JobLease, lease_seconds: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE evaluation_jobs
                SET lease_expires_at = now() + make_interval(secs => %(lease_seconds)s),
                    last_heartbeat_at = now()
                WHERE id = %(job_id)s
                  AND lease_token = %(lease_token)s
                  AND status = 'running'
                """,
                {
                    "job_id": job.job_id,
                    "lease_token": job.lease_token,
                    "lease_seconds": lease_seconds,
                },
            )
            return cursor.rowcount == 1

    def set_progress(
        self,
        job: JobLease,
        stage: str,
        completed: int,
        total: int,
        lease_seconds: int,
    ) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE evaluation_jobs
                SET stage = %(stage)s,
                    progress_completed = %(completed)s,
                    progress_total = %(total)s,
                    lease_expires_at = now() + make_interval(secs => %(lease_seconds)s),
                    last_heartbeat_at = now()
                WHERE id = %(job_id)s
                  AND lease_token = %(lease_token)s
                  AND status = 'running'
                """,
                {
                    "stage": stage,
                    "completed": completed,
                    "total": total,
                    "lease_seconds": lease_seconds,
                    "job_id": job.job_id,
                    "lease_token": job.lease_token,
                },
            )
            if cursor.rowcount != 1:
                raise LeaseLostError(f"Lease lost for job {job.job_id}")

    def set_dataset_counts(
        self,
        job: JobLease,
        context_count: int,
        question_count: int,
    ) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE datasets data
                SET context_count = %(context_count)s,
                    question_count = %(question_count)s
                FROM evaluation_jobs jobs
                WHERE data.id = jobs.dataset_id
                  AND jobs.id = %(job_id)s
                  AND jobs.lease_token = %(lease_token)s
                  AND jobs.status = 'running'
                """,
                {
                    "context_count": context_count,
                    "question_count": question_count,
                    "job_id": job.job_id,
                    "lease_token": job.lease_token,
                },
            )
            if cursor.rowcount != 1:
                raise LeaseLostError(f"Lease lost for job {job.job_id}")

    def complete_job(self, job: JobLease, results: list[ModelResult]) -> None:
        with self._connection() as connection:
            owned = connection.execute(
                """
                SELECT dataset_id
                FROM evaluation_jobs
                WHERE id = %(job_id)s
                  AND lease_token = %(lease_token)s
                  AND status = 'running'
                FOR UPDATE
                """,
                {
                    "job_id": job.job_id,
                    "lease_token": job.lease_token,
                },
            ).fetchone()
            if owned is None:
                raise LeaseLostError(f"Lease lost for job {job.job_id}")

            try:
                from psycopg.types.json import Jsonb
            except ImportError as exc:
                raise RepositoryError(
                    "Install psycopg[binary] to persist evaluation results."
                ) from exc

            connection.execute(
                "DELETE FROM evaluation_results WHERE job_id = %(job_id)s",
                {"job_id": job.job_id},
            )
            for result in results:
                connection.execute(
                    """
                    INSERT INTO evaluation_results (
                        job_id,
                        dataset_id,
                        model_name,
                        metrics
                    )
                    VALUES (
                        %(job_id)s,
                        %(dataset_id)s,
                        %(model_name)s,
                        %(metrics)s
                    )
                    """,
                    {
                        "job_id": job.job_id,
                        "dataset_id": job.dataset_id,
                        "model_name": result.model_name,
                        "metrics": Jsonb(result.metrics),
                    },
                )

            connection.execute(
                """
                UPDATE evaluation_jobs
                SET status = 'completed',
                    stage = 'completed',
                    progress_completed = progress_total,
                    lease_token = NULL,
                    lease_expires_at = NULL,
                    completed_at = now()
                WHERE id = %(job_id)s
                """,
                {"job_id": job.job_id},
            )
            connection.execute(
                """
                UPDATE datasets
                SET status = 'ready'
                WHERE id = %(dataset_id)s
                """,
                {"dataset_id": job.dataset_id},
            )

    def fail_job(
        self,
        job: JobLease,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        retry_delay_seconds: int,
    ) -> None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT attempt_count, max_attempts, dataset_id
                FROM evaluation_jobs
                WHERE id = %(job_id)s
                  AND lease_token = %(lease_token)s
                  AND status = 'running'
                FOR UPDATE
                """,
                {
                    "job_id": job.job_id,
                    "lease_token": job.lease_token,
                },
            ).fetchone()
            if row is None:
                return

            should_retry = retryable and row["attempt_count"] < row["max_attempts"]
            if should_retry:
                connection.execute(
                    """
                    UPDATE evaluation_jobs
                    SET status = 'queued',
                        stage = 'retry_scheduled',
                        run_after = now() + make_interval(secs => %(delay)s),
                        lease_token = NULL,
                        lease_expires_at = NULL,
                        error_code = %(error_code)s,
                        error_message = %(error_message)s
                    WHERE id = %(job_id)s
                    """,
                    {
                        "delay": retry_delay_seconds,
                        "error_code": error_code,
                        "error_message": error_message,
                        "job_id": job.job_id,
                    },
                )
                connection.execute(
                    """
                    UPDATE datasets
                    SET status = 'queued'
                    WHERE id = %(dataset_id)s
                    """,
                    {"dataset_id": row["dataset_id"]},
                )
            else:
                connection.execute(
                    """
                    UPDATE evaluation_jobs
                    SET status = 'failed',
                        stage = 'failed',
                        lease_token = NULL,
                        lease_expires_at = NULL,
                        error_code = %(error_code)s,
                        error_message = %(error_message)s,
                        completed_at = now()
                    WHERE id = %(job_id)s
                    """,
                    {
                        "error_code": error_code,
                        "error_message": error_message,
                        "job_id": job.job_id,
                    },
                )
                connection.execute(
                    """
                    UPDATE datasets
                    SET status = 'failed'
                    WHERE id = %(dataset_id)s
                    """,
                    {"dataset_id": row["dataset_id"]},
                )

    def queue_expired_cleanup(self, batch_size: int) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT queue_expired_dataset_cleanup(%(batch_size)s) AS count",
                {"batch_size": batch_size},
            ).fetchone()
            return int(row["count"])

    def claim_cleanup(self, lease_seconds: int) -> CleanupLease | None:
        lease_token = uuid4()
        with self._connection() as connection:
            row = connection.execute(
                """
                WITH candidate AS (
                    SELECT id
                    FROM blob_cleanup_requests
                    WHERE attempt_count < max_attempts
                      AND (
                          (status = 'pending' AND run_after <= now())
                          OR (
                              status = 'running'
                              AND lease_expires_at <= now()
                          )
                      )
                    ORDER BY run_after, created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE blob_cleanup_requests cleanup
                SET status = 'running',
                    attempt_count = cleanup.attempt_count + 1,
                    lease_token = %(lease_token)s,
                    lease_expires_at = now() + make_interval(secs => %(lease_seconds)s)
                FROM candidate
                WHERE cleanup.id = candidate.id
                RETURNING cleanup.*
                """,
                {
                    "lease_token": lease_token,
                    "lease_seconds": lease_seconds,
                },
            ).fetchone()
            if row is None:
                return None
            return CleanupLease(
                cleanup_id=row["id"],
                dataset_id=row["dataset_id"],
                lease_token=row["lease_token"],
                blob_url=row["blob_url"],
                attempt_count=row["attempt_count"],
                max_attempts=row["max_attempts"],
            )

    def complete_cleanup(self, cleanup: CleanupLease) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE blob_cleanup_requests
                SET status = 'deleted',
                    lease_token = NULL,
                    lease_expires_at = NULL,
                    completed_at = now()
                WHERE id = %(cleanup_id)s
                  AND lease_token = %(lease_token)s
                  AND status = 'running'
                """,
                {
                    "cleanup_id": cleanup.cleanup_id,
                    "lease_token": cleanup.lease_token,
                },
            )
            if cursor.rowcount != 1:
                return

            if cleanup.dataset_id is not None:
                connection.execute(
                    """
                    DELETE FROM datasets data
                    WHERE data.id = %(dataset_id)s
                      AND data.deleted_at IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM blob_cleanup_requests cleanup
                          WHERE cleanup.dataset_id = data.id
                            AND cleanup.status <> 'deleted'
                      )
                    """,
                    {"dataset_id": cleanup.dataset_id},
                )

    def fail_cleanup(
        self,
        cleanup: CleanupLease,
        error_message: str,
        retry_delay_seconds: int,
    ) -> None:
        with self._connection() as connection:
            terminal = cleanup.attempt_count >= cleanup.max_attempts
            connection.execute(
                """
                UPDATE blob_cleanup_requests
                SET status = %(status)s,
                    run_after = now() + make_interval(secs => %(delay)s),
                    lease_token = NULL,
                    lease_expires_at = NULL,
                    last_error = %(error_message)s
                WHERE id = %(cleanup_id)s
                  AND lease_token = %(lease_token)s
                  AND status = 'running'
                """,
                {
                    "status": "failed" if terminal else "pending",
                    "delay": retry_delay_seconds,
                    "error_message": error_message,
                    "cleanup_id": cleanup.cleanup_id,
                    "lease_token": cleanup.lease_token,
                },
            )
