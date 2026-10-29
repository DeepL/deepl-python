# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.api_data import (
    AppInfo,
    CustomInstruction,
    GlossaryInfo,
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryDictionaryEntriesResponse,
    MultilingualGlossaryDictionaryInfo,
    MultilingualGlossaryInfo,
    Language,
    LanguageInclude,
    LanguageResource,
    LanguageResourceName,
    LanguageSupport,
    SpokenTerms,
    SpokenTermsEntries,
    SpokenTermsList,
    WriteResult,
    WritingStyle,
    WritingTone,
    StyleProfile,
    StyleRuleInfo,
    TranslationMemoryExport,
    TranslationMemoryImport,
    TranslationMemoryInfo,
    TranslationMemoryJob,
    TranslationMemorySegments,
)
from deepl.exceptions import DeepLException
from deepl.translator import (
    Translator,
    _DOWNLOAD_CHUNK_SIZE,
    _warn_download_without_output_file,
    _warn_skip_language_check,
)
from deepl import util
import os
import pathlib
import requests  # type: ignore
import time
import urllib.parse
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
    TypeVar,
    Union,
)

_T = TypeVar("_T")


def _apply_extra_body_parameters(
    request_data: dict, extra_body_parameters: Optional[dict]
) -> None:
    # Entries replace keys of the same name set by the client.
    if extra_body_parameters:
        for k, v in extra_body_parameters.items():
            request_data[k] = v


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


