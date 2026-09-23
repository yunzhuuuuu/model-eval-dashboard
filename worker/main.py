"""Production entrypoint for the asynchronous evaluation worker."""

from __future__ import annotations

import logging
import signal
import threading

from worker.config import WorkerConfig
from worker.processor import EvaluationProcessor, ProcessorLimits
from worker.providers import CachedEmbeddingProviders
from worker.repository import PostgresJobRepository
from worker.service import WorkerService
from worker.storage import VercelPrivateBlobStore


def build_service(config: WorkerConfig) -> WorkerService:
    repository = PostgresJobRepository(config.database_url)
    blob_store = VercelPrivateBlobStore(config.blob_token)
    providers = CachedEmbeddingProviders(config.gemini_api_key)
    processor = EvaluationProcessor(
        repository,
        blob_store,
        providers,
        lease_seconds=config.lease_seconds,
        limits=ProcessorLimits(
            max_upload_bytes=config.max_upload_bytes,
            max_contexts=config.max_contexts,
            max_questions=config.max_questions,
        ),
    )
    return WorkerService(
        repository,
        processor,
        blob_store,
        lease_seconds=config.lease_seconds,
        retry_delay_seconds=config.retry_delay_seconds,
        cleanup_batch_size=config.cleanup_batch_size,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = WorkerConfig.from_env()
    service = build_service(config)
    stop_event = threading.Event()

    def stop(_signal_number, _frame):
        logging.getLogger(__name__).info("Worker shutdown requested")
        stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    service.run_forever(stop_event, poll_seconds=config.poll_seconds)


if __name__ == "__main__":
    main()
