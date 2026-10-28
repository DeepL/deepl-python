# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from . import http_client, util
from .exceptions import (
    AuthorizationException,
    DeepLException,
    DocumentNotReadyException,
    GlossaryNotFoundException,
    NotFoundException,
    QuotaExceededException,
    TooManyRequestsException,
)
import http
import http.client
import json as json_module
import requests  # type: ignore
from typing import Any, Dict, Optional, Tuple, Union
import urllib.parse


class BaseClient:
    """Shared HTTP handling for the DeepL API clients. Internal, not part of
    the public API."""

    _DEEPL_SERVER_URL = "https://api.deepl.com"

    # HTTP status code used by DeepL API to indicate the character limit for
    # this billing period has been reached.
    _HTTP_STATUS_QUOTA_EXCEEDED = 456

    def __init__(
        self,
        auth_key: str,
        *,
        server_url: str,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: bool = True,
        verify_ssl: Union[bool, str, None] = None,
        max_retries: Optional[int] = None,
        timeout_s: Optional[float] = None,
    ):
        self._server_url = server_url
        self._client = http_client.HttpClient(
            proxy,
            send_platform_info,
            verify_ssl,
            max_retries=max_retries,
            timeout_s=timeout_s,
        )
        self.headers = {"Authorization": f"DeepL-Auth-Key {auth_key}"}

    def __del__(self):
        self.close()

    def _api_call(
        self,
        url: str,
        *,
        method: str = "POST",
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        stream: bool = False,
        headers: Optional[dict] = None,
        retry_only_unprocessed: bool = False,
        **kwargs,
    ) -> Tuple[int, Union[str, requests.Response], Any]:
        """
        Makes a request to the API, and returns response as status code,
        content and JSON object.
        """
        if data is not None and json is not None:
            raise ValueError("cannot accept both json and data")

        if data is None:
            data = {}
        url = urllib.parse.urljoin(self._server_url, url)

        util.log_info("Request to DeepL API", method=method, url=url)
        util.log_debug("Request details", data=data, json=json)

        if headers is None:
            headers = dict()
        headers.update(
            {k: v for k, v in self.headers.items() if k not in headers}
        )

        status_code, content = self._client.request_with_backoff(
            method,
            url,
            data=data,
            json=json,
            stream=stream,
            headers=headers,
            retry_only_unprocessed=retry_only_unprocessed,
            **kwargs,
        )

        json = None
        if isinstance(content, str):
            content_str = content
            try:
                json = json_module.loads(content)
            except json_module.JSONDecodeError:
                pass
        else:
            content_str = content.text

        util.log_info("DeepL API response", url=url, status_code=status_code)
        util.log_debug("Response details", content=content_str)

        return status_code, content, json

    def _raise_for_status(
        self,
        status_code: int,
        content: Union[str, requests.Response],
        json: Any,
        glossary: bool = False,
        downloading_document: bool = False,
    ):
        message = ""
        if json is not None and isinstance(json, dict) and "message" in json:
            message += ", message: " + json["message"]
        if json is not None and isinstance(json, dict) and "detail" in json:
            message += ", detail: " + json["detail"]

        if 200 <= status_code < 400:
            return
        elif status_code in (
            http.HTTPStatus.UNAUTHORIZED,
            http.HTTPStatus.FORBIDDEN,
        ):
            raise AuthorizationException(
                f"Authorization failure, check auth_key{message}",
                http_status_code=status_code,
            )
        elif status_code == self._HTTP_STATUS_QUOTA_EXCEEDED:
            raise QuotaExceededException(
                f"Quota for this billing period has been exceeded{message}",
                http_status_code=status_code,
            )
        elif status_code == http.HTTPStatus.NOT_FOUND:
            if glossary:
                raise GlossaryNotFoundException(
                    f"Glossary not found{message}",
                    http_status_code=status_code,
                )
            raise NotFoundException(
                f"Not found{message}",
                http_status_code=status_code,
            )
        elif status_code == http.HTTPStatus.BAD_REQUEST:
            raise DeepLException(
                f"Bad request{message}", http_status_code=status_code
            )
        elif status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
            raise TooManyRequestsException(
                "Too many requests, DeepL servers are currently experiencing "
                f"high load{message}",
                should_retry=True,
                http_status_code=status_code,
            )
        elif status_code == http.HTTPStatus.SERVICE_UNAVAILABLE:
            if downloading_document:
                raise DocumentNotReadyException(
                    f"Document not ready{message}",
                    should_retry=True,
                    http_status_code=status_code,
                )
            else:
                raise DeepLException(
                    f"Service unavailable{message}",
                    should_retry=True,
                    http_status_code=status_code,
                )
        else:
            status_name = (
                http.client.responses[status_code]
                if status_code in http.client.responses
                else "Unknown"
            )
            content_str = content if isinstance(content, str) else content.text
            raise DeepLException(
                f"Unexpected status code: {status_code} {status_name}, "
                f"content: {content_str}.",
                should_retry=False,
                http_status_code=status_code,
            )

    def close(self):
        if hasattr(self, "_client"):
            self._client.close()

    def set_app_info(self, app_info_name: str, app_info_version: str):
        self._client.set_app_info(app_info_name, app_info_version)
        return self

    @property
    def server_url(self):
        return self._server_url
