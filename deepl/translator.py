# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.api_data import (
    DocumentHandle,
    DocumentStatus,
    Formality,
    GlossaryLanguagePair,
    GlossaryInfo,
    MultilingualGlossaryInfo,
    ModelType,
    Language,
    SplitSentences,
    StyleRuleInfo,
    TextResult,
    TranslationMemoryInfo,
    Usage,
)
from . import http_client, util
from .exceptions import (
    DocumentNotReadyException,
    GlossaryNotFoundException,
    QuotaExceededException,
    TooManyRequestsException,
    DeepLException,
    AuthorizationException,
    DocumentTranslationException,
)
import http
import http.client
import json as json_module
import os
import pathlib
import requests  # type: ignore
import time
from typing import (
    Any,
    BinaryIO,
    Dict,
    Iterable,
    List,
    Optional,
    TextIO,
    Tuple,
    Union,
)
import urllib.parse


class Translator:
    """Wrapper for the DeepL API for language translation.

    You must create an instance of Translator to use the DeepL API.

    :param auth_key: Authentication key as found in your DeepL API account.
    :param server_url: (Optional) Base URL of DeepL API, can be overridden e.g.
        for testing purposes.
    :param proxy: (Optional) Proxy server URL string or dictionary containing
        URL strings for the 'http' and 'https' keys. This is passed to the
        underlying requests session, see the requests proxy documentation for
        more information.
    :param send_platform_info: (Optional) boolean that indicates if the client
        library can send basic platform info (python version, OS, http library
        version) to the DeepL API. True = send info, False = only send client
        library version
    :param verify_ssl: (Optional) Controls how requests verifies SSL
        certificates. This is passed to the underlying requests session, see
        the requests verify documentation for more information.
    :param skip_language_check: Deprecated, and now has no effect as the
        corresponding internal functionality has been removed. This parameter
        will be removed in a future version.

    All functions may raise DeepLException or a subclass if a connection error
    occurs.
    """

    _DEEPL_SERVER_URL = "https://api.deepl.com"
    _DEEPL_SERVER_URL_FREE = "https://api-free.deepl.com"

    # HTTP status code used by DeepL API to indicate the character limit for
    # this billing period has been reached.
    _HTTP_STATUS_QUOTA_EXCEEDED = 456

    def __init__(
        self,
        auth_key: str,
        *,
        server_url: Optional[str] = None,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: bool = True,
        verify_ssl: Union[bool, str, None] = None,
        skip_language_check: bool = False,
    ):
        if not auth_key:
            raise ValueError("auth_key must not be empty")

        if server_url is None:
            server_url = (
                self._DEEPL_SERVER_URL_FREE
                if util.auth_key_is_free_account(auth_key)
                else self._DEEPL_SERVER_URL
            )

        self._server_url = server_url
        self._client = http_client.HttpClient(
            proxy, send_platform_info, verify_ssl
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

    def _check_valid_languages(
        self, source_lang: Optional[str], target_lang: str
    ):
        """Internal function to check given languages are valid."""
        if target_lang == "EN":
            raise DeepLException(
                'target_lang="EN" is deprecated, please use "EN-GB" or "EN-US"'
                "instead."
            )
        elif target_lang == "PT":
            raise DeepLException(
                'target_lang="PT" is deprecated, please use "PT-PT" or "PT-BR"'
                "instead."
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
    ) -> dict:
        # target_lang and source_lang are case insensitive
        target_lang = str(target_lang).upper()
        if source_lang is not None:
            source_lang = str(source_lang).upper()

        if glossary is not None and source_lang is None:
            raise ValueError("source_lang is required if using a glossary")

        if glossary_ids is not None:
            if glossary is not None:
                raise ValueError(
                    "glossary_ids cannot be used together with the glossary "
                    "parameter"
                )
            if source_lang is None:
                raise ValueError(
                    "source_lang is required if using glossary_ids"
                )
            if len(glossary_ids) > 5:
                raise ValueError(
                    "glossary_ids must not contain more than 5 glossary IDs"
                )

        if isinstance(glossary, GlossaryInfo):
            if (
                Language.remove_regional_variant(target_lang)
                != glossary.target_lang
                or source_lang != glossary.source_lang
            ):
                raise ValueError(
                    "source_lang and target_lang must match glossary"
                )

        if isinstance(glossary, MultilingualGlossaryInfo):
            target_lang_code = Language.remove_regional_variant(target_lang)
            if not any(
                glossary_dict.target_lang == target_lang_code
                and glossary_dict.source_lang == source_lang
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

        self._check_valid_languages(source_lang, target_lang)

        request_data: dict = {"target_lang": target_lang}
        if source_lang is not None:
            request_data["source_lang"] = source_lang
        if formality is not None:
            request_data["formality"] = str(formality).lower()
        if isinstance(glossary, GlossaryInfo) or isinstance(
            glossary, MultilingualGlossaryInfo
        ):
            request_data["glossary_id"] = glossary.glossary_id
        elif glossary is not None:
            request_data["glossary_id"] = glossary
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
            request_data["glossary_ids"] = resolved_ids
        if isinstance(style_rule, StyleRuleInfo):
            request_data["style_id"] = style_rule.style_id
        elif style_rule is not None:
            request_data["style_id"] = style_rule
        if isinstance(translation_memory, TranslationMemoryInfo):
            request_data["translation_memory_id"] = (
                translation_memory.translation_memory_id
            )
        elif translation_memory is not None:
            request_data["translation_memory_id"] = translation_memory
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
            "v2/glossaries", json=request_data
        )
        self._raise_for_status(status, content, json, glossary=True)
        return GlossaryInfo.from_json(json)

    def close(self):
        if hasattr(self, "_client"):
            self._client.close()

    def set_app_info(self, app_info_name: str, app_info_version: str):
        self._client.set_app_info(app_info_name, app_info_version)
        return self

    @property
    def server_url(self):
        return self._server_url

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
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
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
        :type text: UTF-8 :class:`str`; string sequence (list, tuple, iterator,
            generator)
        :param source_lang: (Optional) Language code of input text, for example
            "DE", "EN", "FR". If omitted, DeepL will auto-detect the input
            language. If a glossary is used, source_lang must be specified.
        :param target_lang: language code to translate text into, for example
            "DE", "EN-US", "FR".
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
            translation. Must match specified source_lang and target_lang.
        :param glossary_ids: (Optional) list of up to 5 glossaries or glossary
            IDs to use for translation, applied in order. Requires source_lang
            to be set and cannot be combined with the glossary parameter.
        :param style_rule: (Optional) style rule or style rule ID to use for
            translation.
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param tag_handling: (Optional) Type of tags to parse before
            translation, only "xml" and "html" are currently available.
        :param tag_handling_version: (Optional) Version of tag handling
            algorithm to use, "v1" or "v2".
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
            keys in this dict will be added to the request body. Existing
            keys set by the client will not be overwritten by entries in
            extra_body_parameters.
        :return: List of TextResult objects containing results, unless input
            text was one string, then a single TextResult object is returned.
        """
        if isinstance(text, str):
            if len(text) == 0:
                raise ValueError("text must not be empty")
            text = [text]
            multi_input = False
        elif hasattr(text, "__iter__"):
            multi_input = True
            text = list(text)
        else:
            raise TypeError(
                "text parameter must be a string or an iterable of strings"
            )

        request_data = self._check_language_and_formality(
            source_lang,
            target_lang,
            formality,
            glossary,
            style_rule,
            translation_memory,
            translation_memory_threshold,
            glossary_ids,
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
            request_data["tag_handling"] = tag_handling
        if tag_handling_version is not None:
            request_data["tag_handling_version"] = tag_handling_version
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

        # Do not overwrite keys that were explicitly set by this method.
        if extra_body_parameters:
            for k, v in extra_body_parameters.items():
                request_data[k] = v

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
            billed_characters = int(translation.get("billed_characters"))
            model_type_used = translation.get("model_type_used")
            output.append(
                TextResult(
                    text,
                    detected_source_language,
                    billed_characters,
                    model_type_used,
                )
            )

        return output if multi_input else output[0]

    def translate_text_with_glossary(
        self,
        text: Union[str, Iterable[str]],
        glossary: GlossaryInfo,
        target_lang: Union[str, Language, None] = None,
        **kwargs,
    ) -> Union[TextResult, List[TextResult]]:
        """Translate text(s) using given glossary. The source and target
        languages are assumed to match the glossary languages.

        Note that if the glossary target language is English (EN), the text
        will be translated into British English (EN-GB). To instead translate
        into American English specify target_lang="EN-US".

        :param text: Text to translate.
        :type text: UTF-8 :class:`str`; string sequence (list, tuple, iterator,
            generator)
        :param glossary: glossary to use for translation.
        :type glossary: :class:`GlossaryInfo`.
        :param target_lang: override target language of glossary.
        :return: List of TextResult objects containing results, unless input
            text was one string, then a single TextResult object is returned.
        """

        if not isinstance(glossary, GlossaryInfo):
            msg = (
                "This function expects the glossary parameter to be an "
                "instance of GlossaryInfo. Use get_glossary() to obtain a "
                "GlossaryInfo using the glossary ID of an existing "
                "glossary. Alternatively, use translate_text() and "
                "specify the glossary ID using the glossary parameter. "
            )
            raise ValueError(msg)

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
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        timeout_s: Optional[int] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentStatus:
        """Upload document at given input path, translate it into the target
        language, and download result to given output path.

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
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param timeout_s: (beta) (Optional) Maximum time to wait before
            the call raises an error. Note that this is not accurate to the
            second, but only polls every 5 seconds.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body. Existing
            keys set by the client will not be overwritten by entries in
            extra_body_parameters.
        :return: DocumentStatus when document translation completed, this
            allows the number of billed characters to be queried.

        :raises DocumentTranslationException: If an error occurs during
            translation. The exception includes information about the document
            request.
        """
        # Determine output_format from output path
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
                        glossary_ids=glossary_ids,
                        style_rule=style_rule,
                        translation_memory=translation_memory,
                        translation_memory_threshold=(
                            translation_memory_threshold
                        ),
                        output_format=output_format,
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
        *,
        source_lang: Optional[str] = None,
        target_lang: str,
        formality: Union[str, Formality] = Formality.DEFAULT,
        glossary: Union[
            str, GlossaryInfo, MultilingualGlossaryInfo, None
        ] = None,
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        filename: Optional[str] = None,
        output_format: Optional[str] = None,
        timeout_s: Optional[int] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentStatus:
        """Upload document, translate it into the target language, and download
        result.

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
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param filename: (Optional) Filename including extension, only required
            if uploading string or bytes containing file content.
        :param output_format: (Optional) Desired output file extension, if
            it differs from the input file format.
        :param timeout_s: (beta) (Optional) Maximum time to wait before
            the call raises an error. Note that this is not accurate to the
            second, but only polls every 5 seconds.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body. Existing
            keys set by the client will not be overwritten by entries in
            extra_body_parameters.
        :return: DocumentStatus when document translation completed, this
            allows the number of billed characters to be queried.

        :raises DocumentTranslationException: If an error occurs during
            translation, the exception includes the document handle.
        """

        handle = self.translate_document_upload(
            input_document,
            target_lang=target_lang,
            source_lang=source_lang,
            formality=formality,
            glossary=glossary,
            glossary_ids=glossary_ids,
            style_rule=style_rule,
            translation_memory=translation_memory,
            translation_memory_threshold=translation_memory_threshold,
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
        glossary_ids: Optional[
            List[Union[str, GlossaryInfo, MultilingualGlossaryInfo]]
        ] = None,
        style_rule: Union[str, StyleRuleInfo, None] = None,
        translation_memory: Union[str, TranslationMemoryInfo, None] = None,
        translation_memory_threshold: Optional[int] = None,
        filename: Optional[str] = None,
        output_format: Optional[str] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DocumentHandle:
        """Upload document to be translated and return handle associated with
        request.

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
        :param translation_memory: (Optional) translation memory or translation
            memory ID to use for translation.
        :param translation_memory_threshold: (Optional) minimum matching
            percentage for fuzzy matches from the translation memory (0-100).
            Recommended minimum is 75%.
        :param filename: (Optional) Filename including extension, only required
            if uploading string or bytes containing file content.
        :param output_format: (Optional) Desired output file extension, if
            it differs from the input file format.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body. Existing
            keys set by the client will not be overwritten by entries in
            extra_body_parameters.
        :return: DocumentHandle with ID and key identifying document.
        """

        request_data = self._check_language_and_formality(
            source_lang,
            target_lang,
            formality,
            glossary,
            style_rule,
            translation_memory,
            translation_memory_threshold,
            glossary_ids=glossary_ids,
        )
        if output_format:
            request_data["output_format"] = output_format

        # The document endpoint uses multipart/form-data. Send glossary_ids as
        # a single comma-separated field (the form form of the array), matching
        # the other SDKs, instead of repeated multipart fields.
        if isinstance(request_data.get("glossary_ids"), list):
            request_data["glossary_ids"] = ",".join(
                request_data["glossary_ids"]
            )

        files: Dict[str, Any] = {}
        if isinstance(input_document, (str, bytes)):
            if filename is None:
                raise ValueError(
                    "filename is required if uploading file content as string "
                    "or bytes"
                )
            files = {"file": (filename, input_document)}
        else:
            files = {"file": input_document}
        if extra_body_parameters:
            for k, v in extra_body_parameters.items():
                request_data[k] = v

        status, content, json = self._api_call(
            "v2/document", data=request_data, files=files
        )
        self._raise_for_status(status, content, json)

        if not json:
            json = {}
        return DocumentHandle(
            json.get("document_id", ""), json.get("document_key", "")
        )

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
        url = f"v2/document/{handle.document_id}"

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
        return DocumentStatus(
            status, seconds_remaining, billed_characters, error_message
        )

    def translate_document_wait_until_done(
        self,
        handle: DocumentHandle,
        timeout_s: Optional[int] = None,
    ) -> DocumentStatus:
        """
        Continually polls the status of the document translation associated
        with the given handle, sleeping in between requests, and returns the
        final status when the translation completes (whether successful or
        not).
        :param handle: DocumentHandle to the document translation to wait on.
        :param timeout_s: (beta) (Optional) Maximum time to wait before
            the call raises an error. Note that this is not accurate to the
            second, but only polls every 5 seconds.
        :return: DocumentStatus containing the status when completed.
        """
        status = self.translate_document_get_status(handle)
        start_time_s = time.time()
        while status.ok and not status.done:
            if (
                timeout_s is not None
                and time.time() - start_time_s > timeout_s
            ):
                raise DeepLException(
                    f"Manual timeout of {timeout_s}s exceeded for"
                    + " document translation",
                    should_retry=False,
                )
            else:
                secs = (
                    5.0  # seconds_remaining is currently unreliable, so just
                )
                # poll equidistantly
                util.log_info(
                    f"Rechecking document translation status "
                    f"after sleeping for {secs:.3f} seconds."
                )
                time.sleep(secs)
                status = self.translate_document_get_status(handle)
        return status

    def translate_document_download(
        self,
        handle: DocumentHandle,
        output_file: Union[TextIO, BinaryIO, Any, None] = None,
        chunk_size: int = 1,
    ) -> Optional[requests.Response]:
        """Downloads the translated document for the request associated with
        given handle and returns a response object for streaming the data. Call
        iter_content() on the response object to read streamed file data.
        Alternatively, a file-like object may be given as output_file where the
        complete file will be downloaded and written to.

        :param handle: DocumentHandle associated with request.
        :param output_file: (Optional) File-like object to store downloaded
            document. If not provided, use iter_content() on the returned
            response object to read streamed file data.
        :param chunk_size: (Optional) Size of chunk in bytes for streaming.
            Only used if output_file is specified.
        :return: None if output_file is specified, otherwise the
            requests.Response will be returned.
        """

        data = {"document_key": handle.document_key}
        url = f"v2/document/{handle.document_id}/result"

        status_code, response, json = self._api_call(
            url, json=data, stream=True
        )
        # TODO: once we drop py3.6 support, replace this with @overload
        # annotations in `_api_call` and chained private functions.
        # See for example https://stackoverflow.com/a/74070166/4926599
        # In addition, drop the type: ignore annotation on the
        # `import requests` / `from requests`
        assert isinstance(response, requests.Response)

        self._raise_for_status(
            status_code, "<file>", json, downloading_document=True
        )

        if output_file:
            chunks = response.iter_content(chunk_size=chunk_size)
            for chunk in chunks:
                output_file.write(chunk)
            return None
        else:
            return response

    def get_source_languages(self, skip_cache: bool = False) -> List[Language]:
        """Request the list of available source languages.

        :param skip_cache: Deprecated, and now has no effect as the
            corresponding internal functionality has been removed. This
            parameter will be removed in a future version.
        :return: List of supported source languages.
        """
        status, content, json = self._api_call("v2/languages", method="GET")
        self._raise_for_status(status, content, json)
        languages = json if (json and isinstance(json, list)) else []
        return [
            Language(
                language["language"],
                language["name"],
            )
            for language in languages
        ]

    def get_target_languages(self, skip_cache: bool = False) -> List[Language]:
        """Request the list of available target languages.

        :param skip_cache: Deprecated, and now has no effect as the
            corresponding internal functionality has been removed. This
            parameter will be removed in a future version.
        :return: List of supported target languages.
        """
        data = {"type": "target"}
        status, content, json = self._api_call(
            "v2/languages", method="GET", data=data
        )
        self._raise_for_status(status, content, json)
        languages = json if (json and isinstance(json, list)) else []
        return [
            Language(
                language["language"],
                language["name"],
                language.get("supports_formality", None),
            )
            for language in languages
        ]

    def get_glossary_languages(self) -> List[GlossaryLanguagePair]:
        """Request the list of language pairs supported for glossaries."""
        status, content, json = self._api_call(
            "v2/glossary-language-pairs", method="GET"
        )

        self._raise_for_status(status, content, json)

        supported_languages = (
            json.get("supported_languages", [])
            if (json and isinstance(json, dict))
            else []
        )
        return [
            GlossaryLanguagePair(
                language_pair["source_lang"], language_pair["target_lang"]
            )
            for language_pair in supported_languages
        ]

    def get_usage(self) -> Usage:
        """Requests the current API usage."""
        status, content, json = self._api_call("v2/usage", method="GET")

        self._raise_for_status(status, content, json)

        if not isinstance(json, dict):
            json = {}
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

        :raises ValueError: If the glossary name is empty, or entries are
            empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """

        entries = (
            csv_data if isinstance(csv_data, (str, bytes)) else csv_data.read()
        )

        if not isinstance(entries, (bytes, str)):
            raise ValueError("Entries of the glossary are invalid")
        return self._create_glossary(
            name, source_lang, target_lang, "csv", entries
        )

    def get_glossary(self, glossary_id: str) -> GlossaryInfo:
        """Retrieves GlossaryInfo for the glossary with specified ID.

        :param glossary_id: ID of glossary to retrieve.
        :return: GlossaryInfo with information about specified glossary.
        :raises GlossaryNotFoundException: If no glossary with given ID is
            found.
        """
        status, content, json = self._api_call(
            f"v2/glossaries/{glossary_id}", method="GET"
        )
        self._raise_for_status(status, content, json, glossary=True)
        return GlossaryInfo.from_json(json)

    def list_glossaries(self) -> List[GlossaryInfo]:
        """Retrieves GlossaryInfo for all available glossaries.

        :return: list of GlossaryInfo for all available glossaries.
        """
        status, content, json = self._api_call("v2/glossaries", method="GET")
        self._raise_for_status(status, content, json, glossary=True)
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
        :raises GlossaryNotFoundException: If no glossary with given ID is
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
        self._raise_for_status(status, content, json, glossary=True)
        if not isinstance(content, str):
            raise DeepLException(
                "Could not get the glossary content as a string",
                http_status_code=status,
            )
        return util.convert_tsv_to_dict(content)

    def delete_glossary(self, glossary: Union[str, GlossaryInfo]) -> None:
        """Deletes specified glossary.

        :param glossary: GlossaryInfo or ID of glossary to delete.
        :raises GlossaryNotFoundException: If no glossary with given ID is
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
        self._raise_for_status(status, content, json, glossary=True)
