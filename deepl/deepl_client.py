# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import os
import pathlib
import time
import warnings
from typing import (
    Any,
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
    CustomInstruction,
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
    TranslationMemoryInfo,
    Usage,
    WriteResult,
)
from ._backoff_timer import BackoffTimer
from ._client_base import _ClientBase
from ._http_types import (
    HttpRequest,
    HttpResponse,
    SslConfig,
    StreamingHttpResponse,
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
    _build_create_style_rule_custom_instruction_request,
    _build_create_style_rule_request,
    _build_delete_style_rule_custom_instruction_request,
    _build_delete_style_rule_request,
    _build_get_style_rule_custom_instruction_request,
    _build_get_style_rule_request,
    _build_get_style_rules_request,
    _build_get_target_languages_request,
    _build_update_style_rule_configured_rules_request,
    _build_update_style_rule_custom_instruction_request,
    _build_update_style_rule_name_request,
    _build_get_usage_request,
    _build_list_glossaries_request,
    _build_list_multilingual_glossaries_request,
    _build_list_translation_memories_request,
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
    _parse_custom_instruction_response,
    _parse_get_style_rules_response,
    _parse_get_target_languages_response,
    _parse_style_rule_response,
    _parse_get_usage_response,
    _parse_list_glossaries_response,
    _parse_list_multilingual_glossaries_response,
    _parse_multilingual_glossary_dict_response,
    _parse_multilingual_glossary_entries_response,
    _parse_multilingual_glossary_response,
    _parse_list_translation_memories_response,
    _parse_rephrase_text_response,
    _parse_translate_text_response,
)
from .exceptions import (
    ConnectionException,
    DeepLException,
    DocumentTranslationException,
)
from .ihttp_client import HttpClientProtocol
from .requests_client import RequestsClient
from .retry_config import RetryConfig
from . import util

_DEFAULT_RETRY_CONFIG = RetryConfig()


