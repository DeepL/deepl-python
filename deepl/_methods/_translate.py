# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ..exceptions import DeepLException
from ..api_data import (
    Formality,
    GlossaryInfo,
    Language,
    ModelType,
    MultilingualGlossaryInfo,
    SplitSentences,
    StyleRuleInfo,
    TextResult,
    TranslationMemoryInfo,
)
from .._client_base import _check_language_and_formality
from .._http_types import HttpRequest, HttpResponse


def _join_tags(tag_argument: Union[str, Iterable[str]]) -> List[str]:
    if isinstance(tag_argument, str):
        tag_argument = [tag_argument]
    return [
        tag for arg_string in tag_argument for tag in arg_string.split(",")
    ]


def _build_translate_text_request(
    server_url: str,
    text: Union[str, Iterable[str]],
    *,
    target_lang: Union[str, Language],
    source_lang: Union[str, Language, None] = None,
    context: Optional[str] = None,
    split_sentences: Union[str, SplitSentences, None] = None,
    preserve_formatting: Optional[bool] = None,
    formality: Union[str, Formality, None] = None,
    glossary: Union[str, GlossaryInfo, MultilingualGlossaryInfo, None] = None,
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
) -> Tuple[HttpRequest, bool]:
    """Build a POST /v2/translate request.

    Returns (request, multi_input) where multi_input is True if ``text`` was
    an iterable (so the caller knows whether to unwrap the single result).
    """
    if isinstance(text, str):
        if len(text) == 0:
            raise ValueError("text must not be empty")
        text_list = [text]
        multi_input = False
    elif hasattr(text, "__iter__"):
        multi_input = True
        text_list = list(text)
        if len(text_list) == 0:
            raise ValueError("text must not be empty")
    else:
        raise TypeError(
            "text parameter must be a string or an iterable of strings"
        )

    request_data: Dict[str, Any] = _check_language_and_formality(
        source_lang, target_lang, formality, glossary, style_rule
    )
    request_data["text"] = text_list
    request_data["show_billed_characters"] = True
    if isinstance(translation_memory, TranslationMemoryInfo):
        request_data["translation_memory_id"] = (
            translation_memory.translation_memory_id
        )
    elif translation_memory is not None:
        request_data["translation_memory_id"] = translation_memory
    if translation_memory_threshold is not None:
        if translation_memory is None:
            raise ValueError(
                "translation_memory_threshold requires translation_memory"
            )
        if not (0 <= translation_memory_threshold <= 100):
            raise ValueError(
                "translation_memory_threshold must be between 0 and 100"
            )
        request_data["translation_memory_threshold"] = (
            translation_memory_threshold
        )

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

    if non_splitting_tags is not None:
        request_data["non_splitting_tags"] = _join_tags(non_splitting_tags)
    if splitting_tags is not None:
        request_data["splitting_tags"] = _join_tags(splitting_tags)
    if ignore_tags is not None:
        request_data["ignore_tags"] = _join_tags(ignore_tags)
    if custom_instructions is not None:
        request_data["custom_instructions"] = custom_instructions
    if extra_body_parameters:
        request_data.update(extra_body_parameters)

    body = json_module.dumps(request_data).encode("utf-8")
    return (
        HttpRequest(
            method="POST",
            url=urllib.parse.urljoin(server_url, "v2/translate"),
            headers={"Content-Type": "application/json"},
            body=body,
        ),
        multi_input,
    )


def _parse_translate_text_response(
    response: HttpResponse,
    multi_input: bool,
) -> Union[TextResult, List[TextResult]]:
    json_data = json_module.loads(response.content)
    translations = (
        json_data.get("translations", [])
        if isinstance(json_data, dict)
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
        billed_characters = int(translation.get("billed_characters", 0))
        model_type_used = translation.get("model_type_used")
        output.append(
            TextResult(
                text,
                detected_source_language,
                billed_characters,
                model_type_used,
            )
        )
    if not output and not multi_input:
        raise DeepLException("Unexpected empty translations in API response")
    return output if multi_input else output[0]


def _build_list_translation_memories_request(
    server_url: str,
    *,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> HttpRequest:
    """Build a GET /v3/translation_memories request."""
    params: Dict[str, str] = {}
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["page_size"] = str(page_size)
    url = urllib.parse.urljoin(server_url, "v3/translation_memories")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return HttpRequest(method="GET", url=url)


def _parse_list_translation_memories_response(
    response: HttpResponse,
) -> List[TranslationMemoryInfo]:
    json_data = json_module.loads(response.content)
    memories = (
        json_data.get("translation_memories", [])
        if isinstance(json_data, dict)
        else []
    )
    return [TranslationMemoryInfo.from_json(m) for m in memories]
