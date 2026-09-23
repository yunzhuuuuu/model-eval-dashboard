"""Private Vercel Blob access for the external Python worker."""

from __future__ import annotations

import urllib.parse
import urllib.request


class BlobStorageError(RuntimeError):
    """Raised when a private upload cannot be read or deleted safely."""

class BlobSizeLimitError(BlobStorageError):
    """Raised when an upload exceeds the configured worker limit."""


class VercelPrivateBlobStore:
    def __init__(self, token: str, timeout_seconds: int = 30):
        if not token:
            raise ValueError("A Vercel Blob read-write token is required.")
        self._token = token
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".private.blob.vercel-storage.com")
        ):
            raise BlobStorageError("Refusing to access a non-private Vercel Blob URL.")

    def read_bytes(self, url: str, max_bytes: int) -> bytes:
        self._validate_url(url)
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive.")

        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                data = response.read(max_bytes + 1)
        except Exception as exc:
            raise BlobStorageError(f"Unable to read private upload: {exc}") from exc

        if len(data) > max_bytes:
            raise BlobSizeLimitError(
                f"Uploaded file exceeds the {max_bytes}-byte worker limit."
            )
        return data

    def delete(self, url: str) -> None:
        self._validate_url(url)
        try:
            from vercel.blob import delete

            delete(url, token=self._token)
        except Exception as exc:
            raise BlobStorageError(f"Unable to delete private upload: {exc}") from exc
