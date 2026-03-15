# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import threading
from typing import Dict, Union

import requests  # type: ignore[import-untyped]
import requests.exceptions  # type: ignore[import-untyped]

from .exceptions import ConnectionException
from ._http_types import (
    HttpRequest,
    HttpResponse,
    SslConfig,
    StreamingHttpResponse,
)


class RequestsClient:
    """Synchronous HTTP client backed by :mod:`requests`.

    Uses a thread-local :class:`requests.Session` so that a single
    ``DeepLClient`` instance can be shared across threads safely.

    Makes exactly one attempt per call — retry logic lives in
    ``DeepLClient._send_with_backoff()``.

    All library-specific network errors are translated to
    :class:`~deepl.exceptions.ConnectionException` before raising, so the
    retry loop only needs to handle that one exception type.

    :param proxy: Proxy URL string or dict with ``"http"``/``"https"`` keys.
    :param verify_ssl: SSL verification config (see :data:`~deepl.SslConfig`).
    """

    def __init__(
        self,
        proxy: Union[Dict, str, None] = None,
        verify_ssl: SslConfig = None,
    ) -> None:
        self._proxy = proxy
        self._verify_ssl = verify_ssl
        self._local = threading.local()

    def _get_session(self) -> requests.Session:
        """Return the thread-local session, creating it if needed."""
        if not hasattr(self._local, "session"):
            session = requests.Session()
            if self._proxy:
                proxy = self._proxy
                if isinstance(proxy, str):
                    proxy = {"http": proxy, "https": proxy}
                if not isinstance(proxy, dict):
                    raise ValueError(
                        "proxy may be specified as a URL string or dictionary "
                        "containing URL strings for the http and https keys."
                    )
                session.proxies.update(proxy)
            if self._verify_ssl is not None:
                session.verify = self._verify_ssl
            self._local.session = session
        return self._local.session

    def send(self, request: HttpRequest) -> HttpResponse:
        """Make one synchronous HTTP request; return a buffered response.

        :raises ConnectionException: On any network error.
        """
        session = self._get_session()
        timeout = request.timeout
        try:
            if request.multipart is not None:
                mp = request.multipart
                file_obj = mp.file_factory()
                files = {
                    "file": (mp.file_name, file_obj, mp.file_content_type)
                }
                resp = session.request(
                    request.method,
                    request.url,
                    data=mp.fields,
                    files=files,
                    headers=request.headers,
                    timeout=timeout,
                )
            elif request.body is not None:
                resp = session.request(
                    request.method,
                    request.url,
                    data=request.body,
                    headers=request.headers,
                    timeout=timeout,
                )
            else:
                resp = session.request(
                    request.method,
                    request.url,
                    headers=request.headers,
                    timeout=timeout,
                )
            content = resp.content
            resp.close()
            return HttpResponse(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                content=content,
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionException(
                f"Connection failed: {e}", should_retry=True
            ) from e
        except requests.exceptions.Timeout as e:
            raise ConnectionException(
                f"Request timed out: {e}", should_retry=True
            ) from e
        except requests.exceptions.RequestException as e:
            raise ConnectionException(
                f"Request failed: {e}", should_retry=False
            ) from e
        except Exception as e:
            raise ConnectionException(
                f"Unexpected request failure: {e}", should_retry=False
            ) from e

    def send_streaming(self, request: HttpRequest) -> StreamingHttpResponse:
        """Make one synchronous HTTP request; return a streaming response.

        The caller is responsible for iterating (and thereby consuming) the
        response body via ``iter_content()``.

        :raises ConnectionException: On any network error before the response
            headers are received.
        """
        session = self._get_session()
        timeout = request.timeout
        try:
            if request.body is not None:
                resp = session.request(
                    request.method,
                    request.url,
                    data=request.body,
                    headers=request.headers,
                    timeout=timeout,
                    stream=True,
                )
            else:
                resp = session.request(
                    request.method,
                    request.url,
                    headers=request.headers,
                    timeout=timeout,
                    stream=True,
                )
            # requests.Response satisfies StreamingHttpResponse Protocol:
            # it has status_code, headers, and iter_content().
            return resp  # type: ignore[return-value]
        except requests.exceptions.ConnectionError as e:
            raise ConnectionException(
                f"Connection failed: {e}", should_retry=True
            ) from e
        except requests.exceptions.Timeout as e:
            raise ConnectionException(
                f"Request timed out: {e}", should_retry=True
            ) from e
        except requests.exceptions.RequestException as e:
            raise ConnectionException(
                f"Request failed: {e}", should_retry=False
            ) from e
        except Exception as e:
            raise ConnectionException(
                f"Unexpected request failure: {e}", should_retry=False
            ) from e

    @property
    def http_library_info(self) -> str:
        return f"requests/{requests.__version__}"

    def close(self) -> None:
        """Close the calling thread's session if one exists.

        Note: only cleans up the session belonging to the thread that calls
        this method. Sessions created on other threads are not closed. This
        is an inherent limitation of thread-local storage; in practice it
        means the ``DeepLClient.__del__`` / ``__exit__`` cleanup may leave
        open connections on worker threads. Call ``close()`` from each
        thread that used the client if complete cleanup is required.
        """
        if hasattr(self._local, "session"):
            self._local.session.close()
            del self._local.session
