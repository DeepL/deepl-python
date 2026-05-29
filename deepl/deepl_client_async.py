# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import asyncio
import json as json_module
import os
import pathlib
import time
import warnings
from typing import (
    Any,
    Awaitable,
    BinaryIO,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    TextIO,
    Union,
)

from .api_data import (
    DocumentHandle,
    DocumentStatus,
    Formality,
    GlossaryInfo,
    GlossaryLanguagePair,
    Language,
    ModelType,
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryDictionaryEntriesResponse,
    MultilingualGlossaryDictionaryInfo,
    MultilingualGlossaryInfo,
    SplitSentences,
    StyleRuleInfo,
    TextResult,
    Usage,
    WriteResult,
)
from ._backoff_timer import BackoffTimer
from ._client_base import _ClientBase
from ._http_types import (
    HttpRequest,
    HttpResponse,
    SslConfig,
)
from ._methods import (
    _build_create_glossary_request,
    _build_create_multilingual_glossary_request,
    _build_delete_glossary_request,
    _build_delete_multilingual_glossary_dict_request,
    _build_delete_multilingual_glossary_request,
    _build_document_download_request,
    _build_document_status_request,
    _build_document_upload_request,
    _build_get_glossary_entries_request,
    _build_get_glossary_languages_request,
    _build_get_glossary_request,
    _build_get_multilingual_glossary_entries_request,
    _build_get_multilingual_glossary_request,
    _build_get_source_languages_request,
    _build_get_style_rules_request,
    _build_get_target_languages_request,
    _build_get_usage_request,
    _build_list_glossaries_request,
    _build_list_multilingual_glossaries_request,
    _build_rephrase_text_request,
    _build_replace_multilingual_glossary_dict_request,
    _build_translate_text_request,
    _build_update_multilingual_glossary_dict_request,
    _build_update_multilingual_glossary_name_request,
    _parse_create_glossary_response,
    _parse_document_status_response,
    _parse_document_upload_response,
    _parse_get_glossary_entries_response,
    _parse_get_glossary_languages_response,
    _parse_get_glossary_response,
    _parse_get_source_languages_response,
    _parse_get_style_rules_response,
    _parse_get_target_languages_response,
    _parse_get_usage_response,
    _parse_list_glossaries_response,
    _parse_list_multilingual_glossaries_response,
    _parse_multilingual_glossary_dict_response,
    _parse_multilingual_glossary_entries_response,
    _parse_multilingual_glossary_response,
    _parse_rephrase_text_response,
    _parse_translate_text_response,
)
from .exceptions import (
    ConnectionException,
    DeepLException,
    DocumentTranslationException,
)
from .retry_config import RetryConfig
from . import util

_DEFAULT_RETRY_CONFIG = RetryConfig()


