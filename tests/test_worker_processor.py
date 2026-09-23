from __future__ import annotations

import unittest
from uuid import uuid4

import numpy as np

from worker.domain import JobLease
from worker.processor import EvaluationProcessor, ProcessorLimits


class FakeRepository:
    def __init__(self):
        self.progress = []
        self.counts = None

    def set_progress(self, job, stage, completed, total, lease_seconds):
        self.progress.append((stage, completed, total, lease_seconds))

    def set_dataset_counts(self, job, context_count, question_count):
        self.counts = (context_count, question_count)


class FakeBlobStore:
    def __init__(self, files):
        self.files = files

    def read_bytes(self, url, max_bytes):
        value = self.files[url]
        if len(value) > max_bytes:
            raise AssertionError("test fixture exceeded configured size")
        return value


class FakeProviders:
    @staticmethod
    def _embed(texts):
        return np.asarray(
            [
                [1.0, 0.0] if "alpha" in text.lower() else [0.0, 1.0]
                for text in texts
            ]
        )

    def embed_gemini(self, texts):
        return self._embed(texts)

    def embed_sentence_transformer(self, model_id, texts):
        return self._embed(texts)


class EvaluationProcessorTests(unittest.TestCase):
    def test_processes_all_three_models_and_reports_progress(self):
        repository = FakeRepository()
        storage = FakeBlobStore(
            {
                "context": b"Note\nAlpha note\nBeta note\n",
                "qanda": (
                    b"Question,Relevant Note\n"
                    b"Find alpha,Alpha note\n"
                    b"Find beta,Beta note\n"
                ),
            }
        )
        processor = EvaluationProcessor(
            repository,
            storage,
            FakeProviders(),
            lease_seconds=300,
            limits=ProcessorLimits(max_upload_bytes=1024),
        )
        job = JobLease(
            job_id=uuid4(),
            dataset_id=uuid4(),
            lease_token=uuid4(),
            dataset_name="demo",
            context_blob_url="context",
            qanda_blob_url="qanda",
            attempt_count=1,
            max_attempts=3,
        )

        results = processor.process(job)

        self.assertEqual(repository.counts, (2, 2))
        self.assertEqual(
            [result.model_name for result in results],
            [
                "gemini_3072",
                "all-mpnet-base-v2",
                "multi-qa-MiniLM-L6-dot-v1",
            ],
        )
        for result in results:
            self.assertEqual(
                result.metrics,
                {
                    "Recall@1": 1.0,
                    "Recall@3": 1.0,
                    "Mean Rank": 1.0,
                    "MRR": 1.0,
                },
            )
        self.assertEqual(repository.progress[0][0], "downloading_uploads")
        self.assertEqual(repository.progress[-1][1:3], (8, 8))


if __name__ == "__main__":
    unittest.main()
