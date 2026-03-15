# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import urllib.parse

from ..api_data import Usage
from .._http_types import HttpRequest, HttpResponse


def _build_get_usage_request(server_url: str) -> HttpRequest:
    return HttpRequest(
        method="GET",
        url=urllib.parse.urljoin(server_url, "v2/usage"),
    )


def _parse_get_usage_response(response: HttpResponse) -> Usage:
    json_data = json_module.loads(response.content)
    if not isinstance(json_data, dict):
        json_data = {}
    return Usage(json_data)