class DeepLClientAsync(_ClientBase):
    """Async client for the DeepL API.

    Mirrors :class:`DeepLClient` but all network methods are coroutines.
    Requires :mod:`aiohttp`; install with ``pip install deepl[async]``.

    :param auth_key: Authentication key as found in your DeepL API account.
    :param server_url: (Optional) Base URL of DeepL API.
    :param proxy: (Optional) Proxy URL string or dict with ``"http"``/
        ``"https"`` keys. Forwarded to :class:`AioHttpClient`.
    :param send_platform_info: (Optional) Include OS/Python info in
        User-Agent.
    :param verify_ssl: (Optional) SSL certificate verification config.
    :param http_client: (Optional) Custom async HTTP client. When supplied,
        ``proxy`` and ``verify_ssl`` must not be set.
    :param retry_config: (Optional) Backoff/retry settings.
    :param skip_language_check: Deprecated, no-op.
    """

    def __init__(
        self,
        auth_key: str,
        *,
        server_url: Optional[str] = None,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: bool = True,
        verify_ssl: SslConfig = None,
        http_client: Optional[Any] = None,
        retry_config: RetryConfig = _DEFAULT_RETRY_CONFIG,
        skip_language_check: bool = False,
        _sleep_fn: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> None:
        super().__init__(auth_key, server_url, send_platform_info)

        from . import http_client as _hc

        if _hc.max_network_retries is not None or (
            _hc.min_connection_timeout is not None
        ):
            retry_config = RetryConfig(
                max_retries=(
                    _hc.max_network_retries
                    if _hc.max_network_retries is not None
                    else retry_config.max_retries
                ),
                min_connection_timeout=(
                    _hc.min_connection_timeout
                    if _hc.min_connection_timeout is not None
                    else retry_config.min_connection_timeout
                ),
                backoff_initial=retry_config.backoff_initial,
                backoff_max=retry_config.backoff_max,
                backoff_multiplier=retry_config.backoff_multiplier,
                backoff_jitter=retry_config.backoff_jitter,
            )

        if http_client is not None and (
            proxy is not None or verify_ssl is not None
        ):
            raise ValueError(
                "proxy and verify_ssl must not be set when "
                "http_client is supplied; configure the "
                "http_client directly instead."
            )

        if skip_language_check:
            warnings.warn(
                "skip_language_check is deprecated and has no effect.",
                DeprecationWarning,
                stacklevel=2,
            )

        if http_client is None:
            from .aiohttp_client import AioHttpClient

            http_client = AioHttpClient(
                proxy=proxy,
                verify_ssl=verify_ssl,
            )

        self._http_client = http_client
        if hasattr(http_client, "http_library_info"):
            self._http_library_info = http_client.http_library_info
        if _hc.user_agent is not None:
            self.set_user_agent(_hc.user_agent)
        self._retry_config = retry_config
        self._sleep_fn: Callable[[float], Awaitable[None]] = (
            _sleep_fn if _sleep_fn is not None else asyncio.sleep
        )
        self.headers: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Context manager / lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        if hasattr(self, "_http_client"):
            await self._http_client.close()

    async def __aenter__(self) -> "DeepLClientAsync":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal: retry loop
    # ------------------------------------------------------------------

    async def _send_with_backoff(self, request: HttpRequest) -> HttpResponse:
        """Send a request with exponential-backoff retry.

        Async version of :meth:`DeepLClient._send_with_backoff`.
        """
        max_retries = self._retry_config.max_retries
        min_timeout = self._retry_config.min_connection_timeout

        auth_headers = self._make_auth_headers()
        merged_headers = {**auth_headers, **self.headers, **request.headers}
        base_request = HttpRequest(
            method=request.method,
            url=request.url,
            headers=merged_headers,
            body=request.body,
            multipart=request.multipart,
        )

        util.log_info(
            "Request to DeepL API",
            method=base_request.method,
            url=base_request.url,
        )
        if base_request.body:
            try:
                body_json = json_module.loads(base_request.body)
            except Exception:
                body_json = base_request.body.decode("utf-8", errors="replace")
            util.log_debug("Request details", data={}, json=body_json)
        elif base_request.multipart:
            util.log_debug(
                "Request details",
                data=base_request.multipart.fields,
                json=None,
            )
        else:
            util.log_debug("Request details", data={}, json=None)

        timer = BackoffTimer(self._retry_config)
        while True:
            request = HttpRequest(
                method=base_request.method,
                url=base_request.url,
                headers=base_request.headers,
                body=base_request.body,
                multipart=base_request.multipart,
                timeout=timer.get_timeout(min_timeout),
            )
            response: Optional[HttpResponse] = None
            exception: Optional[ConnectionException] = None
            try:
                response = await self._http_client.send(request)
            except ConnectionException as e:
                exception = e

            if exception is not None:
                if (
                    exception.should_retry
                    and timer.get_num_retries() < max_retries
                ):
                    util.log_info(
                        f"Encountered a retryable-exception: {exception}"
                    )
                    util.log_info(
                        f"Starting retry {timer.get_num_retries() + 1} after "
                        f"{timer.get_time_until_deadline():.2f}s"
                    )
                    await self._sleep_fn(timer.get_time_until_deadline())
                    timer.advance()
                    continue
                raise exception

            assert response is not None
            util.log_info(
                "DeepL API response",
                url=request.url,
                status_code=response.status_code,
            )
            status = response.status_code
            if (
                status == 429 or status >= 500
            ) and timer.get_num_retries() < max_retries:
                util.log_info(
                    f"Starting retry {timer.get_num_retries() + 1} for "
                    f"HTTP {status} after "
                    f"{timer.get_time_until_deadline():.2f}s"
                )
                await self._sleep_fn(timer.get_time_until_deadline())
                timer.advance()
                continue

            return response

    async def _send_streaming_with_backoff(self, request: HttpRequest) -> Any:
        """Like _send_with_backoff but for streaming (document download)."""
        max_retries = self._retry_config.max_retries
        min_timeout = self._retry_config.min_connection_timeout

        auth_headers = self._make_auth_headers()
        merged_headers = {**auth_headers, **self.headers, **request.headers}
        base_request = HttpRequest(
            method=request.method,
            url=request.url,
            headers=merged_headers,
            body=request.body,
            multipart=request.multipart,
        )

        util.log_info(
            "Request to DeepL API",
            method=base_request.method,
            url=base_request.url,
        )

        timer = BackoffTimer(self._retry_config)
        while True:
            request = HttpRequest(
                method=base_request.method,
                url=base_request.url,
                headers=base_request.headers,
                body=base_request.body,
                multipart=base_request.multipart,
                timeout=timer.get_timeout(min_timeout),
            )
            exception: Optional[ConnectionException] = None
            streaming = None
            try:
                streaming = await self._http_client.send_streaming(request)
            except ConnectionException as e:
                exception = e

            if exception is not None:
                if (
                    exception.should_retry
                    and timer.get_num_retries() < max_retries
                ):
                    util.log_info(
                        f"Encountered a retryable-exception: {exception}"
                    )
                    util.log_info(
                        f"Starting retry {timer.get_num_retries() + 1} after "
                        f"{timer.get_time_until_deadline():.2f}s"
                    )
                    await self._sleep_fn(timer.get_time_until_deadline())
                    timer.advance()
                    continue
                raise exception

            assert streaming is not None
            util.log_info(
                "DeepL API response",
                url=request.url,
                status_code=streaming.status_code,
            )
            status = streaming.status_code
            if (
                status == 429 or status >= 500
            ) and timer.get_num_retries() < max_retries:
                util.log_info(
                    f"Starting retry {timer.get_num_retries() + 1} for "
                    f"HTTP {status} after "
                    f"{timer.get_time_until_deadline():.2f}s"
                )
                async for _ in streaming.aiter_content(65536):
                    pass
                await streaming.close()
                await self._sleep_fn(timer.get_time_until_deadline())
                timer.advance()
                continue

            return streaming

    # ------------------------------------------------------------------
    # Public API: text translation
    # ------------------------------------------------------------------

    async def translate_text(
        self,
        text: Union[str, Iterable[str]],
        *,
        source_lang: Union[str, Language, None] = None,
        target_lang: Union[str, Language],
        context: Optional[str] = None,
        split_sentences: Union[str, SplitSentences, None] = None,
        preserve_formatting: Optional[bool] = None,
        formality: Union[str, Formality, None] = None,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        tag_handling: Optional[str] = None,
        tag_handling_version: Optional[str] = None,
        outline_detection: Optional[bool] = None,
        non_splitting_tags: Union[str, List[str], None] = None,
        splitting_tags: Union[str, List[str], None] = None,
        ignore_tags: Union[str, List[str], None] = None,
        model_type: Union[str, ModelType, None] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        custom_instructions: Optional[List[str]] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> Union[TextResult, List[TextResult]]:
        request, multi_input = _build_translate_text_request(
            self._server_url,
            text,
            target_lang=target_lang,
            source_lang=source_lang,
            context=context,
            split_sentences=split_sentences,
            preserve_formatting=preserve_formatting,
            formality=formality,
            glossary=glossary,
            tag_handling=tag_handling,
            tag_handling_version=tag_handling_version,
            outline_detection=outline_detection,
            non_splitting_tags=non_splitting_tags,
            splitting_tags=splitting_tags,
            ignore_tags=ignore_tags,
            model_type=model_type,
            style_rule=style_rule,
            custom_instructions=custom_instructions,
            extra_body_parameters=extra_body_parameters,
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_translate_text_response(response, multi_input)

    async def translate_text_with_glossary(
        self,
        text: Union[str, Iterable[str]],
        glossary: GlossaryInfo,
        target_lang: Union[str, Language, None] = None,
        **kwargs: Any,
    ) -> Union[TextResult, List[TextResult]]:
        if not isinstance(glossary, GlossaryInfo):
            raise ValueError(
                "This function expects the glossary parameter to be an "
                "instance of GlossaryInfo."
            )
        if target_lang is None:
            target_lang = glossary.target_lang
            if target_lang == "EN":
                target_lang = "EN-GB"
        return await self.translate_text(
            text,
            source_lang=glossary.source_lang,
            target_lang=target_lang,
            glossary=glossary,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Public API: document translation
    # ------------------------------------------------------------------

    async def translate_document_from_filepath(
        self,
        input_path: Union[str, pathlib.PurePath],
        output_path: Union[str, pathlib.PurePath],
        *,
        source_lang: Optional[str] = None,
        target_lang: str,
        formality: Union[str, Formality] = Formality.DEFAULT,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        timeout_s: Optional[int] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentStatus:
        in_ext = pathlib.PurePath(input_path).suffix.lower()
        out_ext = pathlib.PurePath(output_path).suffix.lower()
        output_format = None if in_ext == out_ext else out_ext[1:]

        with open(input_path, "rb") as in_file:
            with open(output_path, "wb") as out_file:
                try:
                    return await self.translate_document(
                        in_file,
                        out_file,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        formality=formality,
                        glossary=glossary,
                        output_format=output_format,
                        timeout_s=timeout_s,
                        extra_body_parameters=extra_body_parameters,
                    )
                except Exception as e:
                    out_file.close()
                    await asyncio.to_thread(os.unlink, output_path)
                    raise e

    async def translate_document(
        self,
        input_document: Union[TextIO, BinaryIO, Any],
        output_document: Union[TextIO, BinaryIO, Any],
        *,
        source_lang: Optional[str] = None,
        target_lang: str,
        formality: Union[str, Formality] = Formality.DEFAULT,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        filename: Optional[str] = None,
        output_format: Optional[str] = None,
        timeout_s: Optional[int] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentStatus:
        handle = await self.translate_document_upload(
            input_document,
            target_lang=target_lang,
            source_lang=source_lang,
            formality=formality,
            glossary=glossary,
            filename=filename,
            output_format=output_format,
            extra_body_parameters=extra_body_parameters,
        )

        try:
            status = await self.translate_document_wait_until_done(
                handle, timeout_s
            )
            if status.ok:
                await self.translate_document_download(handle, output_document)
        except Exception as e:
            raise DocumentTranslationException(str(e), handle) from e

        if not status.ok:
            error_message = status.error_message or "unknown error"
            raise DocumentTranslationException(
                f"Error occurred while translating document: {error_message}",
                handle,
            )
        return status

    async def translate_document_upload(
        self,
        input_document: Union[TextIO, BinaryIO, str, bytes, Any],
        *,
        source_lang: Optional[str] = None,
        target_lang: str,
        formality: Union[str, Formality, None] = None,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        filename: Optional[str] = None,
        output_format: Optional[str] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentHandle:
        request = _build_document_upload_request(
            self._server_url,
            input_document,
            target_lang=target_lang,
            source_lang=source_lang,
            formality=formality,
            glossary=glossary,
            filename=filename,
            output_format=output_format,
            extra_body_parameters=extra_body_parameters,
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_document_upload_response(response)

    async def translate_document_get_status(
        self, handle: DocumentHandle
    ) -> DocumentStatus:
        request = _build_document_status_request(self._server_url, handle)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_document_status_response(response, handle)

    async def translate_document_wait_until_done(
        self,
        handle: DocumentHandle,
        timeout_s: Optional[int] = None,
    ) -> DocumentStatus:
        status = await self.translate_document_get_status(handle)
        start_time_s = time.time()
        while status.ok and not status.done:
            if (
                timeout_s is not None
                and time.time() - start_time_s > timeout_s
            ):
                raise DeepLException(
                    f"Manual timeout of {timeout_s}s exceeded for"
                    " document translation",
                    should_retry=False,
                )
            secs = (
                min(status.seconds_remaining, 5.0)
                if status.seconds_remaining is not None
                else 5.0
            )
            util.log_info(
                f"Rechecking document translation status "
                f"after sleeping for {secs:.3f} seconds."
            )
            await self._sleep_fn(secs)
            status = await self.translate_document_get_status(handle)
        return status

    async def translate_document_download(
        self,
        handle: DocumentHandle,
        output_file: Union[TextIO, BinaryIO, Any, None] = None,
        chunk_size: int = 1,
    ) -> Optional[Any]:
        """Download translated document.

        :param handle: DocumentHandle from translate_document_upload.
        :param output_file: (Optional) File-like object to write content to.
            If None, returns the raw streaming response.
        :param chunk_size: Chunk size in bytes when writing to output_file.
        :return: None if output_file provided, otherwise streaming response.
        """
        request = _build_document_download_request(self._server_url, handle)
        streaming = await self._send_streaming_with_backoff(request)

        if not (200 <= streaming.status_code < 400):
            content = b""
            async for chunk in streaming.aiter_content(65536):
                content += chunk
            await streaming.close()
            error_response = HttpResponse(
                status_code=streaming.status_code,
                headers=dict(streaming.headers),
                content=content,
            )
            self._raise_for_status(error_response, downloading_document=True)

        if output_file is not None:
            async for chunk in streaming.aiter_content(chunk_size=chunk_size):
                await asyncio.to_thread(output_file.write, chunk)
            await streaming.close()
            return None
        return streaming

    # ------------------------------------------------------------------
    # Public API: usage and languages
    # ------------------------------------------------------------------

    async def get_usage(self) -> Usage:
        request = _build_get_usage_request(self._server_url)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_usage_response(response)

    async def get_source_languages(
        self, skip_cache: bool = False
    ) -> List[Language]:
        request = _build_get_source_languages_request(self._server_url)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_source_languages_response(response)

    async def get_target_languages(
        self, skip_cache: bool = False
    ) -> List[Language]:
        request = _build_get_target_languages_request(self._server_url)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_target_languages_response(response)

    async def get_glossary_languages(self) -> List[GlossaryLanguagePair]:
        request = _build_get_glossary_languages_request(self._server_url)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_glossary_languages_response(response)

    # ------------------------------------------------------------------
    # Public API: classic (v2) glossaries
    # ------------------------------------------------------------------

    async def create_glossary(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        entries: Dict[str, str],
    ) -> GlossaryInfo:
        if not entries:
            raise ValueError("glossary entries must not be empty")
        return await self._create_glossary(
            name,
            source_lang,
            target_lang,
            "tsv",
            util.convert_dict_to_tsv(entries),
        )

    async def create_glossary_from_csv(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> GlossaryInfo:
        entries = (
            csv_data if isinstance(csv_data, (str, bytes)) else csv_data.read()
        )
        if not isinstance(entries, (bytes, str)):
            raise ValueError("Entries of the glossary are invalid")
        return await self._create_glossary(
            name, source_lang, target_lang, "csv", entries
        )

    async def _create_glossary(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        entries_format: str,
        entries: Union[str, bytes],
    ) -> GlossaryInfo:
        request = _build_create_glossary_request(
            self._server_url,
            name,
            source_lang,
            target_lang,
            entries_format,
            entries,
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_create_glossary_response(response)

    async def get_glossary(self, glossary_id: str) -> GlossaryInfo:
        request = _build_get_glossary_request(self._server_url, glossary_id)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_get_glossary_response(response)

    async def list_glossaries(self) -> List[GlossaryInfo]:
        request = _build_list_glossaries_request(self._server_url)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_list_glossaries_response(response)

    async def get_glossary_entries(
        self, glossary: Union[str, GlossaryInfo]
    ) -> dict:
        request = _build_get_glossary_entries_request(
            self._server_url, glossary
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_get_glossary_entries_response(response)

    async def delete_glossary(
        self, glossary: Union[str, GlossaryInfo]
    ) -> None:
        request = _build_delete_glossary_request(self._server_url, glossary)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)

    # ------------------------------------------------------------------
    # Public API: multilingual (v3) glossaries
    # ------------------------------------------------------------------

    async def create_multilingual_glossary(
        self,
        name: str,
        glossary_dicts: List[MultilingualGlossaryDictionaryEntries],
    ) -> MultilingualGlossaryInfo:
        if any(not d.entries for d in glossary_dicts):
            raise ValueError("glossary entries must not be empty")
        return await self._create_multilingual_glossary(name, glossary_dicts)

    async def create_multilingual_glossary_from_csv(
        self,
        name: str,
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> MultilingualGlossaryInfo:
        entries = util.convert_csv_to_dict(csv_data)
        dictionaries = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        return await self._create_multilingual_glossary(name, dictionaries)

    async def _create_multilingual_glossary(
        self,
        name: str,
        glossary_dicts: List[MultilingualGlossaryDictionaryEntries],
    ) -> MultilingualGlossaryInfo:
        request = _build_create_multilingual_glossary_request(
            self._server_url, name, glossary_dicts
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    async def update_multilingual_glossary_name(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        name: str,
    ) -> MultilingualGlossaryInfo:
        request = _build_update_multilingual_glossary_name_request(
            self._server_url, glossary, name
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    async def update_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        glossary_dict: MultilingualGlossaryDictionaryEntries,
    ) -> MultilingualGlossaryInfo:
        if not glossary_dict or not glossary_dict.entries:
            raise ValueError("glossary entries must not be empty")
        request = _build_update_multilingual_glossary_dict_request(
            self._server_url, glossary, [glossary_dict]
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    async def replace_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        glossary_dict: MultilingualGlossaryDictionaryEntries,
    ) -> MultilingualGlossaryDictionaryInfo:
        if not glossary_dict or not glossary_dict.entries:
            raise ValueError("glossary entries must not be empty")
        request = _build_replace_multilingual_glossary_dict_request(
            self._server_url,
            glossary,
            glossary_dict.source_lang,
            glossary_dict.target_lang,
            glossary_dict.entries,
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_dict_response(response)

    async def get_multilingual_glossary(
        self, glossary_id: str
    ) -> MultilingualGlossaryInfo:
        request = _build_get_multilingual_glossary_request(
            self._server_url, glossary_id
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    async def list_multilingual_glossaries(
        self,
    ) -> List[MultilingualGlossaryInfo]:
        request = _build_list_multilingual_glossaries_request(self._server_url)
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_list_multilingual_glossaries_response(response)

    async def get_multilingual_glossary_entries(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
    ) -> MultilingualGlossaryDictionaryEntriesResponse:
        request = _build_get_multilingual_glossary_entries_request(
            self._server_url, glossary, source_lang, target_lang
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_entries_response(response)

    async def delete_multilingual_glossary(
        self, glossary: Union[str, MultilingualGlossaryInfo]
    ) -> None:
        request = _build_delete_multilingual_glossary_request(
            self._server_url, glossary
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)

    async def delete_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        dictionary: Optional[MultilingualGlossaryDictionaryInfo] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> None:
        request = _build_delete_multilingual_glossary_dict_request(
            self._server_url, glossary, source_lang, target_lang, dictionary
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)

    # ------------------------------------------------------------------
    # Public API: Write (rephrase)
    # ------------------------------------------------------------------

    async def rephrase_text(
        self,
        text: Union[str, Iterable[str]],
        *,
        target_lang: Union[None, str, Language] = None,
        style: Optional[str] = None,
        tone: Optional[str] = None,
    ) -> Union[WriteResult, List[WriteResult]]:
        request, multi_input = _build_rephrase_text_request(
            self._server_url,
            text,
            target_lang=target_lang,
            style=style,
            tone=tone,
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_rephrase_text_response(response, multi_input)

    # ------------------------------------------------------------------
    # Public API: style rules
    # ------------------------------------------------------------------

    async def get_all_style_rules(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        detailed: Optional[bool] = None,
    ) -> List[StyleRuleInfo]:
        request = _build_get_style_rules_request(
            self._server_url, page, page_size, detailed
        )
        response = await self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_style_rules_response(response)
