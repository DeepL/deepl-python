# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from . import version
from .exceptions import ConnectionException, DeepLException
import http
import platform
import random
import re
import requests  # type: ignore
import socket
import traceback
import time
import urllib.parse
from functools import lru_cache
from typing import Dict, Iterator, List, Optional, Tuple, Union
from .util import log_info
from deepl import util


class _BackoffTimer:
    """Implements exponential-backoff strategy.
    This strategy is based on the GRPC Connection Backoff Protocol:
    https://github.com/grpc/grpc/blob/master/doc/connection-backoff.md"""

    BACKOFF_INITIAL = 1.0
    BACKOFF_MAX = 120.0
    BACKOFF_JITTER = 0.23
    BACKOFF_MULTIPLIER = 1.6

    def __init__(self, min_timeout: float):
        self._min_timeout = min_timeout
        self._num_retries = 0
        self._backoff = self.BACKOFF_INITIAL
        self._deadline = time.time() + self._backoff

    def get_num_retries(self):
        return self._num_retries

    def get_timeout(self):
        return max(self.get_time_until_deadline(), self._min_timeout)

    def get_time_until_deadline(self):
        return max(self._deadline - time.time(), 0.0)

    def sleep_until_deadline(self):
        time.sleep(self.get_time_until_deadline())

        # Apply multiplier to current backoff time
        self._backoff = min(
            self._backoff * self.BACKOFF_MULTIPLIER, self.BACKOFF_MAX
        )

        # Get deadline by applying jitter as a proportion of backoff:
        # if jitter is 0.1, then multiply backoff by random value in [0.9, 1.1]
        self._deadline = time.time() + self._backoff * (
            1 + self.BACKOFF_JITTER * random.uniform(-1, 1)
        )
        self._num_retries += 1


_PROXY_SCHEMES = ("http", "https", "socks4", "socks4a", "socks5", "socks5h")
_SCHEME_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:/")


def _check_proxy_url(key, value) -> None:
    """Raises ValueError unless value is a proxy URL requests can use. A
    value without a scheme is checked as an http:// URL, as requests uses it.
    The message names only the proxy key: the URL may contain credentials."""
    valid = False
    if isinstance(value, str):
        if not _SCHEME_PREFIX.match(value):
            value = "http://" + value
        try:
            parts = urllib.parse.urlsplit(value)
            parts.port  # raises ValueError for an invalid port
            valid = (
                parts.scheme.lower() in _PROXY_SCHEMES
                and bool(parts.hostname)
                and not any(c.isspace() for c in parts.hostname)
            )
        except ValueError:
            valid = False
    if not valid:
        raise ValueError(
            "proxy must be a URL with scheme http, https, socks4, socks4a, "
            f"socks5 or socks5h and a host: invalid value for {key!r}"
        )


