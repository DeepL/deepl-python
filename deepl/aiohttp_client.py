# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import asyncio
from typing import AsyncIterator, Dict, List, Optional, Union

from .exceptions import ConnectionException
from ._http_types import HttpRequest, HttpResponse

try:
    import aiohttp
    import aiohttp.client_exceptions
except ImportError as _import_error:
    aiohttp = None  # type: ignore[assignment]
    _aiohttp_import_error: Optional[ImportError] = _import_error
else:
    _aiohttp_import_error = None


class _AioHttpStreamingResponse:
    """Wraps an aiohttp.ClientResponse as an AsyncStreamingHttpResponse."""

    def __init__(self, response: "aiohttp.ClientResponse") -> None:
        self._response = response
        self.status_code: int = response.status
        self.headers: Dict[str, str] = dict(response.headers)

    def aiter_content(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        return self._response.content.iter_chunked(chunk_size)

    async def close(self) -> None:
        await self._response.release()


class AioHttpClient:
    """Async HTTP client backed by :mod:`aiohttp`.

    Creates a single :class:`aiohttp.ClientSession` lazily on first use so
    the session is always bound to the running event loop.

    Makes exactly one attempt per call — retry logic lives in
    ``DeepLClientAsync._send_with_backoff()``.

    All library-specific network errors are translated to
    :class:`~deepl.exceptions.ConnectionException` before raising.

    :param proxy: Proxy URL string. Dict form not supported by aiohttp.
    :param verify_ssl: SSL verification config (see :data:`~deepl.SslConfig`).
    """

    def __init__(
        self,
        proxy: Union[Dict, str, None] = None,
        verify_ssl: Union[bool, str, None] = None,
    ) -> None:
        if aiohttp is None:
            raise ImportError(
                "aiohttp is required for async support. "
                "Install it with: pip install deepl[async]"
            ) from _aiohttp_import_error

        if isinstance(proxy, dict):
            proxy = proxy.get("https") or proxy.get("http")
        self._proxy: Optional[str] = proxy
        self._verify_ssl = verify_ssl
        self._session: Optional["aiohttp.ClientSession"] = None
        self._session_loop: Optional[asyncio.AbstractEventLoop] = None
        # Stale sessions waiting to be closed. Populated when the event
        # loop changes between calls (e.g. tests using asyncio.run); drained
        # best-effort by close().
        self._pending_close_sessions: List["aiohttp.ClientSession"] = []

    def _build_connector_kwargs(self) -> Dict:
        kwargs: Dict = {}
        if self._verify_ssl is False:
            kwargs["ssl"] = False
        elif isinstance(self._verify_ssl, str):
            import ssl

            kwargs["ssl"] = ssl.create_default_context(cafile=self._verify_ssl)
        return kwargs

    def _get_session(self) -> "aiohttp.ClientSession":
        """Return or create the session, re-creating if the event loop changed.

        aiohttp ≥3.9 binds a ClientSession to the loop that was running when
        it was constructed. Re-using a session across asyncio.run() calls (e.g.
        in test suites) raises RuntimeError. We detect this by comparing the
        session's internal loop against the currently running loop and
        transparently replace it.
        """
        loop = asyncio.get_running_loop()
        stale = (
            self._session is None
            or self._session.closed
            or self._session_loop is not loop
        )
        if stale:
            if self._session is not None and not self._session.closed:
                self._pending_close_sessions.append(self._session)
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    **self._build_connector_kwargs()
                )
            )
            self._session_loop = loop
        assert self._session is not None
        return self._session

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Make one async HTTP request; return a buffered response.

        :raises ConnectionException: On any network error.
        """
        session = self._get_session()
        timeout = aiohttp.ClientTimeout(total=request.timeout)
        try:
            if request.multipart is not None:
                mp = request.multipart
                form = aiohttp.FormData()
                for key, value in mp.fields.items():
                    form.add_field(key, value)
                form.add_field(
                    "file",
                    mp.file_factory(),
                    filename=mp.file_name,
                    content_type=mp.file_content_type,
                )
                resp = await session.request(
                    request.method,
                    request.url,
                    data=form,
                    headers=request.headers,
                    timeout=timeout,
                    proxy=self._proxy,
                )
            elif request.body is not None:
                resp = await session.request(
                    request.method,
                    request.url,
                    data=request.body,
                    headers=request.headers,
                    timeout=timeout,
                    proxy=self._proxy,
                )
            else:
                resp = await session.request(
                    request.method,
                    request.url,
                    headers=request.headers,
                    timeout=timeout,
                    proxy=self._proxy,
                )
            content = await resp.read()
            await resp.release()
            return HttpResponse(
                status_code=resp.status,
                headers=dict(resp.headers),
                content=content,
            )
        except asyncio.TimeoutError as e:
            raise ConnectionException(
                f"Request timed out: {e}", should_retry=True
            ) from e
        except aiohttp.client_exceptions.ClientConnectionError as e:
            raise ConnectionException(
                f"Connection failed: {e}", should_retry=True
            ) from e
        except aiohttp.ClientError as e:
            raise ConnectionException(
                f"Request failed: {e}", should_retry=False
            ) from e
        except Exception as e:
            raise ConnectionException(
                f"Unexpected request failure: {e}", should_retry=False
            ) from e

    async def send_streaming(
        self, request: HttpRequest
    ) -> _AioHttpStreamingResponse:
        """Make one async HTTP request; return a streaming response.

        The caller is responsible for consuming the response body via
        ``aiter_content()``.

        :raises ConnectionException: On any network error before response
            headers are received.
        """
        session = self._get_session()
        timeout = aiohttp.ClientTimeout(total=request.timeout)
        try:
            if request.body is not None:
                resp = await session.request(
                    request.method,
                    request.url,
                    data=request.body,
                    headers=request.headers,
                    timeout=timeout,
                    proxy=self._proxy,
                )
            else:
                resp = await session.request(
                    request.method,
                    request.url,
                    headers=request.headers,
                    timeout=timeout,
                    proxy=self._proxy,
                )
            return _AioHttpStreamingResponse(resp)
        except asyncio.TimeoutError as e:
            raise ConnectionException(
                f"Request timed out: {e}", should_retry=True
            ) from e
        except aiohttp.client_exceptions.ClientConnectionError as e:
            raise ConnectionException(
                f"Connection failed: {e}", should_retry=True
            ) from e
        except aiohttp.ClientError as e:
            raise ConnectionException(
                f"Request failed: {e}", should_retry=False
            ) from e
        except Exception as e:
            raise ConnectionException(
                f"Unexpected request failure: {e}", should_retry=False
            ) from e

    async def close(self) -> None:
        """Close the aiohttp session and any sessions abandoned on loop
        changes.

        Sessions are bound to the loop they were created on; closing one
        from a different loop will fail. We swallow such errors so close()
        is safe to call from any loop.
        """
        for old in self._pending_close_sessions:
            if old.closed:
                continue
            try:
                await old.close()
            except Exception:
                pass
        self._pending_close_sessions.clear()
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None
