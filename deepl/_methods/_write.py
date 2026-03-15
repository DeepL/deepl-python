# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import urllib.parse
from typing import Iterable, List, Optional, Tuple, Union

from ..exceptions import DeepLException
from ..api_data import Language, WriteResult
from .._http_types import HttpRequest, HttpResponse


def _build_rephrase_text_request(
    server_url: str,
    text: Union[str, Iterable[str]],
    *,
    target_lang: Union[None, str, Language] = None,
    style: Optional[str] = None,
    tone: Optional[str] = None,
) -> Tuple[HttpRequest, bool]:
    """Build a POST /v2/write/rephrase request.

    Returns (request, multi_input).
    """
    if isinstance(text, str):
        if len(text) == 0:
            raise ValueError("text must not be empty")
        text_list = [text]
        multi_input = False
    elif hasattr(text, "__iter__"):
        multi_input = True
        text_list = list(text)
    else:
        raise TypeError(
            "text parameter must be a string or an iterable of strings"
        )

    target_lang_str: Optional[str] = (
        str(target_lang) if target_lang is not None else None
    )
    request_data: dict = {"text": text_list}
    if target_lang_str:
        request_data["target_lang"] = target_lang_str
    if style:
        request_data["writing_style"] = style
    if tone:
        request_data["tone"] = tone

    body = json_module.dumps(request_data).encode("utf-8")
    return (
        HttpRequest(
            method="POST",
            url=urllib.parse.urljoin(server_url, "v2/write/rephrase"),
            headers={"Content-Type": "application/json"},
            body=body,
        ),
        multi_input,
    )


def _parse_rephrase_text_response(
    response: HttpResponse,
    multi_input: bool,
) -> Union[WriteResult, List[WriteResult]]:
    json_data = json_module.loads(response.content)
    improvements = (
        json_data.get("improvements", [])
        if isinstance(json_data, dict)
        else []
    )
    output = []
    for improvement in improvements:
        text = improvement.get("text", "") if improvement else ""
        detected_source_language = (
            improvement.get("detected_source_language", "")
            if improvement
            else ""
        )
        target_language = (
            improvement.get("target_language", "") if improvement else ""
        )
        output.append(
            WriteResult(text, detected_source_language, target_language)
        )
    if not output and not multi_input:
        raise DeepLException("Unexpected empty improvements in API response")
    return output if multi_input else output[0]