class DeepLClient(_ClientBase):
    """Client for the DeepL API.

    :param auth_key: Authentication key as found in your DeepL API account.
    :param server_url: (Optional) Base URL of DeepL API, can be overridden
        for testing purposes.
    :param proxy: (Optional) Proxy URL string or dict with ``"http"``/
        ``"https"`` keys. Forwarded to the default :class:`RequestsClient`.
        Raises :exc:`ValueError` if ``http_client`` is also supplied.
    :param send_platform_info: (Optional) If True (default), include OS and
        Python version in User-Agent header.
    :param verify_ssl: (Optional) SSL certificate verification. Forwarded to
        the default :class:`RequestsClient`. Raises :exc:`ValueError` if
        ``http_client`` is also supplied. See :data:`SslConfig`.
    :param http_client: (Optional) Custom HTTP client implementing
        :class:`~deepl.HttpClientProtocol`. When supplied, ``proxy`` and
        ``verify_ssl`` must not be set.
    :param retry_config: (Optional) Backoff/retry settings. Applies regardless
        of which ``http_client`` is used.
    :param skip_language_check: Deprecated, no-op. Will be removed in a
        future version.
    """

    def __init__(
        self,
        auth_key: str,
        *,
        server_url: Optional[str] = None,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: bool = True,
        verify_ssl: SslConfig = None,
        http_client: Optional[HttpClientProtocol] = None,
        retry_config: RetryConfig = _DEFAULT_RETRY_CONFIG,
        skip_language_check: bool = False,
        _sleep_fn: Optional[Callable[[float], None]] = None,
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

        resolved_client: HttpClientProtocol
        if http_client is None:
            resolved_client = RequestsClient(
                proxy=proxy,
                verify_ssl=verify_ssl,
            )
        else:
            resolved_client = http_client

        self._http_client = resolved_client
        self._http_library_info = resolved_client.http_library_info
        if _hc.user_agent is not None:
            self.set_user_agent(_hc.user_agent)
        self._retry_config = retry_config
        self._sleep_fn: Callable[[float], None] = (
            _sleep_fn if _sleep_fn is not None else time.sleep
        )
        self.headers: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Context manager / lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        if hasattr(self, "_http_client"):
            self._http_client.close()

    def __enter__(self) -> "DeepLClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal: retry loop
    # ------------------------------------------------------------------

    def _send_with_backoff(self, request: HttpRequest) -> HttpResponse:
        """Send a request with exponential-backoff retry.

        Adds auth headers, then retries on ConnectionException (with
        should_retry=True), 429, and 5xx up to retry_config.max_retries times.
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
                response = self._http_client.send(request)
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
                    self._sleep_fn(timer.get_time_until_deadline())
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
            # Retry on 429 and any 5xx uniformly. The retry decision is made
            # here before _raise_for_status, so it is independent of the
            # should_retry flag on the eventual exception. All 5xx responses
            # are considered transient at this layer.
            if (
                status == 429 or status >= 500
            ) and timer.get_num_retries() < max_retries:
                util.log_info(
                    f"Starting retry {timer.get_num_retries() + 1} for "
                    f"HTTP {status} after "
                    f"{timer.get_time_until_deadline():.2f}s"
                )
                self._sleep_fn(timer.get_time_until_deadline())
                timer.advance()
                continue

            return response

    def _send_streaming_with_backoff(
        self, request: HttpRequest
    ) -> StreamingHttpResponse:
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
            try:
                streaming = self._http_client.send_streaming(request)
            except ConnectionException as e:
                exception = e
                streaming = None  # type: ignore[assignment]

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
                    self._sleep_fn(timer.get_time_until_deadline())
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
                # Consume and discard the error body before retrying.
                for _ in streaming.iter_content(65536):
                    pass
                self._sleep_fn(timer.get_time_until_deadline())
                timer.advance()
                continue

            return streaming

    # ------------------------------------------------------------------
    # Public API: text translation
    # ------------------------------------------------------------------

    def translate_text(
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
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        custom_instructions: Optional[List[str]] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> Union[TextResult, List[TextResult]]:
        """Translate text(s) into the target language.

        :param text: Text to translate.
        :type text: UTF-8 :class:`str`; string sequence (list, tuple,
            iterator, generator)
        :param source_lang: (Optional) Language code of input text, for
            example "DE", "EN", "FR". If omitted, DeepL will auto-detect.
        :param target_lang: Language code to translate into, e.g. "DE",
            "EN-US", "FR".
        :param context: (Optional) Additional context text (not translated).
        :param split_sentences: (Optional) Controls sentence splitting.
        :param preserve_formatting: (Optional) Preserve formatting.
        :param formality: (Optional) Desired formality level.
        :param glossary: (Optional) Glossary or glossary ID.
        :param tag_handling: (Optional) "xml" or "html".
        :param tag_handling_version: (Optional) "v1" or "v2".
        :param outline_detection: (Optional) Set False to disable auto
            tag detection.
        :param non_splitting_tags: (Optional) XML tags that should not
            split a sentence.
        :param splitting_tags: (Optional) XML tags that should split a
            sentence.
        :param ignore_tags: (Optional) XML tags whose content should not
            be translated.
        :param model_type: (Optional) Translation model quality level.
        :param style_rule: (Optional) Style rule or style rule ID.
        :param translation_memory: (Optional) Translation memory or ID.
        :param translation_memory_threshold: (Optional) Minimum match
            percentage for fuzzy matches (0-100).
        :param custom_instructions: (Optional) List of custom instructions.
        :param extra_body_parameters: (Optional) Additional JSON body fields.
        :return: List of TextResult objects, or a single TextResult if input
            was a single string.
        """
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
            translation_memory=translation_memory,
            translation_memory_threshold=translation_memory_threshold,
            custom_instructions=custom_instructions,
            extra_body_parameters=extra_body_parameters,
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_translate_text_response(response, multi_input)

    def translate_text_with_glossary(
        self,
        text: Union[str, Iterable[str]],
        glossary: GlossaryInfo,
        target_lang: Union[str, Language, None] = None,
        **kwargs: Any,
    ) -> Union[TextResult, List[TextResult]]:
        """Translate text using given glossary.

        Source and target languages are assumed to match the glossary.
        Note: if glossary target language is EN, translates into EN-GB.
        Specify target_lang="EN-US" to translate into American English.

        :param text: Text to translate.
        :param glossary: GlossaryInfo to use.
        :param target_lang: Override target language of glossary.
        """
        if not isinstance(glossary, GlossaryInfo):
            raise ValueError(
                "This function expects the glossary parameter to be an "
                "instance of GlossaryInfo. Use get_glossary() to obtain a "
                "GlossaryInfo using the glossary ID of an existing "
                "glossary. Alternatively, use translate_text() and "
                "specify the glossary ID using the glossary parameter. "
            )

        if target_lang is None:
            target_lang = glossary.target_lang
            if target_lang == "EN":
                target_lang = "EN-GB"

        return self.translate_text(
            text,
            source_lang=glossary.source_lang,
            target_lang=target_lang,
            glossary=glossary,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Public API: document translation
    # ------------------------------------------------------------------

    def translate_document_from_filepath(
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
        """Upload document at given input path, translate, and download."""
        in_ext = pathlib.PurePath(input_path).suffix.lower()
        out_ext = pathlib.PurePath(output_path).suffix.lower()
        output_format = None if in_ext == out_ext else out_ext[1:]

        with open(input_path, "rb") as in_file:
            with open(output_path, "wb") as out_file:
                try:
                    return self.translate_document(
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
                except Exception:
                    out_file.close()
                    os.unlink(output_path)
                    raise

    def translate_document(
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
        """Upload document, translate, and download result."""
        handle = self.translate_document_upload(
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
            status = self.translate_document_wait_until_done(handle, timeout_s)
            if status.ok:
                self.translate_document_download(handle, output_document)
        except Exception as e:
            raise DocumentTranslationException(str(e), handle) from e

        if not status.ok:
            error_message = status.error_message or "unknown error"
            raise DocumentTranslationException(
                f"Error occurred while translating document: {error_message}",
                handle,
            )
        return status

    def translate_document_upload(
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
        """Upload a document for translation; return the document handle."""
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
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_document_upload_response(response)

    def translate_document_get_status(
        self, handle: DocumentHandle
    ) -> DocumentStatus:
        """Get the translation status for the given document handle."""
        request = _build_document_status_request(self._server_url, handle)
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_document_status_response(response, handle)

    def translate_document_wait_until_done(
        self,
        handle: DocumentHandle,
        timeout_s: Optional[int] = None,
    ) -> DocumentStatus:
        """Poll document status until translation completes or fails."""
        status = self.translate_document_get_status(handle)
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
            self._sleep_fn(secs)
            status = self.translate_document_get_status(handle)
        return status

    def translate_document_download(
        self,
        handle: DocumentHandle,
        output_file: Union[TextIO, BinaryIO, Any, None] = None,
        chunk_size: int = 1,
    ) -> Optional[Any]:
        """Download translated document.

        :param handle: DocumentHandle from translate_document_upload.
        :param output_file: (Optional) File-like object to write content to.
            If None, returns a streaming response; call iter_content() on it.
        :param chunk_size: Chunk size in bytes when writing to output_file.
        :return: None if output_file provided, otherwise streaming response.
        """
        request = _build_document_download_request(self._server_url, handle)
        streaming = self._send_streaming_with_backoff(request)

        if not (200 <= streaming.status_code < 400):
            # Consume body to get error details.
            content = b"".join(streaming.iter_content(65536))
            error_response = HttpResponse(
                status_code=streaming.status_code,
                headers=dict(streaming.headers),
                content=content,
            )
            self._raise_for_status(error_response, downloading_document=True)

        if output_file is not None:
            for chunk in streaming.iter_content(chunk_size=chunk_size):
                output_file.write(chunk)  # type: ignore[arg-type]
            return None
        return streaming

    # ------------------------------------------------------------------
    # Public API: usage and languages
    # ------------------------------------------------------------------

    def get_usage(self) -> Usage:
        """Request the current API usage."""
        request = _build_get_usage_request(self._server_url)
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_usage_response(response)

    def get_source_languages(self, skip_cache: bool = False) -> List[Language]:
        """Request the list of available source languages.

        :param skip_cache: Deprecated, no-op.
        """
        request = _build_get_source_languages_request(self._server_url)
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_source_languages_response(response)

    def get_target_languages(self, skip_cache: bool = False) -> List[Language]:
        """Request the list of available target languages.

        :param skip_cache: Deprecated, no-op.
        """
        request = _build_get_target_languages_request(self._server_url)
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_target_languages_response(response)

    def get_glossary_languages(self) -> List[GlossaryLanguagePair]:
        """Request the list of language pairs supported for glossaries."""
        request = _build_get_glossary_languages_request(self._server_url)
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_glossary_languages_response(response)

    # ------------------------------------------------------------------
    # Public API: classic (v2) glossaries
    # ------------------------------------------------------------------

    def create_glossary(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        entries: Dict[str, str],
    ) -> GlossaryInfo:
        """Create a v2 glossary with given name and entries."""
        if not entries:
            raise ValueError("glossary entries must not be empty")
        return self._create_glossary(
            name,
            source_lang,
            target_lang,
            "tsv",
            util.convert_dict_to_tsv(entries),
        )

    def create_glossary_from_csv(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> GlossaryInfo:
        """Create a v2 glossary from CSV data."""
        entries = (
            csv_data if isinstance(csv_data, (str, bytes)) else csv_data.read()
        )
        if not isinstance(entries, (bytes, str)):
            raise ValueError("Entries of the glossary are invalid")
        return self._create_glossary(
            name, source_lang, target_lang, "csv", entries
        )

    def _create_glossary(
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
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_create_glossary_response(response)

    def get_glossary(self, glossary_id: str) -> GlossaryInfo:
        """Retrieve GlossaryInfo for the given glossary ID."""
        request = _build_get_glossary_request(self._server_url, glossary_id)
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_get_glossary_response(response)

    def list_glossaries(self) -> List[GlossaryInfo]:
        """Retrieve GlossaryInfo for all available glossaries."""
        request = _build_list_glossaries_request(self._server_url)
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_list_glossaries_response(response)

    def get_glossary_entries(self, glossary: Union[str, GlossaryInfo]) -> dict:
        """Retrieve the entries of the specified glossary as a dict."""
        request = _build_get_glossary_entries_request(
            self._server_url, glossary
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_get_glossary_entries_response(response)

    def delete_glossary(self, glossary: Union[str, GlossaryInfo]) -> None:
        """Delete the specified glossary."""
        request = _build_delete_glossary_request(self._server_url, glossary)
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)

    # ------------------------------------------------------------------
    # Public API: multilingual (v3) glossaries
    # ------------------------------------------------------------------

    def create_multilingual_glossary(
        self,
        name: str,
        glossary_dicts: List[MultilingualGlossaryDictionaryEntries],
    ) -> MultilingualGlossaryInfo:
        """Create a multilingual glossary."""
        if any(not d.entries for d in glossary_dicts):
            raise ValueError("glossary entries must not be empty")
        return self._create_multilingual_glossary(name, glossary_dicts)

    def create_multilingual_glossary_from_csv(
        self,
        name: str,
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> MultilingualGlossaryInfo:
        """Create a multilingual glossary from CSV data."""
        entries = util.convert_csv_to_dict(csv_data)
        dictionaries = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        return self._create_multilingual_glossary(name, dictionaries)

    def _create_multilingual_glossary(
        self,
        name: str,
        glossary_dicts: List[MultilingualGlossaryDictionaryEntries],
    ) -> MultilingualGlossaryInfo:
        request = _build_create_multilingual_glossary_request(
            self._server_url, name, glossary_dicts
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    def update_multilingual_glossary_name(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        name: str,
    ) -> MultilingualGlossaryInfo:
        """Update the name of a multilingual glossary."""
        request = _build_update_multilingual_glossary_name_request(
            self._server_url, glossary, name
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    def update_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        glossary_dict: MultilingualGlossaryDictionaryEntries,
    ) -> MultilingualGlossaryInfo:
        """Update or create a dictionary in a multilingual glossary."""
        if not glossary_dict or not glossary_dict.entries:
            raise ValueError("glossary entries must not be empty")
        request = _build_update_multilingual_glossary_dict_request(
            self._server_url, glossary, [glossary_dict]
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    def update_multilingual_glossary_dictionary_from_csv(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> MultilingualGlossaryInfo:
        """Update or create a dictionary from CSV data."""
        entries = util.convert_csv_to_dict(csv_data)
        dictionaries = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        request = _build_update_multilingual_glossary_dict_request(
            self._server_url, glossary, dictionaries
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    def replace_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        glossary_dict: MultilingualGlossaryDictionaryEntries,
    ) -> MultilingualGlossaryDictionaryInfo:
        """Replace a dictionary in a multilingual glossary."""
        if not glossary_dict or not glossary_dict.entries:
            raise ValueError("glossary entries must not be empty")
        request = _build_replace_multilingual_glossary_dict_request(
            self._server_url,
            glossary,
            glossary_dict.source_lang,
            glossary_dict.target_lang,
            glossary_dict.entries,
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_dict_response(response)

    def replace_multilingual_glossary_dictionary_from_csv(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> MultilingualGlossaryDictionaryInfo:
        """Replace a glossary dictionary from CSV data."""
        entries = util.convert_csv_to_dict(csv_data)
        request = _build_replace_multilingual_glossary_dict_request(
            self._server_url, glossary, source_lang, target_lang, entries
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_dict_response(response)

    def get_multilingual_glossary(
        self, glossary_id: str
    ) -> MultilingualGlossaryInfo:
        """Retrieve a multilingual glossary by ID."""
        request = _build_get_multilingual_glossary_request(
            self._server_url, glossary_id
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_response(response)

    def list_multilingual_glossaries(self) -> List[MultilingualGlossaryInfo]:
        """List all available multilingual glossaries."""
        request = _build_list_multilingual_glossaries_request(self._server_url)
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_list_multilingual_glossaries_response(response)

    def get_multilingual_glossary_entries(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
    ) -> MultilingualGlossaryDictionaryEntriesResponse:
        """Retrieve entries for a language pair in a multilingual glossary."""
        request = _build_get_multilingual_glossary_entries_request(
            self._server_url, glossary, source_lang, target_lang
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)
        return _parse_multilingual_glossary_entries_response(response)

    def delete_multilingual_glossary(
        self, glossary: Union[str, MultilingualGlossaryInfo]
    ) -> None:
        """Delete a multilingual glossary."""
        request = _build_delete_multilingual_glossary_request(
            self._server_url, glossary
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)

    def delete_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        dictionary: Optional[MultilingualGlossaryDictionaryInfo] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> None:
        """Delete a specific dictionary from a multilingual glossary."""
        request = _build_delete_multilingual_glossary_dict_request(
            self._server_url, glossary, source_lang, target_lang, dictionary
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response, glossary=True)

    # ------------------------------------------------------------------
    # Public API: Write (rephrase)
    # ------------------------------------------------------------------

    def rephrase_text(
        self,
        text: Union[str, Iterable[str]],
        *,
        target_lang: Union[None, str, Language] = None,
        style: Optional[str] = None,
        tone: Optional[str] = None,
    ) -> Union[WriteResult, List[WriteResult]]:
        """Improve the text(s) using the Write API.

        :param text: Text to improve.
        :param target_lang: (Optional) Target language code.
        :param style: (Optional) Writing style. Mutually exclusive with tone.
        :param tone: (Optional) Tone. Mutually exclusive with style.
        :return: Single WriteResult or list of WriteResult objects.
        """
        request, multi_input = _build_rephrase_text_request(
            self._server_url,
            text,
            target_lang=target_lang,
            style=style,
            tone=tone,
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_rephrase_text_response(response, multi_input)

    # ------------------------------------------------------------------
    # Public API: style rules
    # ------------------------------------------------------------------

    def get_all_style_rules(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        detailed: Optional[bool] = None,
    ) -> List[StyleRuleInfo]:
        """Retrieve all available style rules."""
        request = _build_get_style_rules_request(
            self._server_url, page, page_size, detailed
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_get_style_rules_response(response)

    def create_style_rule(
        self,
        name: str,
        language: str,
        configured_rules: Optional[dict] = None,
        custom_instructions: Optional[List[dict]] = None,
    ) -> StyleRuleInfo:
        """Create a new style rule."""
        if not name:
            raise ValueError("name must not be empty")
        if not language:
            raise ValueError("language must not be empty")
        request = _build_create_style_rule_request(
            self._server_url,
            name,
            language,
            configured_rules,
            custom_instructions,
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_style_rule_response(response)

    def get_style_rule(
        self,
        style_rule: Union[str, StyleRuleInfo],
    ) -> StyleRuleInfo:
        """Retrieve a single style rule by ID."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        request = _build_get_style_rule_request(self._server_url, style_rule)
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_style_rule_response(response)

    def update_style_rule_name(
        self,
        style_rule: Union[str, StyleRuleInfo],
        name: str,
    ) -> StyleRuleInfo:
        """Update the name of a style rule."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not name:
            raise ValueError("name must not be empty")
        request = _build_update_style_rule_name_request(
            self._server_url, style_rule, name
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_style_rule_response(response)

    def delete_style_rule(
        self,
        style_rule: Union[str, StyleRuleInfo],
    ) -> None:
        """Delete a style rule."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        request = _build_delete_style_rule_request(
            self._server_url, style_rule
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)

    def update_style_rule_configured_rules(
        self,
        style_rule: Union[str, StyleRuleInfo],
        configured_rules: dict,
    ) -> StyleRuleInfo:
        """Replace the configured rules of a style rule."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        request = _build_update_style_rule_configured_rules_request(
            self._server_url, style_rule, configured_rules
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_style_rule_response(response)

    def create_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
    ) -> CustomInstruction:
        """Create a custom instruction for a style rule."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not label:
            raise ValueError("label must not be empty")
        if not prompt:
            raise ValueError("prompt must not be empty")
        request = _build_create_style_rule_custom_instruction_request(
            self._server_url, style_rule, label, prompt, source_language
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_custom_instruction_response(response)

    def get_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: str,
    ) -> CustomInstruction:
        """Retrieve a custom instruction by ID."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not instruction_id:
            raise ValueError("instruction_id must not be empty")
        request = _build_get_style_rule_custom_instruction_request(
            self._server_url, style_rule, instruction_id
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_custom_instruction_response(response)

    def update_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: str,
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
    ) -> CustomInstruction:
        """Update a custom instruction."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not instruction_id:
            raise ValueError("instruction_id must not be empty")
        if not label:
            raise ValueError("label must not be empty")
        if not prompt:
            raise ValueError("prompt must not be empty")
        request = _build_update_style_rule_custom_instruction_request(
            self._server_url,
            style_rule,
            instruction_id,
            label,
            prompt,
            source_language,
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_custom_instruction_response(response)

    def delete_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: str,
    ) -> None:
        """Delete a custom instruction from a style rule."""
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not instruction_id:
            raise ValueError("instruction_id must not be empty")
        request = _build_delete_style_rule_custom_instruction_request(
            self._server_url, style_rule, instruction_id
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)

    def list_translation_memories(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[TranslationMemoryInfo]:
        """Retrieves a list of TranslationMemoryInfo for available
        translation memories. The maximum number of translation memories
        returned is controlled by page_size (max 25).

        :param page: Page number for pagination, 0-indexed (optional).
        :param page_size: Number of items per page (optional).
        :return: List of TranslationMemoryInfo objects.
        """
        request = _build_list_translation_memories_request(
            self._server_url, page=page, page_size=page_size
        )
        response = self._send_with_backoff(request)
        self._raise_for_status(response)
        return _parse_list_translation_memories_response(response)
