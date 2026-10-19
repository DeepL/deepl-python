# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import pytest
import requests  # type: ignore

from .client import make_translator, url
from .matchers import bodyless_request

USAGE_JSON = {"character_count": 1, "character_limit": 2}


@pytest.mark.parametrize("status", [429, 503])
def test_retries_request_after_retryable_status(mocked, status):
    mocked.get(url("v2/usage"), status=status)
    mocked.get(url("v2/usage"), json=USAGE_JSON, match=bodyless_request())

    make_translator().get_usage()

    assert len(mocked.calls) == 2


def test_retries_request_after_connection_error(mocked):
    mocked.get(
        url("v2/usage"), body=requests.exceptions.ConnectionError("reset")
    )
    mocked.get(url("v2/usage"), json=USAGE_JSON)

    make_translator().get_usage()

    assert len(mocked.calls) == 2


def test_retries_request_after_timeout(mocked):
    mocked.get(url("v2/usage"), body=requests.exceptions.ReadTimeout("slow"))
    mocked.get(url("v2/usage"), json=USAGE_JSON)

    make_translator().get_usage()

    assert len(mocked.calls) == 2


def test_stops_retrying_after_max_network_retries(mocked, monkeypatch):
    monkeypatch.setattr(deepl.http_client, "max_network_retries", 1)
    mocked.get(url("v2/usage"), status=500)
    mocked.get(url("v2/usage"), status=500)

    with pytest.raises(deepl.DeepLException, match="Unexpected status code"):
        make_translator().get_usage()

    assert len(mocked.calls) == 2


def test_raises_connection_exception_for_timeout_without_retries(
    mocked, no_retries
):
    mocked.get(url("v2/usage"), body=requests.exceptions.ReadTimeout("slow"))

    with pytest.raises(
        deepl.ConnectionException, match="Request timed out: slow"
    ) as exc_info:
        make_translator().get_usage()

    assert exc_info.value.should_retry


def test_raises_connection_exception_for_connection_error_without_retries(
    mocked, no_retries
):
    mocked.get(url("v2/usage"), body=requests.exceptions.ConnectionError("x"))

    with pytest.raises(
        deepl.ConnectionException, match="Connection failed: x"
    ) as exc_info:
        make_translator().get_usage()

    assert exc_info.value.should_retry


def test_does_not_retry_other_request_exceptions(mocked):
    mocked.get(url("v2/usage"), body=requests.exceptions.InvalidHeader("bad"))

    with pytest.raises(
        deepl.ConnectionException, match="Request failed: bad"
    ) as exc_info:
        make_translator().get_usage()

    assert not exc_info.value.should_retry
    assert len(mocked.calls) == 1


def test_does_not_retry_unexpected_exceptions(mocked):
    mocked.get(url("v2/usage"), body=RuntimeError("boom"))

    with pytest.raises(
        deepl.ConnectionException, match="Unexpected request failure: boom"
    ) as exc_info:
        make_translator().get_usage()

    assert not exc_info.value.should_retry
    assert len(mocked.calls) == 1


def test_does_not_retry_client_errors(mocked):
    mocked.get(url("v2/usage"), status=400)

    with pytest.raises(deepl.DeepLException, match="Bad request"):
        make_translator().get_usage()

    assert len(mocked.calls) == 1
