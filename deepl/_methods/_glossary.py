# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import urllib.parse
from typing import Dict, List, Optional, Union

from ..api_data import (
    GlossaryInfo,
    Language,
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryDictionaryEntriesResponse,
    MultilingualGlossaryDictionaryInfo,
    MultilingualGlossaryInfo,
)
from .._http_types import HttpRequest, HttpResponse
from .. import util


def _safe_id(glossary_id: str) -> str:
    """URL-encode a glossary/document ID for safe path interpolation."""
    return urllib.parse.quote(glossary_id, safe="")


# ---------------------------------------------------------------------------
# Classic (v2) glossary operations
# ---------------------------------------------------------------------------


def _build_create_glossary_request(
    server_url: str,
    name: str,
    source_lang: Union[str, Language],
    target_lang: Union[str, Language],
    entries_format: str,
    entries: Union[str, bytes],
) -> HttpRequest:
    source_lang_str = Language.remove_regional_variant(source_lang)
    target_lang_str = Language.remove_regional_variant(target_lang)
    if not name:
        raise ValueError("glossary name must not be empty")
    request_data: dict = {
        "name": name,
        "source_lang": source_lang_str,
        "target_lang": target_lang_str,
        "entries_format": entries_format,
        "entries": entries if isinstance(entries, str) else entries.decode(),
    }
    body = json_module.dumps(request_data).encode("utf-8")
    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(server_url, "v2/glossaries"),
        headers={"Content-Type": "application/json"},
        body=body,
    )


def _parse_create_glossary_response(response: HttpResponse) -> GlossaryInfo:
    json_data = json_module.loads(response.content)
    return GlossaryInfo.from_json(json_data)


def _build_get_glossary_request(
    server_url: str, glossary: Union[str, GlossaryInfo]
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, GlossaryInfo)
        else glossary
    )
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, f"v2/glossaries/{glossary_id}"),
    )


def _parse_get_glossary_response(response: HttpResponse) -> GlossaryInfo:
    json_data = json_module.loads(response.content)
    return GlossaryInfo.from_json(json_data)


def _build_list_glossaries_request(server_url: str) -> HttpRequest:
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, "v2/glossaries"),
    )


def _parse_list_glossaries_response(
    response: HttpResponse,
) -> List[GlossaryInfo]:
    json_data = json_module.loads(response.content)
    glossaries = (
        json_data.get("glossaries", []) if isinstance(json_data, dict) else []
    )
    return [GlossaryInfo.from_json(g) for g in glossaries]


def _build_get_glossary_entries_request(
    server_url: str, glossary: Union[str, GlossaryInfo]
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, GlossaryInfo)
        else glossary
    )
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(
            server_url, f"v2/glossaries/{glossary_id}/entries"
        ),
        headers={"Accept": "text/tab-separated-values"},
    )


def _parse_get_glossary_entries_response(response: HttpResponse) -> dict:
    content_str = response.content.decode("utf-8")
    return util.convert_tsv_to_dict(content_str)


def _build_delete_glossary_request(
    server_url: str, glossary: Union[str, GlossaryInfo]
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, GlossaryInfo)
        else glossary
    )
    return HttpRequest(
        method="DELETE",
        url=urllib.parse.urljoin(server_url, f"v2/glossaries/{glossary_id}"),
    )


# ---------------------------------------------------------------------------
# Multilingual (v3) glossary operations
# ---------------------------------------------------------------------------


def _build_create_multilingual_glossary_request(
    server_url: str,
    name: str,
    glossary_dicts: List[MultilingualGlossaryDictionaryEntries],
) -> HttpRequest:
    if not name:
        raise ValueError("glossary name must not be empty")
    req_dicts = [
        {
            "source_lang": Language.remove_regional_variant(d.source_lang),
            "target_lang": Language.remove_regional_variant(d.target_lang),
            "entries": util.convert_dict_to_tsv(d.entries),
            "entries_format": "tsv",
        }
        for d in glossary_dicts
    ]
    body = json_module.dumps({"name": name, "dictionaries": req_dicts}).encode(
        "utf-8"
    )
    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(server_url, "v3/glossaries"),
        headers={"Content-Type": "application/json"},
        body=body,
    )


def _parse_multilingual_glossary_response(
    response: HttpResponse,
) -> MultilingualGlossaryInfo:
    json_data = json_module.loads(response.content)
    return MultilingualGlossaryInfo.from_json(json_data)


