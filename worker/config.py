"""Environment-backed worker configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkerConfig:
    database_url: str
    blob_token: str
    gemini_api_key: str
    lease_seconds: int = 900
    retry_delay_seconds: int = 60
    poll_seconds: float = 2.0
    cleanup_batch_size: int = 100
    max_upload_bytes: int = 10 * 1024 * 1024
    max_contexts: int = 10_000
    max_questions: int = 10_000

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        required = {
            "database_url": os.environ.get("DATABASE_URL", ""),
            "blob_token": os.environ.get("BLOB_READ_WRITE_TOKEN", ""),
            "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            environment_names = {
                "database_url": "DATABASE_URL",
                "blob_token": "BLOB_READ_WRITE_TOKEN",
                "gemini_api_key": "GEMINI_API_KEY",
            }
            labels = ", ".join(environment_names[name] for name in missing)
            raise RuntimeError(f"Missing required worker environment variables: {labels}")

        return cls(
            **required,
            lease_seconds=int(os.environ.get("WORKER_LEASE_SECONDS", "900")),
            retry_delay_seconds=int(
                os.environ.get("WORKER_RETRY_DELAY_SECONDS", "60")
            ),
            poll_seconds=float(os.environ.get("WORKER_POLL_SECONDS", "2")),
            cleanup_batch_size=int(
                os.environ.get("WORKER_CLEANUP_BATCH_SIZE", "100")
            ),
            max_upload_bytes=int(
                os.environ.get("WORKER_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))
            ),
            max_contexts=int(os.environ.get("WORKER_MAX_CONTEXTS", "10000")),
            max_questions=int(os.environ.get("WORKER_MAX_QUESTIONS", "10000")),
        )
