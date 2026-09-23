from __future__ import annotations

import unittest
from unittest.mock import patch

from worker.storage import (
    BlobSizeLimitError,
    BlobStorageError,
    VercelPrivateBlobStore,
)


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def read(self, size):
        return self.value[:size]


class BlobStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = VercelPrivateBlobStore("secret-token")
        self.private_url = (
            "https://store.private.blob.vercel-storage.com/uploads/context.csv"
        )

    def test_rejects_public_or_untrusted_urls(self):
        with self.assertRaises(BlobStorageError):
            self.storage.read_bytes(
                "https://store.public.blob.vercel-storage.com/file.csv",
                100,
            )
        with self.assertRaises(BlobStorageError):
            self.storage.read_bytes("https://example.com/file.csv", 100)

    @patch("urllib.request.urlopen")
    def test_reads_private_blob_with_bearer_token(self, urlopen):
        urlopen.return_value = FakeResponse(b"hello")
        value = self.storage.read_bytes(self.private_url, 100)
        self.assertEqual(value, b"hello")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer secret-token")

    @patch("urllib.request.urlopen")
    def test_rejects_oversized_blob(self, urlopen):
        urlopen.return_value = FakeResponse(b"123456")
        with self.assertRaises(BlobSizeLimitError):
            self.storage.read_bytes(self.private_url, 5)


if __name__ == "__main__":
    unittest.main()
