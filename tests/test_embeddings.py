from __future__ import annotations

from types import SimpleNamespace
import unittest

import numpy as np

from evaluation_core.embeddings import embed_gemini_batches, encode_sentence_transformer


class FakeGeminiModels:
    def __init__(self):
        self.calls = []
        self.fail_once = True

    def embed_content(self, *, model, contents):
        self.calls.append((model, list(contents)))
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("RESOURCE_EXHAUSTED")
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[float(index), 1.0])
                for index, _ in enumerate(contents)
            ]
        )


class FakeSentenceTransformer:
    def encode(self, texts, **options):
        self.texts = texts
        self.options = options
        return np.array([[1.0, 0.0] for _ in texts])


class EmbeddingTests(unittest.TestCase):
    def test_gemini_batching_and_retry_callbacks(self):
        models = FakeGeminiModels()
        countdowns = []
        embeddings = embed_gemini_batches(
            SimpleNamespace(models=models),
            ["a", "b", "c"],
            batch_size=2,
            retry_delay_seconds=2,
            on_retry_countdown=lambda remaining, _error: countdowns.append(remaining),
            sleep=lambda _seconds: None,
        )
        self.assertEqual(countdowns, [2, 1])
        self.assertEqual([call[1] for call in models.calls], [["a", "b"], ["a", "b"], ["c"]])
        self.assertEqual(embeddings.shape, (3, 2))

    def test_sentence_transformer_options_match_legacy_behavior(self):
        model = FakeSentenceTransformer()
        embeddings = encode_sentence_transformer(model, ["one", "two"])
        self.assertEqual(model.texts, ["one", "two"])
        self.assertTrue(model.options["convert_to_numpy"])
        self.assertTrue(model.options["show_progress_bar"])
        self.assertTrue(model.options["normalize_embeddings"])
        self.assertEqual(embeddings.shape, (2, 2))


if __name__ == "__main__":
    unittest.main()
