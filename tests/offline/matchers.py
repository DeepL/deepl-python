# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from responses import matchers

from .client import AUTH_HEADER


def json_request(body):
    """Matches a request with the DeepL authorization header and exactly the
    given JSON body."""
    return [
        matchers.header_matcher(
            {
                "Authorization": AUTH_HEADER,
                "Content-Type": "application/json",
            }
        ),
        matchers.json_params_matcher(body),
    ]


def bodyless_request(query=None):
    """Matches a request with the DeepL authorization header, exactly the
    given query parameters and no body."""
    return [
        matchers.header_matcher({"Authorization": AUTH_HEADER}),
        matchers.query_param_matcher(query or {}),
        _no_body,
    ]


def _no_body(request):
    if request.body:
        return False, f"unexpected body: {request.body!r}"
    return True, ""


def multipart_request(files, data=None):
    """Matches a request with the DeepL authorization header and exactly the
    given multipart form fields, in order, followed by the files."""
    return [
        matchers.header_matcher({"Authorization": AUTH_HEADER}),
        matchers.multipart_matcher(files, data=data),
    ]


def storage_request(content_type=None, body=None):
    """Matches a request to a pre-signed storage URL: no DeepL authorization
    header, the given content type and the given body (or no body)."""
    expected = [_no_authorization]
    if content_type is not None:
        expected.append(
            matchers.header_matcher({"Content-Type": content_type})
        )
    expected.append(matchers.body_matcher(body) if body else _no_body)
    return expected


def _no_authorization(request):
    if "Authorization" in request.headers:
        return False, "storage requests must not carry the DeepL key"
    return True, ""
