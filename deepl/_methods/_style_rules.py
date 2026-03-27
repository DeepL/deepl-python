# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import urllib.parse
from typing import Dict, List, Optional

from ..api_data import CustomInstruction, StyleRuleInfo
from .._http_types import HttpRequest, HttpResponse


def _safe_id(style_rule_id: str) -> str:
    """URL-encode a style rule or instruction ID for safe interpolation."""
    return urllib.parse.quote(style_rule_id, safe="")


def _build_get_style_rules_request(
    server_url: str,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    detailed: Optional[bool] = None,
) -> HttpRequest:
    params = {}
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["page_size"] = str(page_size)
    if detailed is not None:
        params["detailed"] = str(detailed).lower()

    endpoint = "v3/style_rules"
    if params:
        endpoint += "?" + urllib.parse.urlencode(params)

    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, endpoint),
    )


def _parse_get_style_rules_response(
    response: HttpResponse,
) -> List[StyleRuleInfo]:
    json_data = json_module.loads(response.content)
    style_rules = (
        json_data.get("style_rules", []) if isinstance(json_data, dict) else []
    )
    return [StyleRuleInfo.from_json(rule) for rule in style_rules]


def _build_create_style_rule_request(
    server_url: str,
    name: str,
    language: str,
    configured_rules: Optional[dict] = None,
    custom_instructions: Optional[List[dict]] = None,
) -> HttpRequest:
    request_data: Dict = {"name": name, "language": language}
    if configured_rules is not None:
        request_data["configured_rules"] = configured_rules
    if custom_instructions is not None:
        request_data["custom_instructions"] = custom_instructions
    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(server_url, "v3/style_rules"),
        body=json_module.dumps(request_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def _parse_style_rule_response(response: HttpResponse) -> StyleRuleInfo:
    json_data = json_module.loads(response.content)
    return StyleRuleInfo.from_json(json_data)


def _build_get_style_rule_request(
    server_url: str,
    style_rule_id: str,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, f"v3/style_rules/{sid}"),
    )


def _build_update_style_rule_name_request(
    server_url: str,
    style_rule_id: str,
    name: str,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    body = json_module.dumps({"name": name}).encode("utf-8")
    return HttpRequest(
        method="PATCH",
        url=urllib.parse.urljoin(server_url, f"v3/style_rules/{sid}"),
        body=body,
        headers={"Content-Type": "application/json"},
    )


def _build_delete_style_rule_request(
    server_url: str,
    style_rule_id: str,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    return HttpRequest(
        method="DELETE",
        url=urllib.parse.urljoin(server_url, f"v3/style_rules/{sid}"),
    )


def _build_update_style_rule_configured_rules_request(
    server_url: str,
    style_rule_id: str,
    configured_rules: dict,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    body = json_module.dumps(configured_rules).encode("utf-8")
    return HttpRequest(
        method="PUT",
        url=urllib.parse.urljoin(
            server_url,
            f"v3/style_rules/{sid}/configured_rules",
        ),
        body=body,
        headers={"Content-Type": "application/json"},
    )


def _build_create_style_rule_custom_instruction_request(
    server_url: str,
    style_rule_id: str,
    label: str,
    prompt: str,
    source_language: Optional[str] = None,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    request_data: Dict = {"label": label, "prompt": prompt}
    if source_language is not None:
        request_data["source_language"] = source_language
    body = json_module.dumps(request_data).encode("utf-8")
    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(
            server_url,
            f"v3/style_rules/{sid}/custom_instructions",
        ),
        body=body,
        headers={"Content-Type": "application/json"},
    )


def _parse_custom_instruction_response(
    response: HttpResponse,
) -> CustomInstruction:
    json_data = json_module.loads(response.content)
    return CustomInstruction.from_json(json_data)


def _build_get_style_rule_custom_instruction_request(
    server_url: str,
    style_rule_id: str,
    instruction_id: str,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    iid = _safe_id(instruction_id)
    path = f"v3/style_rules/{sid}/custom_instructions/{iid}"
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, path),
    )


def _build_update_style_rule_custom_instruction_request(
    server_url: str,
    style_rule_id: str,
    instruction_id: str,
    label: str,
    prompt: str,
    source_language: Optional[str] = None,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    iid = _safe_id(instruction_id)
    request_data: Dict = {"label": label, "prompt": prompt}
    if source_language is not None:
        request_data["source_language"] = source_language
    body = json_module.dumps(request_data).encode("utf-8")
    path = f"v3/style_rules/{sid}/custom_instructions/{iid}"
    return HttpRequest(
        method="PUT",
        url=urllib.parse.urljoin(server_url, path),
        body=body,
        headers={"Content-Type": "application/json"},
    )


def _build_delete_style_rule_custom_instruction_request(
    server_url: str,
    style_rule_id: str,
    instruction_id: str,
) -> HttpRequest:
    sid = _safe_id(style_rule_id)
    iid = _safe_id(instruction_id)
    path = f"v3/style_rules/{sid}/custom_instructions/{iid}"
    return HttpRequest(
        method="DELETE",
        url=urllib.parse.urljoin(server_url, path),
    )
