# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

"""Synchronous mock HTTP client for unit/retry tests."""

import json
from collections import deque
from typing import Deque, Iterator, List, Optional, Union

from deepl._http_types import HttpRequest, HttpResponse
from deepl.exceptions import ConnectionException


class MockStreamingResponse:
    """Minimal streaming response returned by MockHttpClient.send_streaming."""

    def __init__(
        self, status_code: int, headers: dict, content: bytes
    ) -> None:
        self.status_code = status_code
        self.headers = headers
        self._content = content

    def iter_content(self, chunk_size: int = 65536) -> Iterator[bytes]:
        yield self._content


# A response queue entry is either an HttpResponse or a ConnectionException.
QueueEntry = Union[HttpResponse, ConnectionException]


class MockHttpClient:
    """Configurable HTTP client for testing retry and error-mapping logic.

    Responses are consumed from ``responses`` in order.  Each call to
    ``send()`` pops the next entry; if it is a :class:`ConnectionException`
    it is raised, otherwise the :class:`HttpResponse` is returned.

    Attributes
    ----------
    calls:
        List of :class:`HttpRequest` objects received by ``send()``.
    """

    http_library_info: str = "mock/0.0"

    def __init__(self, responses: Optional[List[QueueEntry]] = None) -> None:
        self._responses: Deque[QueueEntry] = deque(responses or [])
        self.calls: List[HttpRequest] = []

    def push(self, *entries: QueueEntry) -> None:
        """Append one or more response entries to the queue."""
        self._responses.extend(entries)

    @staticmethod
    def ok_response(body: dict, status: int = 200) -> HttpResponse:
        """Helper: build a 200 JSON response."""
        content = json.dumps(body).encode("utf-8")
        return HttpResponse(
            status_code=status,
            headers={"Content-Type": "application/json"},
            content=content,
        )

    @staticmethod
    def status_response(status: int, message: str = "") -> HttpResponse:
        """Helper: build a non-2xx response with an optional message body."""
        body = {"message": message} if message else {}
        content = json.dumps(body).encode("utf-8")
        return HttpResponse(
            status_code=status,
            headers={"Content-Type": "application/json"},
            content=content,
        )

    @staticmethod
    def connection_error(
        message: str = "connection failed", *, should_retry: bool = True
    ) -> ConnectionException:
        """Helper: build a ConnectionException."""
        return ConnectionException(message, should_retry=should_retry)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.calls.append(request)
        if not self._responses:
            raise AssertionError(
                f"MockHttpClient.send() called but response queue is empty "
                f"(call #{len(self.calls)})"
            )
        entry = self._responses.popleft()
        if isinstance(entry, Exception):
            raise entry
        return entry

    def send_streaming(self, request: HttpRequest) -> MockStreamingResponse:
        self.calls.append(request)
        if not self._responses:
            raise AssertionError(
                f"MockHttpClient.send_streaming() called but queue is empty "
                f"(call #{len(self.calls)})"
            )
        entry = self._responses.popleft()
        if isinstance(entry, Exception):
            raise entry
        assert isinstance(entry, HttpResponse)
        return MockStreamingResponse(
            status_code=entry.status_code,
            headers=entry.headers,
            content=entry.content,
        )

    def close(self) -> None:
        pass
