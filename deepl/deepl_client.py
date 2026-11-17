# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.api_data import (
    AppInfo,
    CustomInstruction,
    DocumentHandle,
    DocumentStatus,
    Formality,
    GlossaryInfo,
    GlossaryLanguagePair,
    Language,
    LanguageInclude,
    LanguageResource,
    LanguageResourceName,
    LanguageSupport,
    ModelType,
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryDictionaryInfo,
    MultilingualGlossaryInfo,
    SplitSentences,
    SpokenTerms,
    SpokenTermsEntries,
    SpokenTermsList,
    StyleProfile,
    StyleRuleInfo,
    TagHandlingMode,
    TagHandlingVersion,
    TextResult,
    TranslationMemoryExport,
    TranslationMemoryImport,
    TranslationMemoryInfo,
    TranslationMemoryJob,
    TranslationMemorySegments,
    Usage,
    WriteResult,
    WritingStyle,
    WritingTone,
    _malformed_response,
)
from deepl.exceptions import (
    ConnectionException,
    DeepLException,
    DocumentTranslationException,
    NotFoundException,
    TranslationMemoryJobException,
)
from deepl import _http_client, util
from deepl._base_client import BaseClient
import json as json_module
import os
import pathlib
import requests  # type: ignore
import time
import urllib.parse
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    TextIO,
    TypeVar,
    Union,
)


def _quote_path(value: str) -> str:
    """URL-encodes a value for use as a single URL path segment."""
    return urllib.parse.quote(value, safe="")


def _check_target_lang_given(
    method: str, target_lang: Union[str, Language, None]
) -> Union[str, Language]:
    if target_lang is None:
        raise TypeError(f"{method}() missing required argument: 'target_lang'")
    return target_lang


def _check_language(name: str, value: Union[str, Language, None]) -> None:
    """Raises ValueError for an empty language code."""
    if value is not None and not str(value):
        raise ValueError(f"{name} must not be empty")


def _resource_id(value: str, name: str) -> str:
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


# Default chunk size for writing downloads into output_file.
_DOWNLOAD_CHUNK_SIZE = 64 * 1024


def _required_str(json: dict, key: str) -> str:
    value = json[key]
    if not isinstance(value, str):
        raise TypeError(f"{key!r} is not a string")
    return value


def _document_translation_exception(
    cause: Exception, handle: Optional[DocumentHandle]
) -> DocumentTranslationException:
    if isinstance(cause, DeepLException):
        return DocumentTranslationException(
            str(cause),
            handle,
            should_retry=cause.should_retry,
            http_status_code=cause.http_status_code,
        )
    return DocumentTranslationException(str(cause), handle)


def _tm_job_exception(
    cause: Exception,
    job_id: Optional[str],
    job: Optional[TranslationMemoryJob],
    message: Optional[str] = None,
) -> TranslationMemoryJobException:
    if isinstance(cause, DeepLException):
        return TranslationMemoryJobException(
            message or str(cause),
            job_id,
            job,
            should_retry=cause.should_retry,
            http_status_code=cause.http_status_code,
        )
    return TranslationMemoryJobException(message or str(cause), job_id, job)


_T = TypeVar("_T")


def _tm_job_error_message(job: TranslationMemoryJob) -> str:
    return (
        job.result.error_message if job.result else None
    ) or "unknown error"


def _tm_job_action(job: TranslationMemoryJob) -> str:
    if job.operation == TranslationMemoryJob.OPERATION_IMPORT:
        return "importing"
    if job.operation == TranslationMemoryJob.OPERATION_EXPORT:
        return "exporting"
    return "processing"


def _parse_improvements(json: Any, text_count: int) -> List[WriteResult]:
    improvements = json.get("improvements") if isinstance(json, dict) else None
    if not isinstance(improvements, list) or len(improvements) < text_count:
        raise DeepLException(
            "Unexpected response: expected an improvements list with "
            f"{text_count} entries"
        )
    output = []
    for improvement in improvements:
        if not isinstance(improvement, dict) or not isinstance(
            improvement.get("text"), str
        ):
            raise DeepLException(
                "Unexpected response: improvement without text"
            )
        output.append(
            WriteResult(
                improvement["text"],
                improvement.get("detected_source_language", ""),
                improvement.get("target_language", ""),
            )
        )
    return output