class DeepLClient(Translator):
    def __init__(
        self,
        auth_key: str,
        *,
        server_url: Optional[str] = None,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: bool = True,
        verify_ssl: Union[bool, str, None] = None,
        max_retries: Optional[int] = None,
        timeout_s: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        app_info: Optional[AppInfo] = None,
        skip_language_check: Optional[bool] = None,
    ):
        if skip_language_check is not None:
            _warn_skip_language_check()
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

    def rephrase_text(
        self,
        text: Union[str, Iterable[str]],
        *,
        target_lang: Union[None, str, Language] = None,
        style: Union[str, WritingStyle, None] = None,
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
        :param style: Deprecated alias of `writing_style`.

            .. deprecated:: 1.33.0
                Use `writing_style` instead.
        :param tone: Tone to be used for the improvement, as a WritingTone or
            string. Either writing_style OR tone can be used.
        :param writing_style: Writing style to be used for the improvement, as
            a WritingStyle or string. Either writing_style OR tone can be
            used. Takes precedence over the deprecated `style`.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. If provided,
            keys in this dict will be added to the request body, and replace
            keys of the same name that the client sets.
        :return: List of WriteResult objects containing results, unless input
            text was one string, then a single WriteResult object is returned.
        """
        if style is not None:
            warnings.warn(
                "style is deprecated, use writing_style",
                DeprecationWarning,
                stacklevel=2,
            )
            if writing_style is None:
                writing_style = style

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

        request_data: dict = {"text": text}
        if target_lang:
            request_data["target_lang"] = str(target_lang)
        if writing_style:
            request_data["writing_style"] = str(writing_style)
        if tone:
            request_data["tone"] = str(tone)
        _apply_extra_body_parameters(request_data, extra_body_parameters)

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

        request_data: dict = {"text": text}
        if target_lang:
            request_data["target_lang"] = str(target_lang)
        _apply_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v2/write/correct", json=request_data
        )

        self._raise_for_status(status, content, json)

        output = _parse_improvements(json, len(text))
        return output if multi_input else output[0]

    def create_multilingual_glossary(
        self,
        name: str,
        glossary_dicts: List[MultilingualGlossaryDictionaryEntries],
    ) -> MultilingualGlossaryInfo:
        """Creates a glossary with given name with all of the specified
        dictionaries, each with their own language pair and entries. The
        glossary may be used in the translate_text functions.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function requires the glossary entries for each dictionary to be
        provided as a dictionary of source-target terms. To create a glossary
        from a CSV file downloaded from the DeepL website, see
        create_glossary_from_csv().

        :param name: user-defined name to attach to glossary.
        :param dictionaries: a list of MultilingualGlossaryDictionaryEntries
            which each contains entries for a particular language pair
        :return: GlossaryInfo containing information about created glossary.

        :raises ValueError: If the glossary name is empty, or entries are
            empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        if any(map(lambda d: not d.entries, glossary_dicts)):
            raise ValueError("glossary entries must not be empty")

        return self._create_multilingual_glossary(name, glossary_dicts)

    def create_multilingual_glossary_from_csv(
        self,
        name: str,
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    ) -> MultilingualGlossaryInfo:
        """Creates a glossary with given name for the source and target
        languages, containing the entries in the given CSV data.
        The glossary may be used in the translate_text functions.

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
        :param csv_data: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :return: GlossaryInfo containing information about created glossary.

        :raises ValueError: If the glossary name is empty, or entries are
            empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
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
        if not name:
            raise ValueError("glossary name must not be empty")

        req_glossary_dicts = []
        # glossaries are only supported for base language types
        for glossary_dict in glossary_dicts:
            req_glossary_dict = {
                "source_lang": Language.remove_regional_variant(
                    glossary_dict.source_lang
                ),
                "target_lang": Language.remove_regional_variant(
                    glossary_dict.target_lang
                ),
                "entries": util.convert_dict_to_tsv(glossary_dict.entries),
                "entries_format": "tsv",
            }
            req_glossary_dicts.append(req_glossary_dict)

        request_data = {
            "name": name,
            "dictionaries": req_glossary_dicts,
        }

        status, content, json = self._api_call(
            "v3/glossaries", json=request_data
        )
        self._raise_for_status(status, content, json, glossary=True)
        return MultilingualGlossaryInfo.from_json(json)

    def update_multilingual_glossary_name(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        name: str,
    ) -> MultilingualGlossaryInfo:
        """Updates the name of a glossary with the provided name.

        :param glossary: GlossaryInfo or ID of glossary to update.
        :param name: The new name of the glossary
        :return: MultilingualGlossaryInfo containing information about updated
            glossary.

        :raises ValueError: If the name is empty or invalid.
        :raises DeepLException: If the glossary cannot be found.
        """
        if not name:
            raise ValueError("glossary name must not be empty")

        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id
        request_data = {"name": name}

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary}", method="PATCH", json=request_data
        )
        self._raise_for_status(status, content, json, glossary=True)
        return MultilingualGlossaryInfo.from_json(json)

    def update_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        glossary_dict: MultilingualGlossaryDictionaryEntries,
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
        dictionary of source-target terms. To create a glossary from a CSV file
        downloaded from the DeepL website, see create_glossary_from_csv().

        :param glossary: GlossaryInfo or ID of glossary to update.
        :param glossary_dict: The new or updated glossary dictionary
        :return: MultilingualGlossaryInfo containing information about updated
            glossary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        if not glossary_dict or not glossary_dict.entries:
            raise ValueError("glossary entries must not be empty")

        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id

        return self._update_multilingual_glossary(glossary, [glossary_dict])

    def update_multilingual_glossary_dictionary_from_csv(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
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
        :param csv_data: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :return: MultilingualGlossaryInfo containing information about updated
            glossary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        entries = util.convert_csv_to_dict(csv_data)

        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id

        dictionaries = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        return self._update_multilingual_glossary(glossary, dictionaries)

    def _update_multilingual_glossary(
        self,
        glossary_id: str,
        dictionaries: List[MultilingualGlossaryDictionaryEntries],
    ) -> MultilingualGlossaryInfo:
        if not glossary_id:
            raise ValueError("glossary id must not be empty")

        req_glossary_dicts = []
        # glossaries are only supported for base language types
        for glossary_dict in dictionaries:
            req_glossary_dict = {
                "source_lang": Language.remove_regional_variant(
                    glossary_dict.source_lang
                ),
                "target_lang": Language.remove_regional_variant(
                    glossary_dict.target_lang
                ),
                "entries": util.convert_dict_to_tsv(glossary_dict.entries),
                "entries_format": "tsv",
            }
            req_glossary_dicts.append(req_glossary_dict)

        request_data = {}

        if dictionaries:
            request_data["dictionaries"] = req_glossary_dicts

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}", method="PATCH", json=request_data
        )
        self._raise_for_status(status, content, json, glossary=True)

        return MultilingualGlossaryInfo.from_json(json)

    def replace_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        glossary_dict: MultilingualGlossaryDictionaryEntries,
    ) -> MultilingualGlossaryDictionaryInfo:
        """Replaces a glossary dictionary with given entries for the
        source and target languages.

        The available glossary language pairs can be queried using
        get_glossary_languages(). Glossaries apply to languages, not specific
        language variants. A glossary for a language applies to any variant
        of that language: a glossary with target language EN may be used to
        translate texts into both EN-US and EN-GB.

        This function requires the glossary entries to be provided as a
        dictionary of source-target terms. To create a glossary from a CSV file
        downloaded from the DeepL website, see create_glossary_from_csv().

        :param glossary: GlossaryInfo or ID of glossary to update.
        :param glossary_dict: The new glossary dictionary
        :return: MultilingualGlossaryDictionaryInfo containing information
            about the updated dictionary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        if not glossary_dict or not glossary_dict.entries:
            raise ValueError("glossary entries must not be empty")

        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id

        return self._replace_multilingual_glossary_dictionary(
            glossary,
            glossary_dict.source_lang,
            glossary_dict.target_lang,
            glossary_dict.entries,
        )

    def replace_multilingual_glossary_dictionary_from_csv(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
        csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
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
        :param csv_data: CSV data containing glossary entries, either as a
            file-like object or string or bytes containing file content.
        :return: MultilingualGlossaryDictionaryInfo containing information
            about updated dictionary.

        :raises ValueError: If the glossary entries are empty or invalid.
        :raises DeepLException: If source and target language pair are not
            supported for glossaries.
        """
        entries = util.convert_csv_to_dict(csv_data)

        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id

        return self._replace_multilingual_glossary_dictionary(
            glossary, source_lang, target_lang, entries
        )

    def _replace_multilingual_glossary_dictionary(
        self,
        glossary_id: str,
        source_lang: str,
        target_lang: str,
        entries: Dict[str, str],
    ) -> MultilingualGlossaryDictionaryInfo:
        if not glossary_id:
            raise ValueError("glossary id must not be empty")

        # glossaries are only supported for base language types
        source_lang = Language.remove_regional_variant(source_lang)
        target_lang = Language.remove_regional_variant(target_lang)

        request_data = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "entries": util.convert_dict_to_tsv(entries),
            "entries_format": "tsv",
        }

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}/dictionaries",
            method="PUT",
            json=request_data,
        )
        self._raise_for_status(status, content, json, glossary=True)
        return MultilingualGlossaryDictionaryInfo.from_json(json)

    def get_multilingual_glossary(
        self, glossary_id: str
    ) -> MultilingualGlossaryInfo:
        """Retrieves MultilingualGlossaryInfo for the glossary with specified
        ID.

        :param glossary_id: ID of glossary to retrieve.
        :return: MultilingualGlossaryInfo with information about specified
            glossary.
        :raises GlossaryNotFoundException: If no glossary with given ID is
            found.
        """
        status, content, json = self._api_call(
            f"v3/glossaries/{glossary_id}", method="GET"
        )
        self._raise_for_status(status, content, json, glossary=True)
        return MultilingualGlossaryInfo.from_json(json)

    def list_multilingual_glossaries(self) -> List[MultilingualGlossaryInfo]:
        """Retrieves a list of MultilingualGlossaryInfo for all available
        glossaries.

        :return: list of MultilingualGlossaryInfos for all available
            glossaries.
        """
        status, content, json = self._api_call("v3/glossaries", method="GET")
        self._raise_for_status(status, content, json, glossary=True)
        glossaries = (
            json.get("glossaries", [])
            if (json and isinstance(json, dict))
            else []
        )
        return [
            MultilingualGlossaryInfo.from_json(glossary)
            for glossary in glossaries
        ]

    def get_multilingual_glossary_entries(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        source_lang: str,
        target_lang: str,
    ) -> MultilingualGlossaryDictionaryEntriesResponse:
        """Retrieves the entries for a given source and target language in the
        specified glossary.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to
            retrieve.
        :param source_lang: Language of source terms.
        :param target_lang: Language of target terms.
        :return: MultilingualGlossaryDictionaryEntriesResponse object
            containing the entries.
        :raises GlossaryNotFoundException: If no glossary with given ID is
            found.
        :raises DeepLException: If the glossary could not be retrieved
            in the right format.
        """
        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id
        source_lang = Language.remove_regional_variant(source_lang)
        target_lang = Language.remove_regional_variant(target_lang)

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary}/entries?source_lang={source_lang}&target_lang={target_lang}",  # noqa: E501
            method="GET",
        )
        self._raise_for_status(status, content, json, glossary=True)
        return MultilingualGlossaryDictionaryEntriesResponse.from_json(json)

    def delete_multilingual_glossary(
        self, glossary: Union[str, MultilingualGlossaryInfo]
    ) -> None:
        """Deletes specified glossary.

        :param glossary: MultilingualGlossaryInfo or ID of glossary to delete.
        :raises GlossaryNotFoundException: If no glossary with given ID is
            found.
        """
        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id

        status, content, json = self._api_call(
            f"v3/glossaries/{glossary}",
            method="DELETE",
        )
        self._raise_for_status(status, content, json, glossary=True)

    def delete_multilingual_glossary_dictionary(
        self,
        glossary: Union[str, MultilingualGlossaryInfo],
        dictionary: Optional[MultilingualGlossaryDictionaryInfo] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> None:
        """Deletes specified glossary dictionary.

        :param glossary: GlossaryInfo or ID of glossary containing the
            dictionary to delete
        :param dictionary: The dictionary to delete. Either the
            MultilingualGlossaryDictionaryInfo or both the source_lang and
            target_lang can be provided to identify the dictionary. However,
            if both are provided, the dictionary takes precendence over
            source_lang and target_lang.
        :param source_lang: Optional parameter representing the source language
            of the dictionary
        :param target_lang: Optional parameter representing the target language
            of the dictionary
        :raises GlossaryNotFoundException: If no glossary with given ID is
            found.
        :raises ValueError: If the dictionary or both the source_lang and
            target_lang were not provided
        """
        if isinstance(glossary, MultilingualGlossaryInfo):
            glossary = glossary.glossary_id

        if not dictionary and not (source_lang and target_lang):
            raise ValueError(
                "must provide dictionary or both source_lang and target_lang"
            )

        if dictionary:
            source_lang = dictionary.source_lang
            target_lang = dictionary.target_lang

        req_url = f"v3/glossaries/{glossary}/dictionaries?source_lang={source_lang}&target_lang={target_lang}"  # noqa: E501
        status, content, json = self._api_call(
            req_url,
            method="DELETE",
        )
        self._raise_for_status(status, content, json, glossary=True)

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
        request_data.update(extra_body_parameters or {})
        status, content, json = self._api_call(
            "v3/spoken-terms", json=request_data
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
        request_data.update(extra_body_parameters or {})
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
        query = urllib.parse.urlencode({"lang": lang})
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
        request_data.update(extra_body_parameters or {})
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
        query = urllib.parse.urlencode({"lang": lang})
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

        endpoint = f"v3/languages?{urllib.parse.urlencode(params)}"
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
            query_string = urllib.parse.urlencode(params)
            endpoint += f"?{query_string}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)

        style_rules = (
            json.get("style_rules", [])
            if (json and isinstance(json, dict))
            else []
        )
        return [
            StyleRuleInfo.from_json(style_rule) for style_rule in style_rules
        ]

    def create_style_rule(
        self,
        name: str,
        language: str,
        configured_rules: Optional[dict] = None,
        custom_instructions: Optional[List[dict]] = None,
    ) -> StyleRuleInfo:
        """Creates a new style rule.

        :param name: Name for the style rule.
        :param language: Language code for the style rule.
        :param configured_rules: Optional dict of configured rules.
        :param custom_instructions: Optional list of custom instruction dicts.
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
            request_data["custom_instructions"] = custom_instructions

        status, content, json = self._api_call(
            "v3/style_rules", json=request_data
        )
        self._raise_for_status(status, content, json)
        return StyleRuleInfo.from_json(json)

    def get_style_rule(
        self,
        style_rule: Union[str, StyleRuleInfo],
    ) -> StyleRuleInfo:
        """Retrieves a single style rule by ID.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :return: StyleRuleInfo for the requested style rule.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        status, content, json = self._api_call(
            f"v3/style_rules/{style_rule}", method="GET"
        )
        self._raise_for_status(status, content, json)
        return StyleRuleInfo.from_json(json)

    def update_style_rule_name(
        self,
        style_rule: Union[str, StyleRuleInfo],
        name: str,
    ) -> StyleRuleInfo:
        """Updates the name of a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param name: New name for the style rule.
        :return: Updated StyleRuleInfo.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not name:
            raise ValueError("name must not be empty")
        request_data = {"name": name}
        status, content, json = self._api_call(
            f"v3/style_rules/{style_rule}", method="PATCH", json=request_data
        )
        self._raise_for_status(status, content, json)
        return StyleRuleInfo.from_json(json)

    def delete_style_rule(
        self,
        style_rule: Union[str, StyleRuleInfo],
    ) -> None:
        """Deletes a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        status, content, json = self._api_call(
            f"v3/style_rules/{style_rule}", method="DELETE"
        )
        self._raise_for_status(status, content, json)

    def update_style_rule_configured_rules(
        self,
        style_rule: Union[str, StyleRuleInfo],
        configured_rules: dict,
    ) -> StyleRuleInfo:
        """Updates the configured rules of a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param configured_rules: Dict of configured rules to set.
        :return: Updated StyleRuleInfo.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        status, content, json = self._api_call(
            f"v3/style_rules/{style_rule}/configured_rules",
            method="PUT",
            json=configured_rules,
        )
        self._raise_for_status(status, content, json)
        return StyleRuleInfo.from_json(json)

    def create_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
    ) -> CustomInstruction:
        """Creates a custom instruction for a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param label: Label for the custom instruction.
        :param prompt: Prompt text for the custom instruction.
        :param source_language: Optional source language code.
        :return: Created CustomInstruction.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not label:
            raise ValueError("label must not be empty")
        if not prompt:
            raise ValueError("prompt must not be empty")
        request_data = {"label": label, "prompt": prompt}
        if source_language is not None:
            request_data["source_language"] = source_language
        status, content, json = self._api_call(
            f"v3/style_rules/{style_rule}/custom_instructions",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return CustomInstruction.from_json(json)

    def get_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: str,
    ) -> CustomInstruction:
        """Retrieves a custom instruction by ID.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param instruction_id: ID of the custom instruction.
        :return: CustomInstruction.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not instruction_id:
            raise ValueError("instruction_id must not be empty")
        url = (
            f"v3/style_rules/{style_rule}"
            f"/custom_instructions/{instruction_id}"
        )
        status, content, json = self._api_call(
            url,
            method="GET",
        )
        self._raise_for_status(status, content, json)
        return CustomInstruction.from_json(json)

    def update_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: str,
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
    ) -> CustomInstruction:
        """Updates a custom instruction.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param instruction_id: ID of the custom instruction.
        :param label: New label for the custom instruction.
        :param prompt: New prompt text for the custom instruction.
        :param source_language: Optional source language code.
        :return: Updated CustomInstruction.
        """
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
        request_data = {"label": label, "prompt": prompt}
        if source_language is not None:
            request_data["source_language"] = source_language
        url = (
            f"v3/style_rules/{style_rule}"
            f"/custom_instructions/{instruction_id}"
        )
        status, content, json = self._api_call(
            url,
            method="PUT",
            json=request_data,
        )
        self._raise_for_status(status, content, json)
        return CustomInstruction.from_json(json)

    def delete_style_rule_custom_instruction(
        self,
        style_rule: Union[str, StyleRuleInfo],
        instruction_id: str,
    ) -> None:
        """Deletes a custom instruction from a style rule.

        :param style_rule: Style rule ID string or StyleRuleInfo object.
        :param instruction_id: ID of the custom instruction to delete.
        """
        if isinstance(style_rule, StyleRuleInfo):
            style_rule = style_rule.style_id
        if not style_rule:
            raise ValueError("style_rule must not be empty")
        if not instruction_id:
            raise ValueError("instruction_id must not be empty")
        url = (
            f"v3/style_rules/{style_rule}"
            f"/custom_instructions/{instruction_id}"
        )
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
            endpoint += f"?{urllib.parse.urlencode(params)}"

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
            "v3/style_profiles", json=request_data
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
        # Entries replace keys of the same name set above.
        if extra_body_parameters:
            request_data.update(extra_body_parameters)
        return request_data

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
            query_string = urllib.parse.urlencode(params)
            endpoint += f"?{query_string}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)

        translation_memories = (
            json.get("translation_memories", [])
            if (json and isinstance(json, dict))
            else []
        )
        return [
            TranslationMemoryInfo.from_json(tm) for tm in translation_memories
        ]

    @staticmethod
    def _translation_memory_id(
        translation_memory: Union[str, TranslationMemoryInfo],
    ) -> str:
        if isinstance(translation_memory, TranslationMemoryInfo):
            translation_memory = translation_memory.translation_memory_id
        if not translation_memory:
            raise ValueError("translation_memory must not be empty")
        return translation_memory

    @staticmethod
    def _job_id(job: Union[str, TranslationMemoryJob]) -> str:
        if isinstance(job, TranslationMemoryJob):
            job = job.job_id
        if not job:
            raise ValueError("job must not be empty")
        return job

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
        return TranslationMemoryInfo.from_json(json)

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
            # quote_via=quote percent-encodes spaces in filter_text as %20.
            # urlencode defaults to quote_plus, which encodes them as "+" —
            # correct for a form body, but not for a URI query string.
            query_string = urllib.parse.urlencode(
                params, quote_via=urllib.parse.quote
            )
            endpoint += f"?{query_string}"

        status, content, json = self._api_call(endpoint, method="GET")
        self._raise_for_status(status, content, json)
        return TranslationMemorySegments.from_json(json)

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
    ) -> TranslationMemoryImport:
        """Creates an import job for a new translation memory.

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

        status, content, json = self._api_call(
            "v3/translation_memories/import", json=request_data
        )
        self._raise_for_status(status, content, json)
        return TranslationMemoryImport.from_json(json)

    def upload_translation_memory_file(
        self,
        translation_memory_import: Union[str, TranslationMemoryImport],
        input_file: Union[BinaryIO, bytes, Any],
        content_type: str = "application/xml",
    ) -> None:
        """Uploads a TMX file to the upload URL of an import job, which starts
        processing.

        :param translation_memory_import: TranslationMemoryImport returned by
            create_translation_memory_import(), or its upload URL.
        :param input_file: TMX file content as bytes or a file-like object
            opened in binary mode.
        :param content_type: (Optional) MIME type of the file. Must match the
            content_type declared when the import job was created.
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
        if hasattr(input_file, "read"):
            input_file = input_file.read()

        status_code, content = self._asset_call(
            "PUT",
            upload_url,
            data=input_file,
            headers={"Content-Type": content_type},
        )
        self._raise_for_asset_status(
            status_code, content, "uploading translation memory file"
        )

    def create_translation_memory_export(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
    ) -> TranslationMemoryExport:
        """Creates an export job for a translation memory.

        Poll get_translation_memory_job() for the download URL of the
        exported TMX file. Use export_translation_memory_to_filepath() to do
        both steps and write the file at once.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        :return: TranslationMemoryExport with the job ID.
        """
        tm_id = self._translation_memory_id(translation_memory)
        status, content, json = self._api_call(
            f"v3/translation_memories/{tm_id}/export"
        )
        self._raise_for_status(status, content, json)
        # 200 means the API reused a previously completed export, 202 that it
        # started a new one.
        return TranslationMemoryExport.from_json(
            json, reused_existing=(status == 200)
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
        return TranslationMemoryJob.from_json(json)

    def wait_until_translation_memory_job_done(
        self,
        job: Union[str, TranslationMemoryJob],
        timeout_s: Optional[int] = None,
    ) -> TranslationMemoryJob:
        """Polls a translation memory job until it finishes, sleeping between
        requests, and returns the final status.

        Note that an import job keeps reporting "awaiting_input" for a while
        after its file has been uploaded, because the API detects the upload
        asynchronously. That status is therefore polled through like any other
        non-terminal one. A job whose file is never uploaded does not finish on
        its own, so pass timeout_s when that is a possibility.

        :param job: Job ID string or TranslationMemoryJob object.
        :param timeout_s: (Optional) Maximum time to wait before raising an
            error. Note that this is not accurate to the second, but only
            polls every 5 seconds.
        :return: TranslationMemoryJob containing the status when finished.
        """
        job_id = self._job_id(job)
        status = self.get_translation_memory_job(job_id)
        start_time_s = time.time()
        while not status.done:
            if (
                timeout_s is not None
                and time.time() - start_time_s > timeout_s
            ):
                raise DeepLException(
                    f"Manual timeout of {timeout_s}s exceeded for"
                    + " translation memory job",
                    should_retry=False,
                )
            secs = 5.0
            util.log_info(
                f"Rechecking translation memory job status after sleeping "
                f"for {secs:.3f} seconds."
            )
            time.sleep(secs)
            status = self.get_translation_memory_job(job_id)
        return status

    def download_translation_memory_export(
        self,
        job: TranslationMemoryJob,
        output_file: Union[BinaryIO, Any, None] = None,
        chunk_size: int = _DOWNLOAD_CHUNK_SIZE,
    ) -> Optional[requests.Response]:
        """Downloads the TMX file of a completed export job.

        :param job: Completed export TranslationMemoryJob carrying the
            download URL.
        :param output_file: File-like object to store the downloaded TMX
            file. Omitting it is deprecated: the requests.Response is then
            returned instead, and iter_content() reads the streamed file data.
            In the next major version output_file will be required.
        :param chunk_size: (Optional) Size of chunk in bytes for streaming,
            default 64 KiB. Only used if output_file is specified.
        :return: None if output_file is specified, otherwise the
            requests.Response.
        """
        download_url = job.result.download_url if job.result else None
        if not download_url:
            raise ValueError(
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

        if output_file:
            for chunk in content.iter_content(chunk_size=chunk_size):
                output_file.write(chunk)
            return None
        _warn_download_without_output_file()
        return content

    def import_translation_memory_from_filepath(
        self,
        input_path: Union[os.PathLike, str],
        *,
        display_name: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> TranslationMemoryJob:
        """Imports a TMX file as a new translation memory: creates the import
        job, uploads the file, and waits for processing to finish.

        :param input_path: Path to the TMX file to import.
        :param display_name: (Optional) Name for the resulting translation
            memory, defaults to the file name.
        :param timeout_s: (Optional) Maximum time to wait for the import to
            finish. Note that this is not accurate to the second, but only
            polls every 5 seconds.
        :return: TranslationMemoryJob for the completed import; its result
            carries the new translation memory ID.

        :raises DeepLException: If the import fails.
        """
        file_path = pathlib.Path(input_path)
        if not file_path.exists():
            raise ValueError(f"file does not exist: {input_path}")

        created = self.create_translation_memory_import(
            file_name=file_path.name,
            content_length=file_path.stat().st_size,
            display_name=display_name,
        )
        with open(file_path, "rb") as input_file:
            self.upload_translation_memory_file(created, input_file)

        job = self.wait_until_translation_memory_job_done(
            created.job_id, timeout_s
        )
        if not job.ok:
            error_message = (
                job.result.error_message if job.result else None
            ) or "unknown error"
            raise DeepLException(
                "Error occurred while importing translation memory: "
                f"{error_message}"
            )
        return job

    def export_translation_memory_to_filepath(
        self,
        translation_memory: Union[str, TranslationMemoryInfo],
        output_path: Union[os.PathLike, str],
        *,
        timeout_s: Optional[int] = None,
    ) -> TranslationMemoryJob:
        """Exports a translation memory to a TMX file: creates the export job,
        waits for it to finish, and writes the result to output_path.

        :param translation_memory: Translation memory ID string or
            TranslationMemoryInfo object.
        :param output_path: Path to write the exported TMX file to.
        :param timeout_s: (Optional) Maximum time to wait for the export to
            finish. Note that this is not accurate to the second, but only
            polls every 5 seconds.
        :return: TranslationMemoryJob for the completed export.

        :raises DeepLException: If the export fails.
        """
        created = self.create_translation_memory_export(translation_memory)
        job = self.wait_until_translation_memory_job_done(
            created.job_id, timeout_s
        )
        if not job.ok:
            error_message = (
                job.result.error_message if job.result else None
            ) or "unknown error"
            raise DeepLException(
                "Error occurred while exporting translation memory: "
                f"{error_message}"
            )

        with open(output_path, "wb") as output_file:
            self.download_translation_memory_export(
                job, output_file, chunk_size=8192
            )
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
        DeepL Authorization header is deliberately not sent.
        """
        util.log_info("Request to storage URL", method=method, url=url)
        return self._client.request_with_backoff(
            method,
            url,
            data=data,
            json=None,
            headers=dict(headers or {}),
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
        detail = content if isinstance(content, str) else ""
        message = f"Error {action}, HTTP status: {status_code}"
        if detail:
            message += f", detail: {detail}"
        raise DeepLException(
            message, should_retry=False, http_status_code=status_code
        )
