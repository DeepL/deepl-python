# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import urllib.parse
from typing import List

from ..api_data import GlossaryLanguagePair, Language
from .._http_types import HttpRequest, HttpResponse


def _build_get_source_languages_request(server_url: str) -> HttpRequest:
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, "v2/languages"),
    )


def _build_get_target_languages_request(server_url: str) -> HttpRequest:
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, "v2/languages?type=target"),
    )


def _parse_get_source_languages_response(
    response: HttpResponse,
) -> List[Language]:
    json_data = json_module.loads(response.content)
    languages = json_data if isinstance(json_data, list) else []
    return [Language(lang["language"], lang["name"]) for lang in languages]


def _parse_get_target_languages_response(
    response: HttpResponse,
) -> List[Language]:
    json_data = json_module.loads(response.content)
    languages = json_data if isinstance(json_data, list) else []
    return [
        Language(
            lang["language"],
            lang["name"],
            lang.get("supports_formality", None),
        )
        for lang in languages
    ]


def _build_get_glossary_languages_request(server_url: str) -> HttpRequest:
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, "v2/glossary-language-pairs"),
    )


def _parse_get_glossary_languages_response(
    response: HttpResponse,
) -> List[GlossaryLanguagePair]:
    json_data = json_module.loads(response.content)
    supported = (
        json_data.get("supported_languages", [])
        if isinstance(json_data, dict)
        else []
    )
    return [
        GlossaryLanguagePair(p["source_lang"], p["target_lang"])
        for p in supported
    ]
