# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import pytest

from .client import make_translator, url


@pytest.mark.parametrize(
    "status, error, message, should_retry",
    [
        (300, deepl.DeepLException, "Unexpected status code: 300", False),
        (304, deepl.DeepLException, "Unexpected status code: 304", False),
        (400, deepl.DeepLException, "Bad request", False),
        (401, deepl.AuthorizationException, "Authorization failure", False),
        (403, deepl.AuthorizationException, "Authorization failure", False),
        (404, deepl.NotFoundException, "Not found", False),
        (413, deepl.DeepLException, "Unexpected status code: 413", False),
        (
            429,
            deepl.TooManyRequestsException,
            "Too many requests",
            True,
        ),
        (
            456,
            deepl.QuotaExceededException,
            "Quota for this billing period has been exceeded",
            False,
        ),
        (500, deepl.DeepLException, "Unexpected status code: 500", True),
        (502, deepl.DeepLException, "Unexpected status code: 502", True),
        (503, deepl.DeepLException, "Service unavailable", True),
        (
            599,
            deepl.DeepLException,
            "Unexpected status code: 599 Unknown",
            True,
        ),
    ],
)
def test_raises_exception_for_status_code(
    mocked, no_retries, status, error, message, should_retry
):
    mocked.get(url("v2/usage"), status=status)

    with pytest.raises(error, match=message) as exc_info:
        make_translator().get_usage()

    assert type(exc_info.value) is error
    assert exc_info.value.http_status_code == status
    assert exc_info.value.should_retry is should_retry


def test_appends_message_and_detail_of_error_reply(mocked):
    mocked.get(
        url("v2/usage"),
        status=400,
        json={"message": "bad value", "detail": "field x"},
    )

    with pytest.raises(deepl.DeepLException) as exc_info:
        make_translator().get_usage()

    assert str(exc_info.value) == (
        "Bad request, message: bad value, detail: field x"
    )


@pytest.mark.parametrize(
    "reply, expected",
    [
        ({"message": None, "detail": 7}, "Bad request, detail: 7"),
        (
            {"message": {"code": 1}, "detail": ["a"]},
            'Bad request, message: {"code": 1}, detail: ["a"]',
        ),
    ],
)
def test_formats_non_string_message_and_detail_of_error_reply(
    mocked, reply, expected
):
    mocked.get(url("v2/usage"), status=400, json=reply)

    with pytest.raises(deepl.DeepLException) as exc_info:
        make_translator().get_usage()

    assert str(exc_info.value) == expected


def test_ignores_error_reply_that_is_not_json(mocked):
    mocked.get(url("v2/usage"), status=400, body="<html>nope</html>")

    with pytest.raises(deepl.DeepLException) as exc_info:
        make_translator().get_usage()

    assert str(exc_info.value) == "Bad request"


def test_includes_reply_content_for_unexpected_status(mocked):
    mocked.get(url("v2/usage"), status=418, body="teapot")

    with pytest.raises(deepl.DeepLException, match="content: teapot"):
        make_translator().get_usage()