def _build_update_multilingual_glossary_name_request(
    server_url: str, glossary: Union[str, MultilingualGlossaryInfo], name: str
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    if not name:
        raise ValueError("glossary name must not be empty")
    if not glossary_id:
        raise ValueError("glossary id must not be empty")
    body = json_module.dumps({"name": name}).encode("utf-8")
    return HttpRequest(
        method="PATCH",
        url=urllib.parse.urljoin(server_url, f"v3/glossaries/{glossary_id}"),
        headers={"Content-Type": "application/json"},
        body=body,
    )


def _build_update_multilingual_glossary_dict_request(
    server_url: str,
    glossary: Union[str, MultilingualGlossaryInfo],
    dictionaries: List[MultilingualGlossaryDictionaryEntries],
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    if not glossary_id:
        raise ValueError("glossary id must not be empty")
    req_dicts = [
        {
            "source_lang": Language.remove_regional_variant(d.source_lang),
            "target_lang": Language.remove_regional_variant(d.target_lang),
            "entries": util.convert_dict_to_tsv(d.entries),
            "entries_format": "tsv",
        }
        for d in dictionaries
    ]
    body = json_module.dumps({"dictionaries": req_dicts}).encode("utf-8")
    return HttpRequest(
        method="PATCH",
        url=urllib.parse.urljoin(server_url, f"v3/glossaries/{glossary_id}"),
        headers={"Content-Type": "application/json"},
        body=body,
    )


def _build_replace_multilingual_glossary_dict_request(
    server_url: str,
    glossary: Union[str, MultilingualGlossaryInfo],
    source_lang: str,
    target_lang: str,
    entries: Dict[str, str],
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    if not glossary_id:
        raise ValueError("glossary id must not be empty")
    request_data = {
        "source_lang": Language.remove_regional_variant(source_lang),
        "target_lang": Language.remove_regional_variant(target_lang),
        "entries": util.convert_dict_to_tsv(entries),
        "entries_format": "tsv",
    }
    body = json_module.dumps(request_data).encode("utf-8")
    return HttpRequest(
        method="PUT",
        url=urllib.parse.urljoin(
            server_url, f"v3/glossaries/{glossary_id}/dictionaries"
        ),
        headers={"Content-Type": "application/json"},
        body=body,
    )


def _parse_multilingual_glossary_dict_response(
    response: HttpResponse,
) -> MultilingualGlossaryDictionaryInfo:
    json_data = json_module.loads(response.content)
    return MultilingualGlossaryDictionaryInfo.from_json(json_data)


def _build_get_multilingual_glossary_request(
    server_url: str, glossary: Union[str, MultilingualGlossaryInfo]
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, f"v3/glossaries/{glossary_id}"),
    )


def _build_list_multilingual_glossaries_request(
    server_url: str,
) -> HttpRequest:
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, "v3/glossaries"),
    )


def _parse_list_multilingual_glossaries_response(
    response: HttpResponse,
) -> List[MultilingualGlossaryInfo]:
    json_data = json_module.loads(response.content)
    glossaries = (
        json_data.get("glossaries", []) if isinstance(json_data, dict) else []
    )
    return [MultilingualGlossaryInfo.from_json(g) for g in glossaries]


def _build_get_multilingual_glossary_entries_request(
    server_url: str,
    glossary: Union[str, MultilingualGlossaryInfo],
    source_lang: str,
    target_lang: str,
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    source_lang = Language.remove_regional_variant(source_lang)
    target_lang = Language.remove_regional_variant(target_lang)
    url = urllib.parse.urljoin(
        server_url,
        f"v3/glossaries/{glossary_id}/entries"
        f"?source_lang={source_lang}&target_lang={target_lang}",
    )
    return HttpRequest(method="GET", url=url)


def _parse_multilingual_glossary_entries_response(
    response: HttpResponse,
) -> MultilingualGlossaryDictionaryEntriesResponse:
    json_data = json_module.loads(response.content)
    return MultilingualGlossaryDictionaryEntriesResponse.from_json(json_data)


def _build_delete_multilingual_glossary_request(
    server_url: str, glossary: Union[str, MultilingualGlossaryInfo]
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    return HttpRequest(
        method="DELETE",
        url=urllib.parse.urljoin(server_url, f"v3/glossaries/{glossary_id}"),
    )


def _build_delete_multilingual_glossary_dict_request(
    server_url: str,
    glossary: Union[str, MultilingualGlossaryInfo],
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    dictionary: Optional[MultilingualGlossaryDictionaryInfo] = None,
) -> HttpRequest:
    glossary_id = _safe_id(
        glossary.glossary_id
        if isinstance(glossary, MultilingualGlossaryInfo)
        else glossary
    )
    if dictionary is not None:
        source_lang = dictionary.source_lang
        target_lang = dictionary.target_lang
    if not source_lang or not target_lang:
        raise ValueError(
            "must provide dictionary or both source_lang and target_lang"
        )
    source_lang = Language.remove_regional_variant(source_lang)
    target_lang = Language.remove_regional_variant(target_lang)
    qs = urllib.parse.urlencode(
        {"source_lang": source_lang, "target_lang": target_lang}
    )
    url = urllib.parse.urljoin(
        server_url,
        f"v3/glossaries/{glossary_id}/dictionaries?{qs}",
    )
    return HttpRequest(method="DELETE", url=url)