class HttpClient:
    def __init__(
        self,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: Optional[bool] = True,
        verify_ssl: Union[bool, str, None] = None,
        max_retries: Optional[int] = 5,
        timeout_s: Optional[float] = 10.0,
    ):
        self._max_retries = 5 if max_retries is None else max_retries
        self._timeout_s = 10.0 if timeout_s is None else timeout_s
        self._session = requests.Session()
        if proxy:
            if isinstance(proxy, str):
                proxy = {"http": proxy, "https": proxy}
            for key, value in proxy.items():
                if value is not None:
                    _check_proxy_url(key, value)
            self._session.proxies.update(proxy)
        if verify_ssl is not None:
            self._session.verify = verify_ssl
        self._send_platform_info = (
            True if send_platform_info is None else send_platform_info
        )
        self._app_info_name: Optional[str] = None
        self._app_info_version: Optional[str] = None

    def set_app_info(self, app_info_name: str, app_info_version: str):
        self._app_info_name = app_info_name
        self._app_info_version = app_info_version
        return self

    def close(self):
        self._session.close()

    def request_with_backoff(
        self,
        method: str,
        url: str,
        data: Optional[dict],
        json: Optional[dict],
        headers: dict,
        stream: bool = False,
        retry_only_unprocessed: bool = False,
        **kwargs,
    ) -> Tuple[int, Union[str, requests.Response]]:
        """Makes API request, retrying if necessary, and returns response.

        If retry_only_unprocessed is True, the request is only retried after
        failures that show it was not processed (HTTP 429 and network failures
        while connecting, before any request byte is written: DNS resolution
        errors, refused connections, connect timeouts, resets and timeouts in
        the TLS or proxy handshake), for requests that are unsafe to repeat; a
        raised ConnectionException then has should_retry True only after those
        failures or a response body cut off mid-read. Otherwise connection
        failures, including a connection that breaks off while the response
        body is read, and timeouts are retried too.

        Return and exceptions are the same as function request()."""
        backoff = _BackoffTimer(self._timeout_s)
        request = self._prepare_request(
            method, url, data, json, headers, **kwargs
        )

        while True:
            response: Optional[Tuple[int, Union[str, requests.Response]]]
            try:
                response = self._internal_request(
                    request, stream=stream, timeout=backoff.get_timeout()
                )
                exception = None
            except Exception as e:
                response = None
                exception = e

            if not self._should_retry(
                response,
                exception,
                backoff.get_num_retries(),
                retry_only_unprocessed,
            ):
                if response is not None:
                    return response
                if retry_only_unprocessed and isinstance(
                    exception, ConnectionException
                ):
                    # Repeating a request that may have been processed could
                    # create a duplicate.
                    exception.should_retry = exception.should_retry and (
                        _was_not_sent(exception)
                        or _body_was_cut_off(exception)
                    )
                raise exception  # type: ignore[misc]

            if exception is not None:
                log_info(
                    f"Encountered a retryable-exception: {str(exception)}"
                )

            log_info(
                f"Starting retry {backoff.get_num_retries() + 1} for request "
                f"{method} {url} after sleeping for "
                f"{backoff.get_time_until_deadline():.2f} seconds."
            )
            backoff.sleep_until_deadline()

    def request(
        self,
        method: str,
        url: str,
        data: Optional[dict],
        json: Optional[dict],
        headers: dict,
        stream: bool = False,
        **kwargs,
    ) -> Tuple[int, Union[str, requests.Response]]:
        """Makes API request and returns response content.

        Response is returned as HTTP status code and either content string (if
        stream is False) or response (if stream is True).

        If no response is received will raise ConnectionException."""

        request = self._prepare_request(
            method, url, data, json, headers, **kwargs
        )
        return self._internal_request(request, stream)

    def _internal_request(
        self,
        request: requests.PreparedRequest,
        stream: bool,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Tuple[int, Union[str, requests.Response]]:
        if timeout is None:
            timeout = self._timeout_s
        try:
            response = self._session.send(
                request, stream=stream, timeout=timeout, **kwargs
            )
            if stream:
                return response.status_code, response
            else:
                try:
                    response.encoding = "UTF-8"
                    return response.status_code, response.text
                finally:
                    response.close()

        except requests.exceptions.SSLError as e:
            message = f"TLS connection failed: {e}"
            raise ConnectionException(message, should_retry=False) from e
        except requests.exceptions.ProxyError as e:
            message = f"Proxy connection failed: {e}"
            raise ConnectionException(
                message, should_retry=not _proxy_refused(e)
            ) from e
        except requests.exceptions.ConnectionError as e:
            message = f"Connection failed: {e}"
            raise ConnectionException(message, should_retry=True) from e
        except requests.exceptions.Timeout as e:
            message = f"Request timed out: {e}"
            raise ConnectionException(message, should_retry=True) from e
        except requests.exceptions.ChunkedEncodingError as e:
            # The connection broke off while the body was read (reset or
            # truncated); the request reached the server.
            message = f"Connection broken while reading response: {e}"
            raise ConnectionException(message, should_retry=True) from e
        except requests.exceptions.RequestException as e:
            message = f"Request failed: {e}"
            raise ConnectionException(message, should_retry=False) from e
        except Exception as e:
            message = f"Unexpected request failure: {e}"
            raise ConnectionException(message, should_retry=False) from e

    def _should_retry(
        self, response, exception, num_retries, only_unprocessed=False
    ):
        if num_retries >= self._max_retries:
            return False

        if response is None:
            if only_unprocessed:
                return exception.should_retry and _was_not_sent(exception)
            return exception.should_retry

        status_code, _ = response
        # Retry on Too-Many-Requests error and internal errors
        return status_code == http.HTTPStatus.TOO_MANY_REQUESTS or (
            not only_unprocessed
            and status_code >= http.HTTPStatus.INTERNAL_SERVER_ERROR
        )

    def _prepare_request(
        self,
        method: str,
        url: str,
        data: Optional[dict],
        json: Optional[dict],
        headers: dict,
        **kwargs,
    ) -> requests.PreparedRequest:
        try:
            if not any(k.lower() == "user-agent" for k in headers):
                headers["User-Agent"] = _generate_user_agent(
                    self._send_platform_info,
                    self._app_info_name,
                    self._app_info_version,
                )
            return requests.Request(
                method, url, data=data, headers=headers, json=json, **kwargs
            ).prepare()
        except Exception as e:
            raise DeepLException(
                f"Error occurred while preparing request: {e}"
            ) from e


def read_response_text(response: requests.Response) -> str:
    """Reads the body of a streamed response as text, raising
    ConnectionException if the connection fails while it is read."""
    try:
        return response.text
    except requests.exceptions.RequestException as e:
        raise _body_read_exception(e) from e


def iter_response_content(
    response: requests.Response, chunk_size: int
) -> Iterator[bytes]:
    """Yields the body of a streamed response in chunks, raising
    ConnectionException if the connection fails while it is read."""
    try:
        yield from response.iter_content(chunk_size=chunk_size)
    except requests.exceptions.RequestException as e:
        raise _body_read_exception(e) from e


def _body_read_exception(
    e: requests.exceptions.RequestException,
) -> ConnectionException:
    # Not retried automatically: part of the body may already be consumed.
    return ConnectionException(
        f"Connection failed while reading response: {e}",
        should_retry=True,
    )


# urllib3 1.x has no NameResolutionError; its connection errors keep the
# socket.gaierror as context instead.
_NAME_RESOLUTION_ERRORS = tuple(
    e
    for e in (
        socket.gaierror,
        getattr(
            requests.packages.urllib3.exceptions,  # type: ignore[attr-defined]
            "NameResolutionError",
            None,
        ),
    )
    if e is not None
)


_CONNECT_TIMEOUT_ERRORS = (
    requests.exceptions.ConnectTimeout,
    requests.packages.urllib3.exceptions.ConnectTimeoutError,  # type: ignore
)


def _was_not_sent(exception: BaseException) -> bool:
    """Returns True if the exception shows that the request was never sent:
    it was raised while connecting to the server or proxy, setting up the
    proxy tunnel or in the TLS handshake, before any request byte was
    written."""
    return _caused_by(
        exception,
        _NAME_RESOLUTION_ERRORS
        + (ConnectionRefusedError,)
        + _CONNECT_TIMEOUT_ERRORS,
    ) or any(
        frame.f_code.co_name == "connect"
        and frame.f_globals.get("__name__") == "urllib3.connection"
        for e in _exception_chain(exception)
        for frame, _ in traceback.walk_tb(e.__traceback__)
    )


def _proxy_refused(exception: BaseException) -> bool:
    """Returns True if the proxy answered CONNECT with a non-2xx status, or
    the TLS connection to the proxy failed."""
    return any(
        isinstance(e, requests.packages.urllib3.exceptions.SSLError)
        or (
            isinstance(e, OSError)
            and str(e).startswith("Tunnel connection failed:")
        )
        for e in _exception_chain(exception)
    )


def _body_was_cut_off(exception: BaseException) -> bool:
    """Returns True if the connection broke off while the response body was
    read, after the response status was received."""
    return _caused_by(exception, (requests.exceptions.ChunkedEncodingError,))


def _caused_by(exception: BaseException, types: tuple) -> bool:
    """Returns True if the exception or any exception in its cause chain is
    an instance of one of the given types."""
    return any(isinstance(e, types) for e in _exception_chain(exception))


def _exception_chain(exception: BaseException) -> Iterator[BaseException]:
    """Yields the exception and every exception in its cause chain."""
    pending: List[object] = [exception]
    seen = set()
    while pending:
        e = pending.pop()
        # ssl.SSLError.reason is a string, not an exception.
        if not isinstance(e, BaseException) or id(e) in seen:
            continue
        seen.add(id(e))
        yield e
        pending.extend(
            [e.__cause__, e.__context__, getattr(e, "reason", None)]
        )
        pending.extend(e.args)


@lru_cache(maxsize=4)
def _generate_user_agent(
    send_platform_info: bool,
    app_info_name: Optional[str],
    app_info_version: Optional[str],
):
    library_info_str = f"deepl-python/{version.VERSION}"
    if send_platform_info:
        try:
            library_info_str += (
                f" ({platform.platform()}) "
                f"python/{platform.python_version()}"
            )
        except Exception:
            util.log_info(
                "Exception when querying platform information:\n"
                + traceback.format_exc()
            )
    if app_info_name and app_info_version:
        library_info_str += f" {app_info_name}/{app_info_version}"
    return library_info_str