class DeepLClient(BaseClient):
    """Client for the DeepL API.

    :param auth_key: Authentication key as found in your DeepL API account.
    :param server_url: (Optional) Base URL of DeepL API, can be overridden e.g.
        for testing purposes. Must be an absolute http or https URL with a
        host, otherwise ValueError is raised.
    :param proxy: (Optional) Proxy server URL string or dictionary containing
        URL strings for the 'http' and 'https' keys. This is passed to the
        underlying requests session, see the requests proxy documentation for
        more information. Raises ValueError if a proxy URL has no host or a
        scheme other than http, https, socks4, socks4a, socks5 or socks5h; a
        URL without a scheme is used as an http:// URL.
    :param send_platform_info: (Optional) boolean that indicates if the client
        library can send basic platform info (python version, OS) to the
        DeepL API. True = send info, False = only send client
        library version. None uses the default (True).
    :param verify_ssl: (Optional) Controls how requests verifies SSL
        certificates. This is passed to the underlying requests session, see
        the requests verify documentation for more information.
    :param max_retries: (Optional) Maximum number of times a failed request
        is retried, for failures that may be transient (e.g. HTTP 429).
        Default 5; 0 disables retries. None uses the default.
    :param timeout_s: (Optional) Minimum timeout in seconds for each attempt
        of a request. Default 10.0; None uses the default.
    :param headers: (Optional) Additional HTTP headers sent with every
        request to the DeepL API. A header replaces the library's header of
        the same name (compared case-insensitively), including User-Agent
        and Authorization; Content-Type, Content-Length, Transfer-Encoding,
        Host and an Accept the library sets for a call keep the library's
        value.
    :param app_info: (Optional) AppInfo identifying your application in the
        User-Agent header, same as set_app_info().

    All functions may raise DeepLException or a subclass if a connection error
    occurs.
    """

    _DEEPL_SERVER_URL_FREE = "https://api-free.deepl.com"

    def __init__(
        self,
        auth_key: str,
        *,
        server_url: Optional[str] = None,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: Optional[bool] = True,
        verify_ssl: Union[bool, str, None] = None,
        max_retries: Optional[int] = 5,
        timeout_s: Optional[float] = 10.0,
        headers: Optional[Dict[str, str]] = None,
        app_info: Optional[AppInfo] = None,
    ):
        if not auth_key or not auth_key.strip():
            raise ValueError("auth_key must not be empty")
        auth_key = auth_key.strip()

        if server_url is None:
            server_url = (
                self._DEEPL_SERVER_URL_FREE
                if util.is_free_account_auth_key(auth_key)
                else self._DEEPL_SERVER_URL
            )

        super().__init__(
            auth_key,
            server_url=server_url,
            proxy=proxy,
            send_platform_info=send_platform_info,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            timeout_s=timeout_s,
            headers=headers,
            app_info=app_info,
        )

    def _check_language_and_formality(
        self,
        source_lang: Union[str, Language, None],
        target_lang: Union[str, Language],
        formality: Union[str, Formality, None],
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_profile: Union[str, StyleProfile, None] = None,
        glossary_requires_source_lang: bool = False,
    ) -> dict:
        # target_lang and source_lang are case insensitive
        target_lang = str(target_lang).upper()
        if not target_lang:
            raise ValueError("target_lang must not be empty")
        if source_lang is not None:
            source_lang = str(source_lang).upper()
            if not source_lang:
                raise ValueError("source_lang must not be empty")

        if (
            glossary_requires_source_lang
            and glossary is not None
            and source_lang is None
        ):
            raise ValueError("source_lang is required if using a glossary")

        if glossary_ids is not None:
            if glossary is not None:
                raise ValueError(
                    "glossary_ids cannot be used together with the glossary "
                    "parameter"
                )
            if glossary_requires_source_lang and source_lang is None:
                raise ValueError(
                    "source_lang is required if using glossary_ids"
                )
            if len(glossary_ids) > 5:
                raise ValueError(
                    "glossary_ids must not contain more than 5 glossary IDs"
                )

        if isinstance(glossary, GlossaryInfo):
            target_lang_code = Language.remove_regional_variant(target_lang)
            if (
                target_lang_code != glossary.target_lang
                or source_lang not in (None, glossary.source_lang)
            ):
                raise ValueError(
                    "source_lang and target_lang must match glossary"
                )

        if isinstance(glossary, MultilingualGlossaryInfo):
            target_lang_code = Language.remove_regional_variant(target_lang)
            if not any(
                glossary_dict.target_lang == target_lang_code
                and source_lang in (None, glossary_dict.source_lang)
                for glossary_dict in glossary.dictionaries
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

        request_data: dict = {"target_lang": target_lang}
        if source_lang is not None:
            request_data["source_lang"] = source_lang
        if formality is not None:
            request_data["formality"] = str(formality).lower()
        if isinstance(glossary, GlossaryInfo) or isinstance(
            glossary, MultilingualGlossaryInfo
        ):
            request_data["glossary_id"] = _resource_id(
                glossary.glossary_id, "glossary"
            )
        elif glossary is not None:
            request_data["glossary_id"] = _resource_id(glossary, "glossary")
        if glossary_ids is not None:
            resolved_ids = [
                (
                    entry.glossary_id
                    if isinstance(
                        entry, (GlossaryInfo, MultilingualGlossaryInfo)
                    )
                    else entry
                )
                for entry in glossary_ids
            ]
            # The API expects glossary_ids as an array. For text translation
            # this is JSON-encoded as an array; for document translation
            # (form/multipart) translate_document_upload joins it into a
            # single comma-separated glossary_ids field.
            for resolved_id in resolved_ids:
                _resource_id(resolved_id, "glossary_ids entry")
            request_data["glossary_ids"] = resolved_ids
        if isinstance(style_rule, StyleRuleInfo):
            request_data["style_id"] = _resource_id(
                style_rule.style_id, "style_rule"
            )
        elif style_rule is not None:
            request_data["style_id"] = _resource_id(style_rule, "style_rule")
        if isinstance(style_profile, StyleProfile):
            request_data["style_profile_id"] = _resource_id(
                style_profile.style_profile_id, "style_profile"
            )
        elif style_profile is not None:
            request_data["style_profile_id"] = _resource_id(
                style_profile, "style_profile"
            )
        if isinstance(translation_memory, TranslationMemoryInfo):
            request_data["translation_memory_id"] = _resource_id(
                translation_memory.translation_memory_id, "translation_memory"
            )
        elif translation_memory is not None:
            request_data["translation_memory_id"] = _resource_id(
                translation_memory, "translation_memory"
            )
        if translation_memory_threshold is not None:
            if translation_memory is None:
                raise ValueError(
                    "translation_memory_threshold requires"
                    " translation_memory"
                )
            if not (0 <= translation_memory_threshold <= 100):
                raise ValueError(
                    "translation_memory_threshold must be between 0 and 100"
                )
            request_data["translation_memory_threshold"] = (
                translation_memory_threshold
            )
        return request_data

    def _create_glossary(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        entries_format: str,
        entries: Union[str, bytes],
    ) -> GlossaryInfo:
        # glossaries are only supported for base language types
        source_lang = Language.remove_regional_variant(source_lang)
        target_lang = Language.remove_regional_variant(target_lang)

        if not name:
            raise ValueError("glossary name must not be empty")

        request_data = {
            "name": name,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "entries_format": entries_format,
            "entries": entries,
        }

        status, content, json = self._api_call(
            "v2/glossaries", json=request_data, retry_only_unprocessed=True
        )
        self._raise_for_status(status, content, json)
        return GlossaryInfo.from_json(json)

    def translate_text(
        self,
        text: Union[str, Iterable[str]],
        source_lang: Union[str, Language, None] = None,
        target_lang: Union[str, Language, None] = None,
        *,
        context: Optional[str] = None,
        split_sentences: Union[str, SplitSentences, None] = None,
        preserve_formatting: Optional[bool] = None,
        formality: Union[str, Formality, None] = None,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        tag_handling: Union[str, TagHandlingMode, None] = None,
        tag_handling_version: Union[str, TagHandlingVersion, None] = None,
        outline_detection: Optional[bool] = None,
        non_splitting_tags: Union[str, List[str], None] = None,
        splitting_tags: Union[str, List[str], None] = None,
        ignore_tags: Union[str, List[str], None] = None,
        model_type: Union[str, ModelType, None] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        style_profile: Union[str, StyleProfile, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        custom_instructions: Optional[List[str]] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> Union[TextResult, List[TextResult]]:
        """Translate text(s) into the target language.

        :param text: Text to translate.
        :type text: UTF-8 :class:`str`; string sequence (list, tuple, iterator,
            generator)
        :param source_lang: (Optional) Language code of input text, for example
            "DE", "EN", "FR". If omitted or None, DeepL will auto-detect the
            input language. May be passed positionally after text.
        :param target_lang: Required. Language code to translate text into,
            for example "DE", "EN-US", "FR". May be passed positionally after
            source_lang.
        :param context: (Optional) Additional contextual text to influence
            translations, that is not translated itself. Characters in the
            `context` parameter are not counted toward billing. See the API
            documentation for more information and example usage.
        :param split_sentences: (Optional) Controls how the translation engine
            should split input into sentences before translation, see
            :class:`SplitSentences`.
        :param preserve_formatting: (Optional) Set to True to prevent the
            translation engine from correcting some formatting aspects, and
            instead leave the formatting unchanged.
        :param formality: (Optional) Desired formality for translation, as
            Formality enum, "less", "more", "prefer_less", "prefer_more", or
            "default".
        :param glossary: (Optional) glossary or glossary ID to use for
            translation. Must match target_lang, and source_lang if specified.
            If source_lang is omitted, DeepL uses the glossary dictionary for
            the detected source language.
        :param glossary_ids: (Optional) list of up to 5 glossaries or glossary
            IDs to use for translation, applied in order. Cannot be combined
            with the glossary parameter.
        :param style_rule: (Optional) style rule or style rule ID to use for
            translation.
        :param style_profile: (Optional) style profile or style profile ID to
            use for the translation.
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param tag_handling: (Optional) Type of tags to parse before
            translation, as TagHandlingMode enum, "xml" or "html".
        :param tag_handling_version: (Optional) Version of tag handling
            algorithm to use, as TagHandlingVersion enum, "v1" or "v2".
        :param outline_detection: (Optional) Set to False to disable automatic
            tag detection.
        :param non_splitting_tags: (Optional) XML tags that should not split a
            sentence.
        :type non_splitting_tags: List of XML tags or comma-separated-list of
            tags.
        :param splitting_tags: (Optional) XML tags that should split a
            sentence.
        :type splitting_tags: List of XML tags or comma-separated-list of tags.
        :param ignore_tags: (Optional) XML tags containing text that should not
            be translated.
        :type ignore_tags: List of XML tags or comma-separated-list of tags.
        :param model_type: (Optional) Controls whether the translation engine
            should use a potentially slower model to achieve higher quality.
        :param custom_instructions: (Optional) List of custom instructions to
            guide the translation. Maximum of 10 instructions, each with a
            maximum length of 300 characters.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: List of TextResult objects containing results, unless input
            text was one string, then a single TextResult object is returned.
        """
        if target_lang is None:
            raise TypeError(
                "translate_text() missing required argument: 'target_lang'"
            )
        if isinstance(text, str):
            if len(text) == 0:
                raise ValueError("text must not be empty")
            text = [text]
            multi_input = False
        else:
            multi_input = True
            text = list(text)
            if any(t == "" for t in text):
                raise ValueError("text must not be empty")
        text_count = len(text)

        request_data = self._check_language_and_formality(
            source_lang,
            target_lang,
            formality,
            glossary,
            style_rule,
            translation_memory,
            translation_memory_threshold,
            glossary_ids,
            style_profile=style_profile,
        )
        request_data["text"] = text

        # Always send show_billed_characters=true, remove when the API default
        # is changed to true
        request_data["show_billed_characters"] = True

        if context is not None:
            request_data["context"] = context
        if split_sentences is not None:
            request_data["split_sentences"] = str(split_sentences)
        if preserve_formatting is not None:
            request_data["preserve_formatting"] = bool(preserve_formatting)
        if tag_handling is not None:
            request_data["tag_handling"] = str(tag_handling)
        if tag_handling_version is not None:
            request_data["tag_handling_version"] = str(tag_handling_version)
        if outline_detection is not None:
            request_data["outline_detection"] = bool(outline_detection)
        if model_type is not None:
            request_data["model_type"] = str(model_type)

        def join_tags(tag_argument: Union[str, Iterable[str]]) -> List[str]:
            if isinstance(tag_argument, str):
                tag_argument = [tag_argument]
            return [
                tag
                for arg_string in tag_argument
                for tag in arg_string.split(",")
            ]

        if non_splitting_tags is not None:
            request_data["non_splitting_tags"] = join_tags(non_splitting_tags)
        if splitting_tags is not None:
            request_data["splitting_tags"] = join_tags(splitting_tags)
        if ignore_tags is not None:
            request_data["ignore_tags"] = join_tags(ignore_tags)
        if custom_instructions is not None:
            request_data["custom_instructions"] = custom_instructions

        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v2/translate", json=request_data
        )

        self._raise_for_status(status, content, json)

        translations = (
            json.get("translations", [])
            if (json and isinstance(json, dict))
            else []
        )
        output = []
        for translation in translations:
            text = translation.get("text", "") if translation else ""
            detected_source_language = (
                translation.get("detected_source_language", "")
                if translation
                else ""
            )
            billed_characters = util.get_int_safe(
                translation, "billed_characters"
            )
            model_type_used = translation.get("model_type_used")
            output.append(
                TextResult(
                    text,
                    detected_source_language,
                    billed_characters,
                    model_type_used,
                    translation.get("tag_handling_version"),
                )
            )

        if len(output) < text_count:
            raise DeepLException(
                f"Expected {text_count} translations in the response, "
                f"received {len(output)}"
            )

        return output if multi_input else output[0]

    def translate_document_from_filepath(
        self,
        input_path: Union[str, pathlib.PurePath],
        output_path: Union[str, pathlib.PurePath],
        source_lang: Union[str, Language, None] = None,
        target_lang: Union[str, Language, None] = None,
        *,
        formality: Union[str, Formality, None] = None,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        style_profile: Union[str, StyleProfile, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        enable_watermark: Optional[bool] = None,
        timeout_s: Optional[float] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentStatus:
        """Upload document at given input path, translate it into the target
        language, and download result to given output path.

        The upload request is only retried if it was not sent (HTTP 429 or a
        network failure while connecting, such as a DNS resolution failure, a
        refused connection, a connect timeout, or a reset or timeout in the TLS
        or proxy handshake): a retry after a server error, read timeout or lost
        connection could translate the document twice. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        :param input_path: Path to document to be translated.
        :param output_path: Path to store translated document.
        :param source_lang: (Optional) Language code of input document, for
            example "DE", "EN", "FR". If omitted, DeepL will auto-detect the
            input language.
        :param target_lang: Language code to translate document into, for
            example "DE", "EN-US", "FR".
        :param formality: (Optional) Desired formality for translation, as
            Formality enum, "less", "more", "prefer_less", or "prefer_more".
        :param glossary: (Optional) glossary or glossary ID to use for
            translation. Must match specified source_lang and target_lang.
        :param glossary_ids: (Optional) list of up to 5 glossaries or glossary
            IDs to use for translation, applied in order. Requires source_lang
            to be set and cannot be combined with the glossary parameter.
        :param style_rule: (Optional) style rule or style rule ID to use for
            translation.
        :param style_profile: (Optional) style profile or style profile ID to
            use for the translation.
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param enable_watermark: (Optional) Set to True to add a "Translated
            by DeepL" watermark to the translated document. Only supported for
            docx and pdf output; ignored by the API for other formats.
        :param timeout_s: (beta) (Optional) Maximum time to wait before
            the call raises an error. The status is polled every 5 seconds;
            the last wait is shortened so the call does not run past it.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: DocumentStatus when document translation completed, this
            allows the number of billed characters to be queried.

        :raises ValueError: If the input file does not exist, before any
            request is sent.
        :raises DocumentTranslationException: If an argument is invalid
            (TypeError or ValueError as the cause), the output file already
            exists, opening the input or output file fails, or an error occurs
            during upload, translation or download, or the translation fails.
            The exception includes the document handle if the document was
            already uploaded, otherwise the handle is None. An existing output
            file is never overwritten.
        """
        # Determine output_format from output path
        in_ext = pathlib.PurePath(input_path).suffix.lower()
        out_ext = pathlib.PurePath(output_path).suffix.lower()
        output_format = (
            None if in_ext == out_ext or not out_ext else out_ext[1:]
        )

        if not pathlib.Path(input_path).exists():
            raise ValueError(f"file does not exist: {input_path}")
        try:
            _check_target_lang_given(
                "translate_document_from_filepath", target_lang
            )
        except TypeError as e:
            raise _document_translation_exception(e, None) from e
        if pathlib.Path(output_path).exists():
            raise DocumentTranslationException(
                f"Output file already exists: {output_path}", None
            )

        try:
            in_file = open(input_path, "rb")
        except OSError as e:
            raise DocumentTranslationException(str(e), None) from e
        with in_file:
            try:
                # "x" fails if the file was created after the check above.
                out_file = open(output_path, "xb")
            except OSError as e:
                raise DocumentTranslationException(str(e), None) from e
            with out_file:
                try:
                    return self.translate_document(
                        in_file,
                        out_file,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        formality=formality,
                        glossary=glossary,
                        glossary_ids=glossary_ids,
                        style_rule=style_rule,
                        style_profile=style_profile,
                        translation_memory=translation_memory,
                        translation_memory_threshold=(
                            translation_memory_threshold
                        ),
                        output_format=output_format,
                        enable_watermark=enable_watermark,
                        timeout_s=timeout_s,
                        extra_body_parameters=extra_body_parameters,
                    )
                except Exception as e:
                    out_file.close()
                    os.unlink(output_path)
                    raise e

    def translate_document(
        self,
        input_document: Union[TextIO, BinaryIO, Any],
        output_document: Union[TextIO, BinaryIO, Any],
        source_lang: Union[str, Language, None] = None,
        target_lang: Union[str, Language, None] = None,
        *,
        formality: Union[str, Formality, None] = None,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        style_profile: Union[str, StyleProfile, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        filename: Optional[str] = None,
        output_format: Optional[str] = None,
        enable_watermark: Optional[bool] = None,
        timeout_s: Optional[float] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentStatus:
        """Upload document, translate it into the target language, and download
        result.

        The upload request is only retried if it was not sent (HTTP 429 or a
        network failure while connecting, such as a DNS resolution failure, a
        refused connection, a connect timeout, or a reset or timeout in the TLS
        or proxy handshake): a retry after a server error, read timeout or lost
        connection could translate the document twice. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        :param input_document: Document to translate as a file-like object. It
            is recommended to open files in binary mode.
        :param output_document: File-like object to receive translated
            document.
        :param source_lang: (Optional) Language code of input document, for
            example "DE", "EN", "FR". If omitted, DeepL will auto-detect the
            input language.
        :param target_lang: Language code to translate document into, for
            example "DE", "EN-US", "FR".
        :param formality: (Optional) Desired formality for translation, as
            Formality enum, "less", "more", "prefer_less", or "prefer_more".
        :param glossary: (Optional) glossary or glossary ID to use for
            translation. Must match specified source_lang and target_lang.
        :param glossary_ids: (Optional) list of up to 5 glossaries or glossary
            IDs to use for translation, applied in order. Requires source_lang
            to be set and cannot be combined with the glossary parameter.
        :param style_rule: (Optional) style rule or style rule ID to use for
            translation.
        :param style_profile: (Optional) style profile or style profile ID to
            use for the translation.
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param filename: (Optional) Filename including extension, sent with
            the upload instead of the file object's own name; the API detects
            the input format from its extension. Required if uploading string
            or bytes containing file content.
        :param output_format: (Optional) Desired output file extension, if
            it differs from the input file format.
        :param enable_watermark: (Optional) Set to True to add a "Translated
            by DeepL" watermark to the translated document. Only supported for
            docx and pdf output; ignored by the API for other formats.
        :param timeout_s: (beta) (Optional) Maximum time to wait before
            the call raises an error. The status is polled every 5 seconds;
            the last wait is shortened so the call does not run past it.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: DocumentStatus when document translation completed, this
            allows the number of billed characters to be queried.

        :raises DocumentTranslationException: If an argument is invalid
            (TypeError or ValueError as the cause), or an error occurs during
            upload, translation or download, or the translation fails. The
            exception includes the document handle if the document was
            already uploaded, otherwise the handle is None.
        """
        try:
            _check_target_lang_given("translate_document", target_lang)
            handle = self.translate_document_upload(
                input_document,
                target_lang=target_lang,
                source_lang=source_lang,
                formality=formality,
                glossary=glossary,
                glossary_ids=glossary_ids,
                style_rule=style_rule,
                style_profile=style_profile,
                translation_memory=translation_memory,
                translation_memory_threshold=translation_memory_threshold,
                filename=filename,
                output_format=output_format,
                enable_watermark=enable_watermark,
                extra_body_parameters=extra_body_parameters,
            )
        except Exception as e:
            raise _document_translation_exception(e, None) from e

        try:
            status = self.translate_document_wait_until_done(handle, timeout_s)
            self.translate_document_download(handle, output_document)
        except Exception as e:
            raise _document_translation_exception(e, handle) from e
        return status

    def translate_document_upload(
        self,
        input_document: Union[TextIO, BinaryIO, str, bytes, Any],
        source_lang: Union[str, Language, None] = None,
        target_lang: Union[str, Language, None] = None,
        *,
        formality: Union[str, Formality, None] = None,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        style_profile: Union[str, StyleProfile, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        filename: Optional[str] = None,
        output_format: Optional[str] = None,
        enable_watermark: Optional[bool] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentHandle:
        """Upload document to be translated and return handle associated with
        request.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could translate the document twice. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        :param input_document: Document to translate as a file-like object, or
            string or bytes containing file content.
        :param source_lang: (Optional) Language code of input document, for
            example "DE", "EN", "FR". If omitted, DeepL will auto-detect the
            input language.
        :param target_lang: Language code to translate document into, for
            example "DE", "EN-US", "FR".
        :param formality: (Optional) Desired formality for translation, as
            Formality enum, "less", "more", "prefer_less", or "prefer_more".
        :param glossary: (Optional) glossary or glossary ID to use for
            translation. Must match specified source_lang and target_lang.
        :param glossary_ids: (Optional) list of up to 5 glossaries or glossary
            IDs to use for translation, applied in order. Requires source_lang
            to be set and cannot be combined with the glossary parameter.
        :param style_rule: (Optional) style rule or style rule ID to use for
            translation.
        :param style_profile: (Optional) style profile or style profile ID to
            use for the translation.
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param filename: (Optional) Filename including extension, sent with
            the upload instead of the file object's own name; the API detects
            the input format from its extension. Required if uploading string
            or bytes containing file content.
        :param output_format: (Optional) Desired output file extension, if
            it differs from the input file format.
        :param enable_watermark: (Optional) Set to True to add a "Translated
            by DeepL" watermark to the translated document. Only supported for
            docx and pdf output; ignored by the API for other formats.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: DocumentHandle with ID and key identifying document.

        :raises DeepLException: If the upload fails, or the response does not
            contain the document ID and key.
        """
        target_lang = _check_target_lang_given(
            "translate_document_upload", target_lang
        )

        request_data = self._check_language_and_formality(
            source_lang,
            target_lang,
            formality,
            glossary,
            style_rule,
            translation_memory,
            translation_memory_threshold,
            glossary_ids=glossary_ids,
            style_profile=style_profile,
            glossary_requires_source_lang=True,
        )
        if output_format is not None:
            request_data["output_format"] = output_format
        if enable_watermark is not None:
            # Multipart form field: send "true"/"false", not Python's "True".
            request_data["enable_watermark"] = (
                "true" if enable_watermark else "false"
            )

        # The document endpoint uses multipart/form-data. Send glossary_ids as
        # a single comma-separated field (the form form of the array), matching
        # the other SDKs, instead of repeated multipart fields.
        if isinstance(request_data.get("glossary_ids"), list):
            request_data["glossary_ids"] = ",".join(
                request_data["glossary_ids"]
            )

        if filename is None and isinstance(input_document, (str, bytes)):
            raise ValueError(
                "filename is required if uploading file content as string "
                "or bytes"
            )
        files: Dict[str, Any] = {
            "file": (
                input_document
                if filename is None
                else (filename, input_document)
            )
        }
        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v2/document",
            data=request_data,
            files=files,
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)

        document_id = (
            json.get("document_id") if isinstance(json, dict) else None
        )
        document_key = (
            json.get("document_key") if isinstance(json, dict) else None
        )
        if not (
            isinstance(document_id, str)
            and document_id
            and isinstance(document_key, str)
            and document_key
        ):
            raise DeepLException(
                "Document upload response did not contain a document_id and "
                f"document_key, content: {content}"
            )
        return DocumentHandle(document_id, document_key)

    def translate_document_get_status(
        self, handle: DocumentHandle
    ) -> DocumentStatus:
        """Gets the status of the document translation request associated with
         given handle.

        :param handle: DocumentHandle to the request to check.
        :return: DocumentStatus containing the request status.

        :raises DocumentTranslationException: If an error occurs during
            querying the document, the exception includes the document handle.
        """

        data = {"document_key": handle.document_key}
        url = f"v2/document/{_quote_path(handle.document_id)}"

        status_code, content, json = self._api_call(url, json=data)

        self._raise_for_status(status_code, content, json)

        status = (
            json.get("status", None)
            if (json and isinstance(json, dict))
            else None
        )
        if not status:
            raise DocumentTranslationException(
                "Querying document status gave an empty response", handle
            )
        seconds_remaining = (
            json.get("seconds_remaining", None)
            if (json and isinstance(json, dict))
            else None
        )
        billed_characters = (
            json.get("billed_characters", None)
            if (json and isinstance(json, dict))
            else None
        )
        error_message = (
            json.get("error_message", None)
            if (json and isinstance(json, dict))
            else None
        )
        document_id = json.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            document_id = handle.document_id
        return DocumentStatus(
            status,
            seconds_remaining,
            billed_characters,
            error_message,
            document_id=document_id,
        )

    def translate_document_wait_until_done(
        self,
        handle: DocumentHandle,
        timeout_s: Optional[float] = None,
    ) -> DocumentStatus:
        """
        Continually polls the status of the document translation associated
        with the given handle, sleeping in between requests, and returns the
        final status when the translation completes successfully. An unknown
        status keeps polling, so pass timeout_s to bound the wait.
        :param handle: DocumentHandle to the document translation to wait on.
        :param timeout_s: (beta) (Optional) Maximum time to wait before
            the call raises an error. The status is polled every 5 seconds;
            the last wait is shortened so the call does not run past it.
        :return: DocumentStatus containing the status when done.

        :raises DeepLException: If the document translation fails, with the
            API's error message, or if timeout_s is exceeded.
        """
        deadline_s = None if timeout_s is None else time.time() + timeout_s
        status = self.translate_document_get_status(handle)
        while status.ok and not status.done:
            remaining_s = (
                None if deadline_s is None else deadline_s - time.time()
            )
            if remaining_s is not None and remaining_s <= 0:
                raise DeepLException(
                    f"Manual timeout of {timeout_s}s exceeded for"
                    + " document translation",
                    should_retry=False,
                )
            else:
                # seconds_remaining is unreliable, so poll every 5 seconds;
                # the last sleep is cut to the deadline.
                secs = 5.0 if remaining_s is None else min(5.0, remaining_s)
                util.log_info(
                    f"Rechecking document translation status "
                    f"after sleeping for {secs:.3f} seconds."
                )
                time.sleep(secs)
                status = self.translate_document_get_status(handle)
        if not status.ok:
            error_message = status.error_message or "unknown error"
            raise DeepLException(
                f"Error occurred while translating document: {error_message}",
                should_retry=False,
            )
        return status

    def translate_document_download(
        self,
        handle: DocumentHandle,
        output_file: Union[TextIO, BinaryIO, Any],
        chunk_size: int = _DOWNLOAD_CHUNK_SIZE,
    ) -> None:
        """Downloads the translated document for the request associated with
        given handle and writes it to the file-like object output_file.

        :param handle: DocumentHandle associated with request.
        :param output_file: File-like object to store downloaded document.
        :param chunk_size: (Optional) Size of chunk in bytes for streaming,
            default 64 KiB.

        :raises ConnectionException: If the connection fails while the
            document is downloaded into output_file.
        """

        data = {"document_key": handle.document_key}
        url = f"v2/document/{_quote_path(handle.document_id)}/result"

        status_code, response, json = self._api_call(
            url, json=data, stream=True
        )
        # TODO: once we drop py3.6 support, replace this with @overload
        # annotations in `_api_call` and chained private functions.
        # See for example https://stackoverflow.com/a/74070166/4926599
        # In addition, drop the type: ignore annotation on the
        # `import requests` / `from requests`
        assert isinstance(response, requests.Response)

        if not 200 <= status_code < 300:
            # The streamed body is not parsed by _api_call; read the error.
            content = _http_client.read_response_text(response)
            try:
                json = json_module.loads(content)
            except ValueError:
                json = None
            self._raise_for_status(
                status_code, content, json, downloading_document=True
            )

        # output_file is annotated to accept TextIO too; it receives bytes.
        output: Any = output_file
        chunks = _http_client.iter_response_content(response, chunk_size)
        for chunk in chunks:
            output.write(chunk)

    def get_source_languages(self) -> List[Language]:
        """Request the list of available source languages.

        :return: List of supported source languages.
        """
        status, content, json = self._api_call(
            "v3/languages",
            method="GET",
            params={"resource": "translate_text"},
        )
        self._raise_for_status(status, content, json)
        if not isinstance(json, list):
            raise DeepLException("Languages response is not a list")
        languages = json
        try:
            return [
                Language(
                    language["lang"].upper(),
                    _required_str(language, "name"),
                )
                for language in languages
                if language.get("usable_as_source")
            ]
        except (AttributeError, KeyError, TypeError) as e:
            raise DeepLException(
                f"Malformed language in response: {e!r}"
            ) from e

    def get_target_languages(self) -> List[Language]:
        """Request the list of available target languages.

        :return: List of supported target languages.
        """
        status, content, json = self._api_call(
            "v3/languages",
            method="GET",
            params={"resource": "translate_text"},
        )
        self._raise_for_status(status, content, json)
        if not isinstance(json, list):
            raise DeepLException("Languages response is not a list")
        languages = json
        try:
            return [
                Language(
                    language["lang"].upper(),
                    _required_str(language, "name"),
                    "formality" in (language.get("features") or {}),
                )
                for language in languages
                if language.get("usable_as_target")
            ]
        except (AttributeError, KeyError, TypeError) as e:
            raise DeepLException(
                f"Malformed language in response: {e!r}"
            ) from e

    def get_glossary_languages(self) -> List[GlossaryLanguagePair]:
        """Request the list of language pairs supported for glossaries.

        Note: the v3 API reports per-language usability rather than an
        explicit pair list, so pairs here are the cross product of
        usable_as_source x usable_as_target languages (excluding
        self-pairs). This assumes glossary support is a full symmetric
        cross product, which holds today (verified against production)
        but is not guaranteed by the API contract.
        """
        status, content, json = self._api_call(
            "v3/languages",
            method="GET",
            params={"resource": "glossary"},
        )

        self._raise_for_status(status, content, json)

        languages = json if (json and isinstance(json, list)) else []
        source_langs = [
            language["lang"]
            for language in languages
            if language.get("usable_as_source")
        ]
        target_langs = [
            language["lang"]
            for language in languages
            if language.get("usable_as_target")
        ]
        return [
            GlossaryLanguagePair(source_lang, target_lang)
            for source_lang in source_langs
            for target_lang in target_langs
            if source_lang != target_lang
        ]

    def get_usage(self) -> Usage:
        """Requests the current API usage."""
        status, content, json = self._api_call("v2/usage", method="GET")

        self._raise_for_status(status, content, json)

        if not isinstance(json, dict):
            raise DeepLException("Usage response is not a JSON object")
        return Usage(json)

    def create_glossary(
        self,
        name: str,
        source_lang: Union[str, Language],
        target_lang: Union[str, Language],
        entries: Dict[str, str],
    ) -> GlossaryInfo:
        """Creates a glossary with given name for the source and target
        languages, containing the entries in dictionary. The glossary may be
        used in the translate_text functions.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second glossary. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        Only certain language pairs are supported. The available language pairs
        can be queried using get_glossary_languages(). Glossaries are not
        regional specific: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function requires the glossary entries to be provided as a
        dictionary of source-target terms. To create a glossary from a CSV file
        downloaded from the DeepL website, see create_glossary_from_csv().

        :param name: user-defined name to attach to glossary.
        :param source_lang: Language of source terms.
        :param target_lang: Language of target terms.
        :param entries: dictionary of terms to insert in glossary, with the
            keys and values representing source and target terms respectively.
        :return: GlossaryInfo containing information about created glossary.

        :raises ValueError: If the glossary name is empty, or entries are
            empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
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
        """Creates a glossary with given name for the source and target
        languages, containing the entries in the given CSV data.
        The glossary may be used in the translate_text functions.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second glossary. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        Only certain language pairs are supported. The available language pairs
        can be queried using get_glossary_languages(). Glossaries are not
        regional specific: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function allows you to upload a glossary CSV file that you have
        downloaded from the DeepL website.

        Information about the expected CSV format can be found in the API
        documentation: https://www.deepl.com/docs-api/managing-glossaries/supported-glossary-formats/  # noqa

        :param name: user-defined name to attach to glossary.
        :param source_lang: Language of source terms.
        :param target_lang: Language of target terms.
        :param csv_data: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :return: GlossaryInfo containing information about created glossary.

        :raises ValueError: If the glossary name is empty.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """

        entries = (
            csv_data if isinstance(csv_data, (str, bytes)) else csv_data.read()
        )

        # The request body is JSON, which cannot carry bytes.
        if isinstance(entries, bytes):
            entries = entries.decode("utf-8")
        return self._create_glossary(
            name, source_lang, target_lang, "csv", entries
        )

    def get_glossary(self, glossary_id: str) -> GlossaryInfo:
        """Retrieves GlossaryInfo for the glossary with specified ID.

        :param glossary_id: ID of glossary to retrieve.
        :return: GlossaryInfo with information about specified glossary.
        :raises NotFoundException: If no glossary with given ID is
            found.
        """
        status, content, json = self._api_call(
            f"v2/glossaries/{glossary_id}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return GlossaryInfo.from_json(json)

    def list_glossaries(self) -> List[GlossaryInfo]:
        """Retrieves GlossaryInfo for all available glossaries.

        :return: list of GlossaryInfo for all available glossaries.
        """
        status, content, json = self._api_call("v2/glossaries", method="GET")
        self._raise_for_status(status, content, json)
        glossaries = (
            json.get("glossaries", [])
            if (json and isinstance(json, dict))
            else []
        )
        return [GlossaryInfo.from_json(glossary) for glossary in glossaries]

    def get_glossary_entries(self, glossary: Union[str, GlossaryInfo]) -> dict:
        """Retrieves the entries of the specified glossary and returns them as
        a dictionary.

        :param glossary: GlossaryInfo or ID of glossary to retrieve.
        :return: dictionary of glossary entries.
        :raises NotFoundException: If no glossary with given ID is
            found.
        :raises DeepLException: If the glossary could not be retrieved
            in the right format.
        """
        if isinstance(glossary, GlossaryInfo):
            glossary_id = glossary.glossary_id
        else:
            glossary_id = glossary

        status, content, json = self._api_call(
            f"v2/glossaries/{glossary_id}/entries",
            method="GET",
            headers={"Accept": "text/tab-separated-values"},
        )
        self._raise_for_status(status, content, json)
        if not isinstance(content, str):
            raise DeepLException(
                "Could not get the glossary content as a string",
                http_status_code=status,
            )
        return util.convert_tsv_to_dict(content)

    def delete_glossary(self, glossary: Union[str, GlossaryInfo]) -> None:
        """Deletes specified glossary.

        :param glossary: GlossaryInfo or ID of glossary to delete.
        :raises NotFoundException: If no glossary with given ID is
            found.
        """
        if isinstance(glossary, GlossaryInfo):
            glossary_id = glossary.glossary_id
        else:
            glossary_id = glossary

        status, content, json = self._api_call(
            f"v2/glossaries/{glossary_id}",
            method="DELETE",
        )
        self._raise_for_status(status, content, json)

    def rephrase_text(
        self,
        text: Union[str, Iterable[str]],
        *,
        target_lang: Union[None, str, Language] = None,
        tone: Union[str, WritingTone, None] = None,
        writing_style: Union[str, WritingStyle, None] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> Union[WriteResult, List[WriteResult]]:
        """Improve the text(s) and optionally convert them to the variant of
        the `target_lang` (requires source lang to match target_lang, excluding
        variants).

        :param text: Text to improve.
        :type text: UTF-8 :class:`str`; string sequence (list, tuple, iterator,
            generator)
        :param target_lang: language code the final text should be in, for
            example "DE", "EN-US", "FR".
        :param tone: Tone to be used for the improvement, as a WritingTone or
            string. Either writing_style OR tone can be used.
        :param writing_style: Writing style to be used for the improvement, as
            a WritingStyle or string. Either writing_style OR tone can be
            used.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: List of WriteResult objects containing results, unless input
            text was one string, then a single WriteResult object is returned.
        :raises ValueError: If a text or target_lang is empty.
        """
        if isinstance(text, str):
            if len(text) == 0:
                raise ValueError("text must not be empty")
            text = [text]
            multi_input = False
        else:
            multi_input = True
            text = list(text)
            if any(t == "" for t in text):
                raise ValueError("text must not be empty")

        if target_lang is not None and str(target_lang) == "":
            raise ValueError("target_lang must not be empty")

        request_data: dict = {"text": text}
        if target_lang is not None:
            request_data["target_lang"] = str(target_lang)
        if writing_style is not None:
            request_data["writing_style"] = str(writing_style)
        if tone is not None:
            request_data["tone"] = str(tone)
        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v2/write/rephrase", json=request_data
        )

        self._raise_for_status(status, content, json)

        output = _parse_improvements(json, len(text))
        return output if multi_input else output[0]

    def correct_text(
        self,
        text: Union[str, Iterable[str]],
        *,
        target_lang: Union[None, str, Language] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> Union[WriteResult, List[WriteResult]]:
        """Fix spelling and grammar errors in the text(s). Unlike
        `rephrase_text`, this applies a minimal-change correction pass and
        does not rewrite the text for style or tone.

        :param text: Text to correct.
        :type text: UTF-8 :class:`str`; string sequence (list, tuple, iterator,
            generator)
        :param target_lang: language code the final text should be in, for
            example "DE", "EN-US", "FR".
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: List of WriteResult objects containing results, unless input
            text was one string, then a single WriteResult object is returned.
        :raises ValueError: If a text or target_lang is empty.
        """

        if isinstance(text, str):
            if len(text) == 0:
                raise ValueError("text must not be empty")
            text = [text]
            multi_input = False
        else:
            multi_input = True
            text = list(text)
            if any(t == "" for t in text):
                raise ValueError("text must not be empty")

        if target_lang is not None and str(target_lang) == "":
            raise ValueError("target_lang must not be empty")

        request_data: dict = {"text": text}
        if target_lang is not None:
            request_data["target_lang"] = str(target_lang)
        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v2/write/correct", json=request_data
        )

        self._raise_for_status(status, content, json)

        output = _parse_improvements(json, len(text))
        return output if multi_input else output[0]

    def create_multilingual_glossary(
        self,
        name: str,
        dictionaries: List[MultilingualGlossaryDictionaryEntries],
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        """Creates a glossary with given name with all of the specified
        dictionaries, each with their own language pair and entries. The
        glossary may be used in the translate_text functions.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second glossary. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function requires the glossary entries for each dictionary to be
        provided as a dictionary of source-target terms. To create a glossary
        from a CSV file downloaded from the DeepL website, see
        create_multilingual_glossary_from_csv().

        :param name: user-defined name to attach to glossary.
        :param dictionaries: a list of MultilingualGlossaryDictionaryEntries
            which each contains entries for a particular language pair
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryInfo containing information about the
            created glossary.

        :raises ValueError: If the glossary name or dictionaries list is
            empty, or entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        if not dictionaries:
            raise ValueError("dictionaries must not be empty")
        if any(not self._has_entries(d) for d in dictionaries):
            raise ValueError("glossary entries must not be empty")

        return self._create_multilingual_glossary(
            name, dictionaries, extra_body_parameters
        )

    def create_multilingual_glossary_from_csv(
        self,
        name: str,
        source_lang: str,
        target_lang: str,
        csv: Union[TextIO, BinaryIO, str, bytes, Any],
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        """Creates a glossary with given name for the source and target
        languages, containing the entries in the given CSV data.
        The glossary may be used in the translate_text functions.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second glossary. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function allows you to upload a glossary CSV file that you have
        downloaded from the DeepL website.

        Information about the expected CSV format can be found in the API
        documentation: https://developers.deepl.com/docs/api-reference/glossaries#csv-comma-separated-values  # noqa

        :param name: user-defined name to attach to glossary.
        :param source_lang: Language of source entries.
        :param target_lang: Language of target entries.
        :param csv: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryInfo containing information about the
            created glossary.

        :raises ValueError: If the glossary name is empty, or entries are
            empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        entries = util.convert_csv_to_dict(csv)

        dictionaries = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        return self._create_multilingual_glossary(
            name, dictionaries, extra_body_parameters
        )

    def _create_multilingual_glossary(
        self,
        name: str,
        dictionaries: List[MultilingualGlossaryDictionaryEntries],
        extra_body_parameters: Optional[dict],
    ) -> MultilingualGlossaryInfo:
        if not name:
            raise ValueError("glossary name must not be empty")

        request_data: Dict[str, Any] = {
            "name": name,
            "dictionaries": self._dictionaries_json(dictionaries),
        }
        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v3/glossaries", json=request_data, retry_only_unprocessed=True
        )
        self._raise_for_status(status, content, json)
        return MultilingualGlossaryInfo.from_json(json)

    def update_multilingual_glossary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        *,
        name: Optional[str] = None,
        dictionaries: Optional[
            List[MultilingualGlossaryDictionaryEntries]
        ] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        """Updates a glossary: renames it and/or merges the given
        dictionaries into it. For each given dictionary, existing entries
        for its language pair are updated and new entries added; a language
        pair the glossary does not have yet is added as a new dictionary.

        Only the options that are set are sent.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to update.
        :param name: (Optional) New name of the glossary.
        :param dictionaries: (Optional) List of
            MultilingualGlossaryDictionaryEntries to merge into the glossary.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryInfo containing information about the
            updated glossary.
        :raises NotFoundException: If no glossary with given ID is
            found.
        """
        return self._update_multilingual_glossary(
            glossary,
            name=name,
            dictionaries=dictionaries,
            extra_body_parameters=extra_body_parameters,
        )

    def update_multilingual_glossary_name(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        name: str,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        """Updates the name of a glossary with the provided name.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to update.
        :param name: The new name of the glossary
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryInfo containing information about updated
            glossary.

        :raises ValueError: If the name is empty or invalid.
        :raises DeepLException: If the glossary cannot be found.
        """
        if not name:
            raise ValueError("glossary name must not be empty")

        return self._update_multilingual_glossary(
            glossary, name=name, extra_body_parameters=extra_body_parameters
        )

    def update_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        dictionary: MultilingualGlossaryDictionaryEntries,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        """Updates or creates a glossary dictionary with given glossary
        dictionary with its entries for the source and target languages.
        Either updates the glossary's entries if they exist for the
        given language pair, or adds any new ones to the dictionary if not.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function requires the glossary entries to be provided as a
        dictionary of source-target terms. To update a glossary from a CSV
        file, see update_multilingual_glossary_dictionary_from_csv().

        :param glossary: MultilingualGlossaryInfo or ID of glossary to update.
        :param dictionary: The new or updated glossary dictionary
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryInfo containing information about updated
            glossary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        if not self._has_entries(dictionary):
            raise ValueError("glossary entries must not be empty")

        return self._update_multilingual_glossary(
            glossary,
            dictionaries=[dictionary],
            extra_body_parameters=extra_body_parameters,
        )

    def update_multilingual_glossary_dictionary_from_csv(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        csv: Union[TextIO, BinaryIO, str, bytes, Any],
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        """Updates or creates a glossary dictionary with given entries in
        CSV formatting for the source and target languages. Either updates
        entries if they exist for the given language pair, or adds new ones
        to the dictionary if not.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function allows you to upload a glossary CSV file that you have
        downloaded from the DeepL website.

        Information about the expected CSV format can be found in the API
        documentation: https://www.deepl.com/docs-api/managing-glossaries/supported-glossary-formats/  # noqa

        :param glossary: MultilingualGlossaryInfo or ID of glossary to update.
        :param source_lang: Language of source entries.
        :param target_lang: Language of target entries.
        :param csv: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryInfo containing information about updated
            glossary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        entries = util.convert_csv_to_dict(csv)
        if not entries:
            raise ValueError("glossary entries must not be empty")

        dictionaries = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        return self._update_multilingual_glossary(
            glossary,
            dictionaries=dictionaries,
            extra_body_parameters=extra_body_parameters,
        )

    def _update_multilingual_glossary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        *,
        name: Optional[str] = None,
        dictionaries: Optional[
            List[MultilingualGlossaryDictionaryEntries]
        ] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryInfo:
        glossary_id = self._multilingual_glossary_id(glossary)

        request_data: Dict[str, Any] = {}
        if name is not None:
            request_data["name"] = name
        if dictionaries is not None:
            request_data["dictionaries"] = self._dictionaries_json(
                dictionaries
            )
        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}", method="PATCH", json=request_data
        )
        self._raise_for_status(status, content, json)

        return MultilingualGlossaryInfo.from_json(json)

    def replace_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        dictionary: MultilingualGlossaryDictionaryEntries,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryDictionaryInfo:
        """Replaces a glossary dictionary with given entries for the
        source and target languages.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function requires the glossary entries to be provided as a
        dictionary of source-target terms. To replace a dictionary from a CSV
        file, see replace_multilingual_glossary_dictionary_from_csv().

        :param glossary: MultilingualGlossaryInfo or ID of glossary to update.
        :param dictionary: The new glossary dictionary
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryDictionaryInfo containing information
            about the updated dictionary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        if not self._has_entries(dictionary):
            raise ValueError("glossary entries must not be empty")

        return self._replace_multilingual_glossary_dictionary(
            glossary,
            dictionary.source_lang,
            dictionary.target_lang,
            dictionary.entries,
            extra_body_parameters,
        )

    def replace_multilingual_glossary_dictionary_from_csv(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        csv: Union[TextIO, BinaryIO, str, bytes, Any],
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> MultilingualGlossaryDictionaryInfo:
        """Replaces a glossary dictionary with given CSV formatted entries
        for the source and target languages.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function allows you to upload a glossary CSV file that you have
        downloaded from the DeepL website.

        Information about the expected CSV format can be found in the API
        documentation: https://www.deepl.com/docs-api/managing-glossaries/supported-glossary-formats/  # noqa

        :param glossary: MultilingualGlossaryInfo or ID of glossary to update.
        :param source_lang: Language of source entries.
        :param target_lang: Language of target entries.
        :param csv: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace fields with the same key.
        :return: MultilingualGlossaryDictionaryInfo containing information
            about updated dictionary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        entries = util.convert_csv_to_dict(csv)
        if not entries:
            raise ValueError("glossary entries must not be empty")

        return self._replace_multilingual_glossary_dictionary(
            glossary, source_lang, target_lang, entries, extra_body_parameters
        )

    def _replace_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        entries: Dict[str, str],
        extra_body_parameters: Optional[dict],
    ) -> MultilingualGlossaryDictionaryInfo:
        glossary_id = self._multilingual_glossary_id(glossary)

        request_data: Dict[str, Any] = self._dictionary_json(
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        )
        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}/dictionaries",
            method="PUT",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return MultilingualGlossaryDictionaryInfo.from_json(json)

    def get_multilingual_glossary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
    ) -> MultilingualGlossaryInfo:
        """Retrieves MultilingualGlossaryInfo for the specified glossary.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to
            retrieve.
        :return: MultilingualGlossaryInfo with information about specified
            glossary.
        :raises NotFoundException: If no glossary with given ID is
            found.
        """
        status, content, json = self._api_call(
            f"v3/glossaries/{self._multilingual_glossary_id(glossary)}",
            method="GET",
        )
        self._raise_for_status(status, content, json)
        return MultilingualGlossaryInfo.from_json(json)

    def list_multilingual_glossaries(self) -> List[MultilingualGlossaryInfo]:
        """Retrieves a list of MultilingualGlossaryInfo for all available
        glossaries.

        :return: list of MultilingualGlossaryInfos for all available
            glossaries.
        """
        status, content, json = self._api_call("v3/glossaries", method="GET")
        self._raise_for_status(status, content, json)
        glossaries = (
            json.get("glossaries", [])
            if (json and isinstance(json, dict))
            else []
        )
        return [
            MultilingualGlossaryInfo.from_json(glossary)
            for glossary in glossaries
        ]

    def get_multilingual_glossary_dictionary_entries(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
    ) -> MultilingualGlossaryDictionaryEntries:
        """Retrieves the entries of the dictionary for the given source and
        target language in the specified glossary.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to
            retrieve.
        :param source_lang: Language of source terms.
        :param target_lang: Language of target terms.
        :return: MultilingualGlossaryDictionaryEntries whose entries are a
            dictionary of source-target terms.
        :raises NotFoundException: If the glossary or the dictionary
            is not found.
        """
        glossary_id = self._multilingual_glossary_id(glossary)
        query = self._language_pair_query(source_lang, target_lang)

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}/entries?{query}",
            method="GET",
        )
        self._raise_for_status(status, content, json)
        try:
            dictionaries = list(json["dictionaries"])
        except (KeyError, TypeError) as error:
            raise _malformed_response(
                "MultilingualGlossaryDictionaryEntries", error
            ) from error
        if not dictionaries:
            raise NotFoundException(
                "Not found, message: no dictionary for "
                f"{source_lang}->{target_lang}"
            )
        return MultilingualGlossaryDictionaryEntries.from_json(dictionaries[0])

    def delete_multilingual_glossary(
        self, glossary: Union[str, MultilingualGlossaryInfo]
    ) -> None:
        """Deletes specified glossary.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to delete.
        :raises NotFoundException: If no glossary with given ID is
            found.
        """
        status, content, json = self._api_call(
            f"v3/glossaries/{self._multilingual_glossary_id(glossary)}",
            method="DELETE",
        )
        self._raise_for_status(status, content, json)

    def delete_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        *,
        dictionary: Optional[MultilingualGlossaryDictionaryInfo] = None,
    ) -> None:
        """Deletes the dictionary for the given language pair from the
        specified glossary.

        :param glossary: MultilingualGlossaryInfo or ID of glossary
            containing the dictionary to delete.
        :param source_lang: Source language of the dictionary.
        :param target_lang: Target language of the dictionary.
        :param dictionary: (Optional, keyword-only) The
            MultilingualGlossaryDictionaryInfo to delete, instead of
            source_lang and target_lang. If given, it takes precedence over
            source_lang and target_lang.
        :raises NotFoundException: If no glossary with given ID is
            found.
        :raises ValueError: If neither the dictionary nor both source_lang and
            target_lang were provided.
        """
        glossary_id = self._multilingual_glossary_id(glossary)

        if not dictionary and not (source_lang and target_lang):
            raise ValueError(
                "must provide dictionary or both source_lang and target_lang"
            )

        if dictionary:
            source_lang = dictionary.source_lang
            target_lang = dictionary.target_lang

        query = self._language_pair_query(
            source_lang, target_lang  # type: ignore[arg-type]
        )
        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}/dictionaries?{query}",
            method="DELETE",
        )
        self._raise_for_status(status, content, json)

    @staticmethod
    def _multilingual_glossary_id(
        glossary: Union[str, MultilingualGlossaryInfo],
    ) -> str:
        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id
        if not glossary:
            raise ValueError("glossary id must not be empty")
        return urllib.parse.quote(glossary, safe="")

    @staticmethod
    def _language_pair_query(source_lang: str, target_lang: str) -> str:
        _check_language("source_lang", source_lang)
        _check_language("target_lang", target_lang)
        # glossaries are only supported for base language types
        return util.encode_query(
            {
                "source_lang": Language.remove_regional_variant(source_lang),
                "target_lang": Language.remove_regional_variant(target_lang),
            }
        )

    @staticmethod
    def _has_entries(
        dictionary: MultilingualGlossaryDictionaryEntries,
    ) -> bool:
        entries = dictionary.entries
        if isinstance(entries, str):
            # Empty lines are skipped when parsing, so "\n" holds no entries.
            entries = util.convert_tsv_to_dict(entries)
        return bool(entries)

    @staticmethod
    def _dictionary_json(
        dictionary: MultilingualGlossaryDictionaryEntries,
    ) -> Dict[str, Any]:
        _check_language("source_lang", dictionary.source_lang)
        _check_language("target_lang", dictionary.target_lang)
        entries: Union[Dict[str, str], str] = dictionary.entries
        if isinstance(entries, str):
            # Trimmed and validated like a dict.
            entries = util.convert_tsv_to_dict(entries)
        # glossaries are only supported for base language types
        return {
            "source_lang": Language.remove_regional_variant(
                dictionary.source_lang
            ),
            "target_lang": Language.remove_regional_variant(
                dictionary.target_lang
            ),
            "entries": util.convert_dict_to_tsv(entries),
            "entries_format": "tsv",
        }

    @classmethod
    def _dictionaries_json(
        cls, dictionaries: List[MultilingualGlossaryDictionaryEntries]
    ) -> List[Dict[str, Any]]:
        return [cls._dictionary_json(d) for d in dictionaries]

    def create_spoken_terms(
        self,
        name: str,
        term_lists: List[SpokenTermsEntries],
        *,
        extra_body_parameters: Optional[Dict[str, Any]] = None,
    ) -> SpokenTerms:
        """Creates a spoken-terms collection with the given name and term
        lists, one per language. Spoken terms improve the transcription of
        the given terms.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second collection. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        :param name: User-defined name to attach to the collection.
        :param term_lists: List of SpokenTermsEntries, each containing the
            terms of one language.
        :param extra_body_parameters: (Optional) Additional key/value pairs
            to send in the JSON request body; they replace fields the library
            sets with the same key.
        :return: SpokenTerms containing information about the created
            collection.
        :raises ValueError: If a term, after stripping leading and trailing
            whitespace, is empty or contains a control character, as
            validate_glossary_term() checks.
        """
        request_data: Dict[str, Any] = {
            "name": name,
            "term_lists": [
                self._spoken_terms_json(entries) for entries in term_lists
            ],
        }
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            "v3/spoken-terms", json=request_data, retry_only_unprocessed=True
        )
        self._raise_for_status(status, content, json)
        return self._parse_spoken_terms_response(SpokenTerms.from_json, json)

    def list_spoken_terms(self) -> List[SpokenTerms]:
        """Retrieves all spoken-terms collections.

        :return: List of SpokenTerms for all collections.
        """
        status, content, json = self._api_call("v3/spoken-terms", method="GET")
        self._raise_for_status(status, content, json)
        spoken_terms = (
            json.get("spoken_terms", [])
            if (json and isinstance(json, dict))
            else []
        )
        return self._parse_spoken_terms_response(
            lambda items: [SpokenTerms.from_json(item) for item in items],
            spoken_terms,
        )

    def get_spoken_terms(
        self, spoken_terms: Union[str, SpokenTerms]
    ) -> SpokenTerms:
        """Retrieves a spoken-terms collection.

        :param spoken_terms: SpokenTerms or ID of the collection.
        :return: SpokenTerms with information about the collection.
        :raises DeepLException: If no collection with the given ID is found.
        """
        spoken_terms_id = self._spoken_terms_id(spoken_terms)
        status, content, json = self._api_call(
            f"v3/spoken-terms/{spoken_terms_id}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return self._parse_spoken_terms_response(SpokenTerms.from_json, json)

    def update_spoken_terms(
        self,
        spoken_terms: Union[str, SpokenTerms],
        *,
        name: Optional[str] = None,
        term_lists: Optional[List[SpokenTermsEntries]] = None,
        extra_body_parameters: Optional[Dict[str, Any]] = None,
    ) -> SpokenTerms:
        """Updates a spoken-terms collection: renames it and/or merges the
        given terms into the existing term list of each given language.

        :param spoken_terms: SpokenTerms or ID of the collection.
        :param name: (Optional) New name of the collection.
        :param term_lists: (Optional) List of SpokenTermsEntries whose terms
            are merged into the term list of the same language.
        :param extra_body_parameters: (Optional) Additional key/value pairs
            to send in the JSON request body; they replace fields the library
            sets with the same key.
        :return: SpokenTerms containing information about the updated
            collection.
        :raises ValueError: If a term, after stripping leading and trailing
            whitespace, is empty or contains a control character, as
            validate_glossary_term() checks.
        """
        spoken_terms_id = self._spoken_terms_id(spoken_terms)
        request_data: Dict[str, Any] = {}
        if name is not None:
            request_data["name"] = name
        if term_lists is not None:
            request_data["term_lists"] = [
                self._spoken_terms_json(entries) for entries in term_lists
            ]
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            f"v3/spoken-terms/{spoken_terms_id}",
            method="PATCH",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return self._parse_spoken_terms_response(SpokenTerms.from_json, json)

    def get_spoken_terms_entries(
        self, spoken_terms: Union[str, SpokenTerms], lang: str
    ) -> SpokenTermsEntries:
        """Retrieves the terms of one language in a spoken-terms collection.

        :param spoken_terms: SpokenTerms or ID of the collection.
        :param lang: Language of the term list, e.g. "en".
        :return: SpokenTermsEntries containing the terms.
        """
        spoken_terms_id = self._spoken_terms_id(spoken_terms)
        _check_language("lang", lang)
        query = util.encode_query({"lang": lang})
        status, content, json = self._api_call(
            f"v3/spoken-terms/{spoken_terms_id}/entries?{query}",
            method="GET",
        )
        self._raise_for_status(status, content, json)
        return self._parse_spoken_terms_response(
            SpokenTermsEntries.from_json, json
        )

    def replace_spoken_terms_list(
        self,
        spoken_terms: Union[str, SpokenTerms],
        entries: SpokenTermsEntries,
        *,
        extra_body_parameters: Optional[Dict[str, Any]] = None,
    ) -> SpokenTermsList:
        """Replaces the term list of one language in a spoken-terms
        collection, or adds it if the collection has no list for the
        language.

        :param spoken_terms: SpokenTerms or ID of the collection.
        :param entries: SpokenTermsEntries with the language and its terms.
        :param extra_body_parameters: (Optional) Additional key/value pairs
            to send in the JSON request body; they replace fields the library
            sets with the same key.
        :return: SpokenTermsList containing information about the term list.
        :raises ValueError: If a term, after stripping leading and trailing
            whitespace, is empty or contains a control character, as
            validate_glossary_term() checks.
        """
        spoken_terms_id = self._spoken_terms_id(spoken_terms)
        request_data = self._spoken_terms_json(entries)
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            f"v3/spoken-terms/{spoken_terms_id}/term-lists",
            method="PUT",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return self._parse_spoken_terms_response(
            SpokenTermsList.from_json, json
        )

    def delete_spoken_terms(
        self, spoken_terms: Union[str, SpokenTerms]
    ) -> None:
        """Deletes a spoken-terms collection.

        :param spoken_terms: SpokenTerms or ID of the collection.
        """
        spoken_terms_id = self._spoken_terms_id(spoken_terms)
        status, content, json = self._api_call(
            f"v3/spoken-terms/{spoken_terms_id}", method="DELETE"
        )
        self._raise_for_status(status, content, json)

    def delete_spoken_terms_list(
        self, spoken_terms: Union[str, SpokenTerms], lang: str
    ) -> None:
        """Deletes the term list of one language from a spoken-terms
        collection.

        :param spoken_terms: SpokenTerms or ID of the collection.
        :param lang: Language of the term list to delete, e.g. "de".
        """
        spoken_terms_id = self._spoken_terms_id(spoken_terms)
        _check_language("lang", lang)
        query = util.encode_query({"lang": lang})
        status, content, json = self._api_call(
            f"v3/spoken-terms/{spoken_terms_id}/term-lists?{query}",
            method="DELETE",
        )
        self._raise_for_status(status, content, json)

    @staticmethod
    def _parse_spoken_terms_response(
        parse: Callable[[Any], _T], json: Any
    ) -> _T:
        try:
            return parse(json)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise DeepLException(
                f"Malformed spoken-terms response: {e!r}"
            ) from e

    @staticmethod
    def _spoken_terms_json(entries: SpokenTermsEntries) -> dict:
        _check_language("lang", entries.lang)
        # Terms are sent newline-separated: a term with a newline would
        # silently become several terms.
        terms = [term.strip() for term in entries.entries]
        for term in terms:
            util.validate_glossary_term(term)
        return SpokenTermsEntries(entries.lang, terms).to_json()

    @staticmethod
    def _spoken_terms_id(spoken_terms: Union[str, SpokenTerms]) -> str:
        if isinstance(spoken_terms, SpokenTerms):
            spoken_terms = spoken_terms.spoken_terms_id
        if not spoken_terms:
            raise ValueError("spoken_terms must not be empty")
        return urllib.parse.quote(spoken_terms, safe="")

    def get_languages_for_resource(
        self,
        resource: Union[str, LanguageResourceName],
        *,
        include: Optional[Iterable[Union[str, LanguageInclude]]] = None,
    ) -> List[LanguageSupport]:
        """Retrieves the languages supported by the given resource, each
        with its per-feature support information.

        :param resource: Resource to query, for example
            LanguageResourceName.TRANSLATE_TEXT or "translate_text".
        :param include: (Optional) Values to also include beta languages and
            features (LanguageInclude.BETA) or third-party-backed features
            (LanguageInclude.EXTERNAL). By default only stable languages and
            features are returned.
        :return: List of LanguageSupport objects.
        """
        resource = str(resource)
        if len(resource) == 0:
            raise ValueError("resource must not be empty")

        params = [("resource", resource)]
        if include is not None:
            params.extend(("include", str(value)) for value in include)

        endpoint = f"v3/languages?{util.encode_query(params)}"
        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)

        if not isinstance(json, list):
            raise DeepLException("Languages response is not a list")
        languages = json
        try:
            return [LanguageSupport.from_json(lang) for lang in languages]
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise DeepLException(
                f"Malformed language in response: {e!r}"
            ) from e

    def get_language_resources(self) -> List[LanguageResource]:
        """Retrieves the resources supported by the DeepL API, along with
        their features and whether each feature requires support from the
        source and/or target language.

        :return: List of LanguageResource objects, one per resource.
        """
        status, content, json = self._api_call(
            "v3/languages/resources", method="GET"
        )
        self._raise_for_status(status, content, json)
        if not isinstance(json, list):
            raise DeepLException("Language resources response is not a list")
        resources = json
        try:
            return [LanguageResource.from_json(r) for r in resources]
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise DeepLException(
                f"Malformed language resource in response: {e!r}"
            ) from e

    def get_all_style_rules(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        detailed: Optional[bool] = None,
    ) -> List[StyleRuleInfo]:
        """Retrieves a list of StyleRuleInfo for all available style rules.

        :param page: Page number for pagination, 0-indexed (optional).
        :param page_size: Number of items per page (optional).
        :param detailed: Whether to include detailed configuration rules
            (optional).
        :return: List of StyleRuleInfo objects for all available style rules.
        """
        params = {}
        if page is not None:
            params["page"] = str(page)
        if page_size is not None:
            params["page_size"] = str(page_size)
        if detailed is not None:
            params["detailed"] = str(detailed).lower()

        endpoint = "v3/style_rules"
        if params:
            query_string = util.encode_query(params)
            endpoint += f"?{query_string}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)

        style_rules = (
            json.get("style_rules", [])
            if (json and isinstance(json, dict))
            else []
        )
        return self._parse_style_rule_response(
            lambda rules: [StyleRuleInfo.from_json(rule) for rule in rules],
            style_rules,
        )

    def create_style_rule(
        self,
        name: str,
        language: str,
        configured_rules: Optional[dict] = None,
        custom_instructions: Optional[List[dict]] = None,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> StyleRuleInfo:
        """Creates a new style rule.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second style rule. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        :param name: Name for the style rule.
        :param language: Language code for the style rule.
        :param configured_rules: Optional dict of configured rules.
        :param custom_instructions: Optional list of custom instruction dicts.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: StyleRuleInfo for the created style rule.
        """
        if not name:
            raise ValueError("name must not be empty")
        if not language:
            raise ValueError("language must not be empty")

        request_data: Dict[str, Any] = {"name": name, "language": language}
        if configured_rules is not None:
            request_data["configured_rules"] = configured_rules
        if custom_instructions is not None:
            for instruction in custom_instructions:
                _check_language(
                    "source_language", instruction.get("source_language")
                )
            request_data["custom_instructions"] = custom_instructions

        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            "v3/style_rules",
            json=request_data,
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(StyleRuleInfo.from_json, json)

    def get_style_rule(
        self,
        style_rule: Union[str, StyleRuleInfo],
    ) -> StyleRuleInfo:
        """Retrieves a single style rule by ID.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :return: StyleRuleInfo for the requested style rule.
        """
        style_id = self._style_rule_id(style_rule)
        status, content, json = self._api_call(
            f"v3/style_rules/{style_id}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(StyleRuleInfo.from_json, json)

    def update_style_rule_name(
        self,
        style_rule: Union[str, StyleRuleInfo],
        name: str,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> StyleRuleInfo:
        """Updates the name of a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param name: New name for the style rule.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: Updated StyleRuleInfo.
        """
        style_id = self._style_rule_id(style_rule)
        if not name:
            raise ValueError("name must not be empty")
        request_data = {"name": name}
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            f"v3/style_rules/{style_id}",
            method="PATCH",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(StyleRuleInfo.from_json, json)

    def delete_style_rule(
        self,
        style_rule: Union[str, StyleRuleInfo],
    ) -> None:
        """Deletes a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        """
        style_id = self._style_rule_id(style_rule)
        status, content, json = self._api_call(
            f"v3/style_rules/{style_id}", method="DELETE"
        )
        self._raise_for_status(status, content, json)

    def update_style_rule_configured_rules(
        self,
        style_rule: Union[str, StyleRuleInfo],
        configured_rules: dict,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> StyleRuleInfo:
        """Updates the configured rules of a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param configured_rules: Dict of configured rules to set.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: Updated StyleRuleInfo.
        """
        style_id = self._style_rule_id(style_rule)
        # Copy so the caller's configured_rules dict is not modified.
        request_data = dict(configured_rules)
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            f"v3/style_rules/{style_id}/configured_rules",
            method="PUT",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(StyleRuleInfo.from_json, json)

    def create_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> CustomInstruction:
        """Creates a custom instruction for a style rule.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second custom instruction. The raised
        exception has should_retry True only after those failures or a response
        body cut off mid-read.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param label: Label for the custom instruction.
        :param prompt: Prompt text for the custom instruction.
        :param source_language: Optional source language code.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: Created CustomInstruction.
        """
        style_id = self._style_rule_id(style_rule)
        if not label:
            raise ValueError("label must not be empty")
        if not prompt:
            raise ValueError("prompt must not be empty")
        _check_language("source_language", source_language)
        request_data = {"label": label, "prompt": prompt}
        if source_language is not None:
            request_data["source_language"] = source_language
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            f"v3/style_rules/{style_id}/custom_instructions",
            json=request_data,
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(
            CustomInstruction.from_json, json
        )

    def get_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: Union[str, CustomInstruction],
    ) -> CustomInstruction:
        """Retrieves a custom instruction by ID.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param instruction_id: ID of the custom instruction, or a
            CustomInstruction object.
        :return: CustomInstruction.
        """
        style_id = self._style_rule_id(style_rule)
        instruction = self._custom_instruction_id(instruction_id)
        url = f"v3/style_rules/{style_id}/custom_instructions/{instruction}"
        status, content, json = self._api_call(
            url,
            method="GET",
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(
            CustomInstruction.from_json, json
        )

    def update_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: Union[str, CustomInstruction],
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> CustomInstruction:
        """Updates a custom instruction.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param instruction_id: ID of the custom instruction, or a
            CustomInstruction object.
        :param label: New label for the custom instruction.
        :param prompt: New prompt text for the custom instruction.
        :param source_language: Optional source language code.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: Updated CustomInstruction.
        """
        style_id = self._style_rule_id(style_rule)
        instruction = self._custom_instruction_id(instruction_id)
        if not label:
            raise ValueError("label must not be empty")
        if not prompt:
            raise ValueError("prompt must not be empty")
        _check_language("source_language", source_language)
        request_data = {"label": label, "prompt": prompt}
        if source_language is not None:
            request_data["source_language"] = source_language
        url = f"v3/style_rules/{style_id}/custom_instructions/{instruction}"
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            url,
            method="PUT",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return self._parse_style_rule_response(
            CustomInstruction.from_json, json
        )

    def delete_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: Union[str, CustomInstruction],
    ) -> None:
        """Deletes a custom instruction from a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param instruction_id: ID of the custom instruction to delete, or a
            CustomInstruction object.
        """
        style_id = self._style_rule_id(style_rule)
        instruction = self._custom_instruction_id(instruction_id)
        url = f"v3/style_rules/{style_id}/custom_instructions/{instruction}"
        status, content, json = self._api_call(
            url,
            method="DELETE",
        )
        self._raise_for_status(status, content, json)

    def list_style_profiles(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[StyleProfile]:
        """Retrieves a page of style profiles.

        :param page: Page number for pagination, 0-indexed (optional, the API
            default is 0).
        :param page_size: Number of items per page (optional, the API default
            is 10; values above 100 are reduced to 100).
        :return: List of StyleProfile objects on the requested page.
        """
        params = {}
        if page is not None:
            params["page"] = str(page)
        if page_size is not None:
            params["page_size"] = str(page_size)

        endpoint = "v3/style_profiles"
        if params:
            endpoint += f"?{util.encode_query(params)}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)

        if not isinstance(json, dict):
            raise DeepLException(
                "Style profile list response is not a JSON object"
            )
        style_profiles = json.get("style_profiles") or []
        if not isinstance(style_profiles, list):
            raise DeepLException(
                "Style profile list response has a malformed style_profiles"
            )
        # from_json raises DeepLException for a malformed entry.
        return [StyleProfile.from_json(p) for p in style_profiles]

    def create_style_profile(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        industry: Optional[str] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule_ids: Optional[List[Union[str, StyleRuleInfo]]] = None,
        translation_memory_ids: Optional[
            List[Union[str, TranslationMemoryInfo]]
        ] = None,
        glossary_priority_order_enabled: Optional[bool] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> StyleProfile:
        """Creates a style profile. Only the name is required; if any of the
        component IDs cannot be used, the request fails and no style profile
        is created.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second style profile. The raised exception
        has should_retry True only after those failures or a response body cut
        off mid-read.

        :param name: Name for the style profile.
        :param description: (Optional) Free-text description.
        :param industry: (Optional) Industry the style profile is written for.
        :param glossary_ids: (Optional) Glossaries to link, highest priority
            first, as IDs or GlossaryInfo / MultilingualGlossaryInfo objects.
        :param style_rule_ids: (Optional) Style rule lists to link, as IDs or
            StyleRuleInfo objects.
        :param translation_memory_ids: (Optional) Translation memories to
            link, as IDs or TranslationMemoryInfo objects.
        :param glossary_priority_order_enabled: (Optional) Whether the order
            of glossary_ids decides which glossary wins when glossaries
            overlap.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: StyleProfile for the created style profile.
        """
        request_data = self._style_profile_json(
            name=name,
            description=description,
            industry=industry,
            glossary_ids=glossary_ids,
            style_rule_ids=style_rule_ids,
            translation_memory_ids=translation_memory_ids,
            glossary_priority_order_enabled=glossary_priority_order_enabled,
            extra_body_parameters=extra_body_parameters,
        )
        status, content, json = self._api_call(
            "v3/style_profiles",
            json=request_data,
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)
        return StyleProfile.from_json(json)

    def get_style_profile(
        self,
        style_profile: Union[str, StyleProfile],
    ) -> StyleProfile:
        """Retrieves a single style profile by ID.

        :param style_profile: Style profile ID string or StyleProfile object.
        :return: StyleProfile for the requested style profile.
        :raises DeepLException: With http_status_code 404 if no style profile
            with the given ID is found.
        """
        style_profile_id = self._style_profile_id(style_profile)
        status, content, json = self._api_call(
            f"v3/style_profiles/{style_profile_id}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return StyleProfile.from_json(json)

    def update_style_profile(
        self,
        style_profile: Union[str, StyleProfile],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        industry: Optional[str] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule_ids: Optional[List[Union[str, StyleRuleInfo]]] = None,
        translation_memory_ids: Optional[
            List[Union[str, TranslationMemoryInfo]]
        ] = None,
        glossary_priority_order_enabled: Optional[bool] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> StyleProfile:
        """Updates a style profile. Options left as None are not sent and not
        changed. An empty string clears description or industry; a component
        list replaces the linked list in full, so an empty list unlinks all
        components of that kind.

        :param style_profile: Style profile ID string or StyleProfile object.
        :param name: (Optional) New name for the style profile.
        :param description: (Optional) New description; "" clears it.
        :param industry: (Optional) New industry; "" clears it.
        :param glossary_ids: (Optional) Glossaries to link, highest priority
            first, as IDs or GlossaryInfo / MultilingualGlossaryInfo objects;
            [] unlinks all glossaries.
        :param style_rule_ids: (Optional) Style rule lists to link, as IDs or
            StyleRuleInfo objects; [] unlinks all style rule lists.
        :param translation_memory_ids: (Optional) Translation memories to
            link, as IDs or TranslationMemoryInfo objects; [] unlinks all
            translation memories.
        :param glossary_priority_order_enabled: (Optional) Whether the order
            of glossary_ids decides which glossary wins when glossaries
            overlap.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: StyleProfile for the updated style profile.
        """
        style_profile_id = self._style_profile_id(style_profile)
        request_data = self._style_profile_json(
            name=name,
            description=description,
            industry=industry,
            glossary_ids=glossary_ids,
            style_rule_ids=style_rule_ids,
            translation_memory_ids=translation_memory_ids,
            glossary_priority_order_enabled=glossary_priority_order_enabled,
            extra_body_parameters=extra_body_parameters,
        )
        status, content, json = self._api_call(
            f"v3/style_profiles/{style_profile_id}",
            method="PATCH",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return StyleProfile.from_json(json)

    def delete_style_profile(
        self,
        style_profile: Union[str, StyleProfile],
    ) -> None:
        """Deletes a style profile.

        :param style_profile: Style profile ID string or StyleProfile object.
        :raises DeepLException: With http_status_code 404 if no style profile
            with the given ID is found.
        """
        style_profile_id = self._style_profile_id(style_profile)
        status, content, json = self._api_call(
            f"v3/style_profiles/{style_profile_id}", method="DELETE"
        )
        self._raise_for_status(status, content, json)

    @staticmethod
    def _style_profile_json(
        *,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ],
        style_rule_ids: Optional[List[Union[str, StyleRuleInfo]]],
        translation_memory_ids: Optional[
            List[Union[str, TranslationMemoryInfo]]
        ],
        extra_body_parameters: Optional[dict],
        **fields: Any,
    ) -> Dict[str, Any]:
        if glossary_ids is not None:
            fields["glossary_ids"] = [
                (
                    g.glossary_id
                    if isinstance(g, (GlossaryInfo, MultilingualGlossaryInfo))
                    else g
                )
                for g in glossary_ids
            ]
        if style_rule_ids is not None:
            fields["style_rule_ids"] = [
                s.style_id if isinstance(s, StyleRuleInfo) else s
                for s in style_rule_ids
            ]
        if translation_memory_ids is not None:
            fields["translation_memory_ids"] = [
                (
                    t.translation_memory_id
                    if isinstance(t, TranslationMemoryInfo)
                    else t
                )
                for t in translation_memory_ids
            ]
        # Unset (None) fields are not sent; "" and [] are sent as given.
        request_data = {k: v for k, v in fields.items() if v is not None}
        util._add_extra_body_parameters(request_data, extra_body_parameters)
        return request_data

    @staticmethod
    def _parse_style_rule_response(
        parse: Callable[[Any], _T], json: Any
    ) -> _T:
        try:
            return parse(json)
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            raise DeepLException(
                f"Unexpected style rule response from server: {e!r}"
            ) from e

    @staticmethod
    def _style_rule_id(style_rule: Union[str, StyleRuleInfo]) -> str:
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        return urllib.parse.quote(style_rule, safe="")

    @staticmethod
    def _custom_instruction_id(
        instruction_id: Union[str, CustomInstruction, None],
    ) -> str:
        if isinstance(instruction_id, CustomInstruction):
            instruction_id = instruction_id.id
        if not instruction_id:
            raise ValueError("instruction_id must not be empty")
        return urllib.parse.quote(instruction_id, safe="")

    @staticmethod
    def _style_profile_id(style_profile: Union[str, StyleProfile]) -> str:
        if isinstance(style_profile, StyleProfile):
            style_profile = style_profile.style_profile_id
        if not style_profile:
            raise ValueError("style_profile must not be empty")
        return urllib.parse.quote(style_profile, safe="")

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
        params = {}
        if page is not None:
            params["page"] = str(page)
        if page_size is not None:
            params["page_size"] = str(page_size)

        endpoint = "v3/translation_memories"
        if params:
            query_string = util.encode_query(params)
            endpoint += f"?{query_string}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)

        return self._parse_translation_memory_response(
            lambda body: [
                TranslationMemoryInfo.from_json(tm)
                for tm in body.get("translation_memories", [])
            ],
            json,
        )

    @staticmethod
    def _parse_translation_memory_response(
        parse: Callable[[Any], _T], json: Any
    ) -> _T:
        # A malformed body (missing keys, wrong types, not JSON at all) must
        # surface as DeepLException, not as a raw KeyError or TypeError.
        try:
            return parse(json)
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            raise DeepLException(
                "Unexpected response from translation memory API: "
                f"{type(error).__name__}: {error}",
                should_retry=False,
            ) from error

    @staticmethod
    def _translation_memory_id(
        translation_memory: Union[str, TranslationMemoryInfo],
    ) -> str:
        if isinstance(translation_memory, TranslationMemoryInfo):
            translation_memory = translation_memory.translation_memory_id
        if not translation_memory:
            raise ValueError("translation_memory must not be empty")
        return urllib.parse.quote(translation_memory, safe="")

    @staticmethod
    def _job_id(job: Union[str, TranslationMemoryJob]) -> str:
        if isinstance(job, TranslationMemoryJob):
            job = job.job_id
        if not job:
            raise ValueError("job must not be empty")
        return urllib.parse.quote(job, safe="")

    def get_translation_memory(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
    ) -> TranslationMemoryInfo:
        """Retrieves a single translation memory by ID.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        :return: TranslationMemoryInfo for the requested translation memory.
        """
        tm_id = self._translation_memory_id(translation_memory)
        status, content, json = self._api_call(
            f"v3/translation_memories/{tm_id}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return self._parse_translation_memory_response(
            TranslationMemoryInfo.from_json, json
        )

    def list_translation_memory_segments(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
        *,
        page_size: Optional[int] = None,
        page_cursor: Optional[str] = None,
        filter_text: Optional[str] = None,
        filter_case_sensitive: Optional[bool] = None,
    ) -> TranslationMemorySegments:
        """Retrieves one page of the segments of a translation memory.

        Pagination is cursor-based: omit page_cursor on the first call, then
        pass the previous response's next_page_cursor to fetch the next page.
        An absent next_page_cursor means the last page has been returned.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        :param page_size: (Optional) Maximum segments per page (1-100,
            defaults to 50).
        :param page_cursor: (Optional) Cursor from a previous response; omit
            on the first call.
        :param filter_text: (Optional) Substring filter across source and
            target text, at least 2 characters.
        :param filter_case_sensitive: (Optional) Whether the filter is
            case-sensitive, defaults to False.
        :return: TranslationMemorySegments for the requested page.
        """
        tm_id = self._translation_memory_id(translation_memory)

        params = {}
        if page_size is not None:
            params["page_size"] = str(page_size)
        if page_cursor is not None:
            params["page_cursor"] = page_cursor
        if filter_text is not None:
            params["filter_text"] = filter_text
        if filter_case_sensitive is not None:
            params["filter_case_sensitive"] = str(
                filter_case_sensitive
            ).lower()

        endpoint = f"v3/translation_memories/{tm_id}/segments"
        if params:
            query_string = util.encode_query(params)
            endpoint += f"?{query_string}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)
        return self._parse_translation_memory_response(
            TranslationMemorySegments.from_json, json
        )

    def delete_translation_memory(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
    ) -> None:
        """Deletes a translation memory.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        """
        tm_id = self._translation_memory_id(translation_memory)
        status, content, json = self._api_call(
            f"v3/translation_memories/{tm_id}", method="DELETE"
        )
        self._raise_for_status(status, content, json)

    def create_translation_memory_import(
        self,
        file_name: str,
        content_length: int,
        *,
        content_type: Optional[str] = None,
        display_name: Optional[str] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> TranslationMemoryImport:
        """Creates an import job for a new translation memory.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second import job. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        The job only declares the file; upload the TMX file itself to the
        returned upload URL with upload_translation_memory_file(), then poll
        get_translation_memory_job() for the outcome. Use
        import_translation_memory_from_filepath() to do all three steps at
        once.

        :param file_name: Name of the TMX file to import, for example
            "legal.tmx".
        :param content_length: Size of the TMX file in bytes.
        :param content_type: (Optional) MIME type of the file, defaults to
            "application/xml".
        :param display_name: (Optional) Name for the resulting translation
            memory, defaults to the file name.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: TranslationMemoryImport with the job ID and upload URL.
        """
        if not file_name:
            raise ValueError("file_name must not be empty")
        if content_length <= 0:
            raise ValueError("content_length must be greater than 0")

        source_file: Dict[str, Any] = {
            "file_name": file_name,
            "content_length": content_length,
        }
        if content_type is not None:
            source_file["content_type"] = content_type

        request_data: Dict[str, Any] = {"source_file": source_file}
        if display_name is not None:
            request_data["parameters"] = {"display_name": display_name}

        util._add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v3/translation_memories/import",
            json=request_data,
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)
        return self._parse_translation_memory_response(
            TranslationMemoryImport.from_json, json
        )

    def upload_translation_memory_file(
        self,
        translation_memory_import: Union[str, TranslationMemoryImport],
        content: Union[BinaryIO, bytes, Any],
        content_type: Optional[str] = "application/xml",
    ) -> None:
        """Uploads a TMX file to the upload URL of an import job, which starts
        processing.

        :param translation_memory_import: TranslationMemoryImport returned by
            create_translation_memory_import(), or its upload URL.
        :param content: TMX file content as bytes or a file-like object
            opened in binary mode.
        :param content_type: (Optional) MIME type of the file. Must match the
            content_type declared when the import job was created. None uses
            the default application/xml.

        :raises DeepLException: If the storage URL returns an error status,
            with http_status_code set; should_retry is True for 429 and 5xx.
        :raises ConnectionException: If the connection fails while the file
            is downloaded into output_file.
        """
        if isinstance(translation_memory_import, TranslationMemoryImport):
            upload_url = translation_memory_import.upload_url
        else:
            upload_url = translation_memory_import
        if not upload_url:
            raise ValueError("upload_url must not be empty")

        # Read a file-like object into bytes up front. The request is prepared
        # once and reused across retries, so a stream body would already be at
        # EOF on the second attempt and upload nothing.
        if hasattr(content, "read"):
            content = content.read()

        status_code, response_content = self._asset_call(
            "PUT",
            upload_url,
            data=content,
            headers={
                "Content-Type": (
                    "application/xml" if content_type is None else content_type
                )
            },
        )
        self._raise_for_asset_status(
            status_code, response_content, "uploading translation memory file"
        )

    def create_translation_memory_export(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
    ) -> TranslationMemoryExport:
        """Creates an export job for a translation memory.

        The request is only retried if it was not sent (HTTP 429 or a network
        failure while connecting, such as a DNS resolution failure, a refused
        connection, a connect timeout, or a reset or timeout in the TLS or
        proxy handshake): a retry after a server error, read timeout or lost
        connection could create a second export job. The raised exception has
        should_retry True only after those failures or a response body cut off
        mid-read.

        Poll get_translation_memory_job() for the download URL of the
        exported TMX file. Use export_translation_memory_to_filepath() to do
        both steps and write the file at once.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        :return: TranslationMemoryExport with the job ID.
        """
        tm_id = self._translation_memory_id(translation_memory)
        status, content, json = self._api_call(
            f"v3/translation_memories/{tm_id}/export",
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)
        # 200 means the API reused a previously completed export, 202 that it
        # started a new one.
        return self._parse_translation_memory_response(
            lambda body: TranslationMemoryExport.from_json(
                body, reused_existing=(status == 200)
            ),
            json,
        )

    def get_translation_memory_job(
        self,
        job: Union[str, TranslationMemoryJob],
    ) -> TranslationMemoryJob:
        """Retrieves the status of a translation memory import or export job.

        :param job: Job ID string or TranslationMemoryJob object.
        :return: TranslationMemoryJob with the current status.
        """
        job_id = self._job_id(job)
        status, content, json = self._api_call(
            f"v3/translation_memories/jobs/{job_id}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return self._parse_translation_memory_response(
            TranslationMemoryJob.from_json, json
        )

    def wait_until_translation_memory_job_done(
        self,
        job: Union[str, TranslationMemoryJob],
        timeout_s: Optional[float] = None,
    ) -> TranslationMemoryJob:
        """Polls a translation memory job until it completes, sleeping 5
        seconds between requests, and returns the completed job. An unknown
        status keeps polling.

        Note that an import job keeps reporting "awaiting_input" for a while
        after its file has been uploaded, because the API detects the upload
        asynchronously. That status is therefore polled through like any other
        non-terminal one. A job whose file is never uploaded does not finish on
        its own, so pass timeout_s when that is a possibility.

        :param job: Job ID string or TranslationMemoryJob object.
        :param timeout_s: (Optional) Maximum time in seconds to wait before
            raising an error. The last sleep is cut short so that the wait
            does not run past the timeout.
        :return: TranslationMemoryJob containing the completed status.

        :raises DeepLException: If the job fails or expires, with the API's
            error message, or if timeout_s is exceeded.
        """
        # Validates the reference; get_translation_memory_job() encodes it.
        self._job_id(job)
        return self._wait_until_translation_memory_job_done(
            job, timeout_s, lambda status: None
        )

    def _wait_until_translation_memory_job_done(
        self,
        job: Union[str, TranslationMemoryJob],
        timeout_s: Optional[float],
        on_status: Callable[[TranslationMemoryJob], None],
    ) -> TranslationMemoryJob:
        start_time_s = time.time()
        status = self.get_translation_memory_job(job)
        on_status(status)
        while True:
            if not status.ok:
                raise DeepLException(
                    f"Error occurred while {_tm_job_action(status)} "
                    f"translation memory: {_tm_job_error_message(status)}",
                    should_retry=False,
                )
            if status.done:
                return status
            secs = 5.0
            if timeout_s is not None:
                remaining_s = start_time_s + timeout_s - time.time()
                if remaining_s <= 0:
                    raise DeepLException(
                        f"Manual timeout of {timeout_s}s exceeded for"
                        + " translation memory job",
                        should_retry=False,
                    )
                secs = min(secs, remaining_s)
            util.log_info(
                f"Rechecking translation memory job status after sleeping "
                f"for {secs:.3f} seconds."
            )
            time.sleep(secs)
            status = self.get_translation_memory_job(job)
            on_status(status)

    def download_translation_memory_export(
        self,
        job: TranslationMemoryJob,
        output_file: Union[BinaryIO, Any],
        chunk_size: int = _DOWNLOAD_CHUNK_SIZE,
    ) -> None:
        """Downloads the TMX file of a completed export job.

        :param job: Completed export TranslationMemoryJob carrying the
            download URL.
        :param output_file: File-like object to store the downloaded TMX
            file.
        :param chunk_size: (Optional) Size of chunk in bytes for streaming,
            default 64 KiB.

        :raises DeepLException: If the job has no download URL (it has not
            completed, or is not an export), or the storage URL returns an
            error status, with http_status_code set; should_retry is True for
            429 and 5xx.
        """
        download_url = job.result.download_url if job.result else None
        if not download_url:
            raise DeepLException(
                "translation memory export job has no download URL; it may "
                "not have completed yet"
            )

        status_code, content = self._asset_call(
            "GET", download_url, stream=True
        )
        self._raise_for_asset_status(
            status_code, content, "downloading translation memory export"
        )
        assert isinstance(content, requests.Response)

        chunks = _http_client.iter_response_content(content, chunk_size)
        for chunk in chunks:
            output_file.write(chunk)

    def import_translation_memory_from_filepath(
        self,
        input_path: Union[os.PathLike, str],
        *,
        display_name: Optional[str] = None,
        timeout_s: Optional[float] = None,
        content_type: Optional[str] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> TranslationMemoryJob:
        """Imports a TMX file as a new translation memory: creates the import
        job, uploads the file, and waits for processing to finish.

        The request that creates the import job is only retried if it was not
        sent (HTTP 429 or a network failure while connecting, such as a DNS
        resolution failure, a refused connection, a connect timeout, or a reset
        or timeout in the TLS or proxy handshake): a retry after a server
        error, read timeout or lost connection could create a second import
        job. The raised exception has should_retry True only after those
        failures or a response body cut off mid-read.

        :param input_path: Path to the TMX file to import.
        :param display_name: (Optional) Name for the resulting translation
            memory, defaults to the file name.
        :param timeout_s: (Optional) Maximum time in seconds to wait for the
            import to finish. The last 5-second sleep between status checks is
            cut short so that the wait does not run past the timeout.
        :param content_type: (Optional) MIME type of the file, declared when
            creating the import job and sent with the upload. Defaults to
            "application/xml".
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON body of the request that creates the import
            job, replacing keys of the same name that the client sets.
        :return: TranslationMemoryJob for the completed import; its result
            carries the new translation memory ID.

        :raises ValueError: If input_path does not exist.
        :raises TranslationMemoryJobException: For every other failure: the
            file cannot be read or is empty (checked before the import job is
            created), creating the job fails, the upload is rejected, the
            import job fails or expires, or timeout_s is exceeded. The
            underlying exception is its __cause__; job_id is set once the job
            was created, and job holds the last status retrieved.
        """
        file_path = pathlib.Path(input_path)
        if not file_path.exists():
            raise ValueError(f"file does not exist: {input_path}")
        # Read the file before creating the job, so an unreadable file fails
        # without leaving an import job waiting for its upload.
        try:
            with open(file_path, "rb") as input_file:
                content = input_file.read()
        except OSError as e:
            raise TranslationMemoryJobException(
                f"Error reading translation memory file {input_path}: {e}"
            ) from e

        job_id: Optional[str] = None
        statuses: List[TranslationMemoryJob] = []
        try:
            created = self.create_translation_memory_import(
                file_name=file_path.name,
                content_length=len(content),
                content_type=content_type,
                display_name=display_name,
                extra_body_parameters=extra_body_parameters,
            )
            job_id = created.job_id
            self.upload_translation_memory_file(
                created,
                content,
                content_type=content_type or "application/xml",
            )
            return self._wait_until_translation_memory_job_done(
                job_id, timeout_s, statuses.append
            )
        except Exception as e:
            raise _tm_job_exception(
                e, job_id, statuses[-1] if statuses else None
            ) from e

    def export_translation_memory_to_filepath(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
        output_path: Union[os.PathLike, str],
        *,
        timeout_s: Optional[float] = None,
    ) -> TranslationMemoryJob:
        """Exports a translation memory to a TMX file: creates the export job,
        waits for it to finish, and writes the result to output_path.

        The request that creates the export job is only retried if it was not
        sent (HTTP 429 or a network failure while connecting, such as a DNS
        resolution failure, a refused connection, a connect timeout, or a reset
        or timeout in the TLS or proxy handshake): a retry after a server
        error, read timeout or lost connection could create a second export
        job. The raised exception has should_retry True only after those
        failures or a response body cut off mid-read.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        :param output_path: Path to write the exported TMX file to.
        :param timeout_s: (Optional) Maximum time in seconds to wait for the
            export to finish. The last 5-second sleep between status checks is
            cut short so that the wait does not run past the timeout.
        :return: TranslationMemoryJob for the completed export.

        :raises TranslationMemoryJobException: For every failure: output_path
            already exists or cannot be written (checked before the export job
            is created), creating the job fails, the export job fails or
            expires, timeout_s is exceeded, the download fails or writing the
            file fails. The underlying exception is its __cause__; job_id is
            set once the job was created, and job holds the last status
            retrieved. An existing file is never overwritten, and a partially
            written output file is removed.
        """
        path = pathlib.Path(output_path)
        # Check the output path before creating the job, so a path that
        # cannot be written fails without exporting first.
        directory = path.parent
        if not directory.is_dir():
            raise TranslationMemoryJobException(
                f"Output directory does not exist: {directory}"
            )
        if path.is_dir():
            raise TranslationMemoryJobException(
                f"Output path is a directory: {output_path}"
            )
        if path.exists():
            raise TranslationMemoryJobException(
                f"Output path already exists: {output_path}"
            )
        if not os.access(directory, os.W_OK):
            raise TranslationMemoryJobException(
                f"Output path is not writable: {output_path}"
            )

        job_id: Optional[str] = None
        statuses: List[TranslationMemoryJob] = []
        try:
            created = self.create_translation_memory_export(translation_memory)
            job_id = created.job_id
            # Raises before the output file is opened, so none is created.
            job = self._wait_until_translation_memory_job_done(
                job_id, timeout_s, statuses.append
            )
        except Exception as e:
            raise _tm_job_exception(
                e, job_id, statuses[-1] if statuses else None
            ) from e

        try:
            # "x" fails if the file was created after the check above.
            output_file = open(path, "xb")
        except OSError as e:
            raise _tm_job_exception(
                e,
                job_id,
                job,
                "Error writing translation memory export to "
                f"{output_path}: {e}",
            ) from e
        try:
            with output_file:
                self.download_translation_memory_export(
                    job, output_file, chunk_size=8192
                )
        except BaseException as e:
            # Do not leave a partial file behind.
            try:
                path.unlink()
            except OSError:
                pass
            if not isinstance(e, Exception):
                raise
            message = (
                "Error writing translation memory export to "
                f"{output_path}: {e}"
                if isinstance(e, OSError)
                else None
            )
            raise _tm_job_exception(e, job_id, job, message) from e
        return job

    def _asset_call(
        self,
        method: str,
        url: str,
        *,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ):
        """Makes a request to a storage URL handed out by the API, for example
        a translation memory upload or download URL.

        These URLs are pre-signed and point outside the DeepL API, so the
        DeepL Authorization header and other client headers are deliberately
        not sent. Only a caller User-Agent is sent, as on API requests.
        """
        util.log_info("Request to storage URL", method=method, url=url)
        request_headers = dict(headers or {})
        request_headers.update(
            {
                k: v
                for k, v in self.headers.items()
                if k.lower() == "user-agent"
            }
        )
        return self._client.request_with_backoff(
            method,
            url,
            data=data,
            json=None,
            headers=request_headers,
            stream=stream,
        )

    @staticmethod
    def _raise_for_asset_status(
        status_code: int,
        content: Union[str, requests.Response],
        action: str,
    ) -> None:
        if 200 <= status_code < 300:
            return
        if isinstance(content, requests.Response):
            # A streamed download: read the error body for the message.
            try:
                detail = _http_client.read_response_text(content)
            except ConnectionException:
                detail = ""
        else:
            detail = content
        message = f"Error {action}, HTTP status: {status_code}"
        if detail:
            message += f", detail: {detail}"
        # Storage URLs are not DeepL API endpoints, so every error is a plain
        # DeepLException; 429 and 5xx are retryable as for the API.
        raise DeepLException(
            message,
            should_retry=status_code == 429 or status_code >= 500,
            http_status_code=status_code,
        )
