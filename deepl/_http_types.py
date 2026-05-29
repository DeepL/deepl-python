# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import io
from dataclasses import dataclass, field
from typing import (
    AsyncIterator,
    BinaryIO,
    Callable,
    Dict,
    Iterator,
    Optional,
    Union,
)

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # type: ignore[assignment]

# SSL verification config, compatible with requests' verify= parameter.
# None/True = default verification, False = disable, str = CA bundle path.
SslConfig = Union[bool, str, None]


@dataclass
class MultipartBody:
    """Multipart form-data body for document upload.

    file_factory is called fresh on each retry attempt so the stream is
    always at position 0.
    """

    fields: Dict[str, str]
    file_factory: Callable[[], BinaryIO]
    file_name: str
    file_content_type: str


@dataclass
class HttpRequest:
    """Transport-agnostic HTTP request.

    body and multipart are mutually exclusive:
    - body: pre-serialised bytes (JSON, TSV, …)
    - multipart: document upload via MultipartBody

    timeout is set by DeepLClient at send time from RetryConfig (possibly
    overridden by http_client module globals) and is always present.
    """

    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None
    multipart: Optional[MultipartBody] = None
    timeout: Optional[float] = None

    def __post_init__(self) -> None:
        if self.body is not None and self.multipart is not None:
            raise ValueError("body and multipart are mutually exclusive")


@dataclass
class HttpResponse:
    """Fully-buffered HTTP response."""

    status_code: int
    headers: Dict[str, str]
    content: bytes


class StreamingHttpResponse(Protocol):
    """Protocol for streaming HTTP responses (document download only).

    NOT @runtime_checkable — this is a return type, not user-supplied.
    """

    status_code: int
    headers: Dict[str, str]

    def iter_content(self, chunk_size: int = 65536) -> Iterator[bytes]: ...


class AsyncStreamingHttpResponse(Protocol):
    """Protocol for async streaming HTTP responses.

    NOT @runtime_checkable — this is a return type, not user-supplied.
    Implementations should also be usable as async context managers
    (``__aenter__`` / ``__aexit__``) so callers can release the
    underlying connection deterministically without an explicit
    ``await close()``.
    """

    status_code: int
    headers: Dict[str, str]

    def aiter_content(
        self, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]: ...

    async def close(self) -> None: ...

    async def __aenter__(self) -> "AsyncStreamingHttpResponse": ...

    async def __aexit__(self, *args: object) -> None: ...


def make_file_factory(
    input_document: Union[BinaryIO, bytes, str],
) -> Callable[[], BinaryIO]:
    """Return a factory that produces a fresh BinaryIO on each call.

    Used for retryable document uploads: each retry gets a seek(0) stream.
    """
    if isinstance(input_document, bytes):
        data = input_document
        return lambda: io.BytesIO(data)
    if isinstance(input_document, str):
        data = input_document.encode("utf-8")
        return lambda: io.BytesIO(data)
    # File-like: read into memory once so retries work reliably.
    data = input_document.read()
    if isinstance(data, str):
        data = data.encode("utf-8")
    return lambda: io.BytesIO(data)
