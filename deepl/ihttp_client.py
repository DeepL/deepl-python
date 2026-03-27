# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from ._http_types import HttpRequest, HttpResponse, StreamingHttpResponse


@runtime_checkable
class HttpClientProtocol(Protocol):
    """Protocol for synchronous HTTP clients.

    Custom implementations must:
    - Make exactly one attempt per call (no internal retry).
    - Translate all library-specific network errors to
      :class:`~deepl.exceptions.ConnectionException` before raising.

    :meth:`send` is used for all endpoints except document download.
    :meth:`send_streaming` is used for document download only.
    """

    @property
    def http_library_info(self) -> str:
        """Version string of the underlying HTTP library, e.g.
        ``"requests/2.32.5"``. Included in the ``User-Agent`` header."""
        ...

    def send(self, request: HttpRequest) -> HttpResponse: ...

    def send_streaming(
        self, request: HttpRequest
    ) -> StreamingHttpResponse: ...

    def close(self) -> None: ...
