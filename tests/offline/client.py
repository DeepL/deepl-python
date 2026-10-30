# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import io
import warnings
from typing import List, Optional

import deepl

SERVER_URL = "https://api.deepl.com"
AUTH_KEY = "k"
AUTH_HEADER = f"DeepL-Auth-Key {AUTH_KEY}"


def url(path: str) -> str:
    return f"{SERVER_URL}/{path}"


def make_translator(**kwargs) -> deepl.Translator:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", "Translator is deprecated", DeprecationWarning
        )
        return deepl.Translator(AUTH_KEY, **kwargs)


def make_deepl_client(**kwargs) -> deepl.DeepLClient:
    return deepl.DeepLClient(AUTH_KEY, **kwargs)


def make_admin_client(**kwargs) -> deepl.DeepLAdminClient:
    return deepl.DeepLAdminClient(AUTH_KEY, **kwargs)


class StreamedBody(io.BufferedReader):
    """Response body for responses that records the size of every read and
    resets the connection once fail_after bytes have been read."""

    def __init__(self, data: bytes = b"", fail_after: Optional[int] = None):
        super().__init__(io.BytesIO(data))  # type: ignore[arg-type]
        self.read_sizes: List[Optional[int]] = []
        self._fail_after = fail_after
        self._bytes_read = 0

    def read(self, size=None):
        self.read_sizes.append(size)
        if (
            self._fail_after is not None
            and self._bytes_read >= self._fail_after
        ):
            raise ConnectionResetError(104, "Connection reset by peer")
        data = super().read(size)
        self._bytes_read += len(data)
        return data

    def read1(self, size=-1):
        return self.read(size)
