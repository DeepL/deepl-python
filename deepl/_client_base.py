# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import http
import http.client
import json as json_module
import platform
import traceback
from typing import Any, Dict, Optional, Union

from . import util, version
from .api_data import (
    GlossaryInfo,
    Language,
    MultilingualGlossaryInfo,
    StyleRuleInfo,
)
from .exceptions import (
    AuthorizationException,
    DeepLException,
    DocumentNotReadyException,
    GlossaryNotFoundException,
    QuotaExceededException,
    TooManyRequestsException,
)
from ._http_types import HttpResponse


def _check_valid_languages(
    source_lang: Optional[str], target_lang: str
) -> None:
    if target_lang == "EN":
        raise DeepLException(
            'target_lang="EN" is deprecated, '
            'please use "EN-GB" or "EN-US" instead.'
        )
    elif target_lang == "PT":
        raise DeepLException(
            'target_lang="PT" is deprecated, '
            'please use "PT-PT" or "PT-BR" instead.'
        )


def _check_language_and_formality(
    source_lang: Optional[Union[str, Any]],
    target_lang: Union[str, Any],
    formality: Optional[Union[str, Any]] = None,
    glossary: Optional[Union[str, Any]] = None,
    style_rule: Optional[Union[str, Any]] = None,
) -> Dict[str, Any]:
    target_lang = str(target_lang).upper()
    if source_lang is not None:
        source_lang = str(source_lang).upper()
    if glossary is not None and source_lang is None:
        raise ValueError("source_lang is required if using a glossary")
    if isinstance(glossary, GlossaryInfo):
        if (
            Language.remove_regional_variant(target_lang)
            != glossary.target_lang
            or source_lang != glossary.source_lang
        ):
            raise ValueError("source_lang and target_lang must match glossary")
    if isinstance(glossary, MultilingualGlossaryInfo):
        target_lang_code = Language.remove_regional_variant(target_lang)
        if not any(
            d.target_lang == target_lang_code and d.source_lang == source_lang
            for d in glossary.dictionaries
        ):
            raise ValueError(
                "must have a glossary with a dictionary for the given "
                "source_lang and target_lang"
            )
    if isinstance(style_rule, StyleRuleInfo):
        if (
            Language.remove_regional_variant(target_lang)
            != style_rule.language.upper()
        ):
            raise ValueError("target_lang must match style rule language")
    _check_valid_languages(source_lang, target_lang)
    request_data: Dict[str, Any] = {"target_lang": target_lang}
    if source_lang is not None:
        request_data["source_lang"] = source_lang
    if formality is not None:
        request_data["formality"] = str(formality).lower()
    if isinstance(glossary, (GlossaryInfo, MultilingualGlossaryInfo)):
        request_data["glossary_id"] = glossary.glossary_id
    elif glossary is not None:
        request_data["glossary_id"] = glossary
    if isinstance(style_rule, StyleRuleInfo):
        request_data["style_id"] = style_rule.style_id
    elif style_rule is not None:
        request_data["style_id"] = style_rule
    return request_data


def _generate_user_agent(
    send_platform_info: bool,
    app_info_name: Optional[str],
    app_info_version: Optional[str],
    http_library_info: str = "",
) -> str:
    """Build the User-Agent header value."""
    library_info_str = f"deepl-python/{version.VERSION}"
    if send_platform_info:
        try:
            library_info_str += (
                f" ({platform.platform()}) "
                f"python/{platform.python_version()}"
            )
            if http_library_info:
                library_info_str += f" {http_library_info}"
        except Exception:
            util.log_info(
                "Exception when querying platform information:\n"
                + traceback.format_exc()
            )
    if app_info_name and app_info_version:
        library_info_str += f" {app_info_name}/{app_info_version}"
    return library_info_str


class _ClientBase:
    """Shared non-I/O logic for DeepLClient and DeepLClientAsync.

    Handles auth, URL resolution, language/formality validation, and
    response error mapping. Contains no network I/O and no close().
    """

    _DEEPL_SERVER_URL = "https://api.deepl.com"
    _DEEPL_SERVER_URL_FREE = "https://api-free.deepl.com"
    _HTTP_STATUS_QUOTA_EXCEEDED = 456

    def __init__(
        self,
        auth_key: str,
        server_url: Optional[str] = None,
        send_platform_info: bool = True,
    ) -> None:
        if not auth_key:
            raise ValueError("auth_key must not be empty")

        self._auth_key = auth_key
        if server_url is None:
            server_url = (
                self._DEEPL_SERVER_URL_FREE
                if util.auth_key_is_free_account(auth_key)
                else self._DEEPL_SERVER_URL
            )
        if not server_url.endswith("/"):
            server_url += "/"
        self._server_url = server_url
        self._send_platform_info = send_platform_info
        self._app_info_name: Optional[str] = None
        self._app_info_version: Optional[str] = None
        self._http_library_info: str = ""
        self._custom_user_agent: Optional[str] = None

    @property
    def server_url(self) -> str:
        return self._server_url.rstrip("/")

    def set_app_info(
        self, app_info_name: str, app_info_version: str
    ) -> "_ClientBase":
        """Set app name and version to be included in the User-Agent header."""
        self._app_info_name = app_info_name
        self._app_info_version = app_info_version
        return self

    def set_user_agent(self, user_agent: str) -> "_ClientBase":
        """Override the entire User-Agent header with a custom string.

        The app info set via :meth:`set_app_info` is still appended if set.
        """
        self._custom_user_agent = user_agent
        return self

    def _make_auth_headers(self) -> Dict[str, str]:
        """Return headers that must be added to every request."""
        if self._custom_user_agent is not None:
            ua = self._custom_user_agent
            if self._app_info_name and self._app_info_version:
                ua = f"{ua} {self._app_info_name}/{self._app_info_version}"
        else:
            ua = _generate_user_agent(
                self._send_platform_info,
                self._app_info_name,
                self._app_info_version,
                self._http_library_info,
            )
        return {
            "Authorization": f"DeepL-Auth-Key {self._auth_key}",
            "User-Agent": ua,
        }

    def _raise_for_status(
        self,
        response: HttpResponse,
        glossary: bool = False,
        downloading_document: bool = False,
    ) -> None:
        """Raise an appropriate exception for non-2xx/3xx responses.

        Parses the JSON body for a human-readable message if available.
        Does nothing for 2xx/3xx responses.
        """
        status_code = response.status_code

        json_data: Any = None
        try:
            json_data = json_module.loads(response.content)
        except Exception:
            pass

        message = ""
        if isinstance(json_data, dict):
            if "message" in json_data:
                message += ", message: " + json_data["message"]
            if "detail" in json_data:
                message += ", detail: " + json_data["detail"]

        if 200 <= status_code < 400:
            return
        elif status_code == http.HTTPStatus.FORBIDDEN:
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
            raise DeepLException(
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
        elif status_code >= 500:
            status_name = http.client.responses.get(status_code, "Unknown")
            content_str = response.content.decode("utf-8", errors="replace")
            raise DeepLException(
                f"Unexpected status code: {status_code} {status_name}, "
                f"content: {content_str}.",
                should_retry=True,
                http_status_code=status_code,
            )
        else:
            status_name = http.client.responses.get(status_code, "Unknown")
            content_str = response.content.decode("utf-8", errors="replace")
            raise DeepLException(
                f"Unexpected status code: {status_code} {status_name}, "
                f"content: {content_str}.",
                should_retry=False,
                http_status_code=status_code,
            )
