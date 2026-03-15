# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

"""Unit tests for DeepLClient retry/error-mapping logic using MockHttpClient.

These tests run without any network access and without real sleeping.
"""

import pytest
import deepl
from deepl.exceptions import (
    AuthorizationException,
    ConnectionException,
    QuotaExceededException,
    TooManyRequestsException,
    DeepLException,
)
from deepl.retry_config import RetryConfig
from .mock_http_client import MockHttpClient


AUTH_KEY = "test-auth-key:fx"
TRANSLATE_RESPONSE = {
    "translations": [
        {
            "detected_source_language": "EN",
            "text": "Protonstrahlen",
            "billed_characters": 11,
        }
    ]
}
USAGE_RESPONSE = {
    "character_count": 0,
    "character_limit": 100,
}


def _make_client(
    mock: MockHttpClient, max_retries: int = 3
) -> deepl.DeepLClient:
    """Return a DeepLClient backed by mock with sleep disabled."""
    config = RetryConfig(max_retries=max_retries)
    client = deepl.DeepLClient(
        AUTH_KEY,
        http_client=mock,
        retry_config=config,
        _sleep_fn=lambda _: None,
    )
    return client


# ---------------------------------------------------------------------------
# Basic success
# ---------------------------------------------------------------------------


def test_success_on_first_attempt():
    mock = MockHttpClient()
    mock.push(MockHttpClient.ok_response(USAGE_RESPONSE))
    client = _make_client(mock)
    usage = client.get_usage()
    assert usage.character.count == 0
    assert len(mock.calls) == 1


# ---------------------------------------------------------------------------
# ConnectionException retries
# ---------------------------------------------------------------------------


def test_retries_on_retryable_connection_error():
    mock = MockHttpClient()
    mock.push(
        MockHttpClient.connection_error(should_retry=True),
        MockHttpClient.connection_error(should_retry=True),
        MockHttpClient.ok_response(USAGE_RESPONSE),
    )
    client = _make_client(mock, max_retries=3)
    usage = client.get_usage()
    assert usage.character.count == 0
    assert len(mock.calls) == 3


def test_no_retry_on_non_retryable_connection_error():
    mock = MockHttpClient()
    mock.push(MockHttpClient.connection_error(should_retry=False))
    client = _make_client(mock)
    with pytest.raises(ConnectionException):
        client.get_usage()
    assert len(mock.calls) == 1


def test_exhausts_retries_on_persistent_connection_error():
    max_retries = 2
    mock = MockHttpClient()
    for _ in range(max_retries + 1):
        mock.push(MockHttpClient.connection_error(should_retry=True))
    client = _make_client(mock, max_retries=max_retries)
    with pytest.raises(ConnectionException):
        client.get_usage()
    # 1 initial attempt + max_retries retries
    assert len(mock.calls) == max_retries + 1


# ---------------------------------------------------------------------------
# HTTP 429 retries
# ---------------------------------------------------------------------------


def test_retries_on_429():
    mock = MockHttpClient()
    mock.push(
        MockHttpClient.status_response(429),
        MockHttpClient.ok_response(USAGE_RESPONSE),
    )
    client = _make_client(mock, max_retries=3)
    usage = client.get_usage()
    assert usage.character.count == 0
    assert len(mock.calls) == 2


def test_exhausts_retries_on_persistent_429():
    max_retries = 2
    mock = MockHttpClient()
    for _ in range(max_retries + 1):
        mock.push(MockHttpClient.status_response(429))
    client = _make_client(mock, max_retries=max_retries)
    with pytest.raises(TooManyRequestsException):
        client.get_usage()
    assert len(mock.calls) == max_retries + 1


# ---------------------------------------------------------------------------
# HTTP 5xx retries
# ---------------------------------------------------------------------------


def test_retries_on_503():
    mock = MockHttpClient()
    mock.push(
        MockHttpClient.status_response(503),
        MockHttpClient.ok_response(USAGE_RESPONSE),
    )
    client = _make_client(mock, max_retries=3)
    usage = client.get_usage()
    assert usage.character.count == 0
    assert len(mock.calls) == 2


def test_retries_on_500():
    mock = MockHttpClient()
    mock.push(
        MockHttpClient.status_response(500),
        MockHttpClient.status_response(500),
        MockHttpClient.ok_response(USAGE_RESPONSE),
    )
    client = _make_client(mock, max_retries=3)
    client.get_usage()
    assert len(mock.calls) == 3


def test_exhausts_retries_on_persistent_500():
    max_retries = 2
    mock = MockHttpClient()
    for _ in range(max_retries + 1):
        mock.push(MockHttpClient.status_response(500))
    client = _make_client(mock, max_retries=max_retries)
    with pytest.raises(DeepLException):
        client.get_usage()
    assert len(mock.calls) == max_retries + 1


# ---------------------------------------------------------------------------
# No retry on 4xx error codes
# ---------------------------------------------------------------------------


def test_no_retry_on_403():
    mock = MockHttpClient()
    mock.push(MockHttpClient.status_response(403))
    client = _make_client(mock)
    with pytest.raises(AuthorizationException):
        client.get_usage()
    assert len(mock.calls) == 1


def test_no_retry_on_456_quota_exceeded():
    mock = MockHttpClient()
    mock.push(MockHttpClient.status_response(456))
    client = _make_client(mock)
    with pytest.raises(QuotaExceededException):
        client.get_usage()
    assert len(mock.calls) == 1


def test_no_retry_on_400():
    mock = MockHttpClient()
    mock.push(MockHttpClient.status_response(400, "Bad request"))
    client = _make_client(mock)
    with pytest.raises(DeepLException):
        client.get_usage()
    assert len(mock.calls) == 1


# ---------------------------------------------------------------------------
# Sleep injection
# ---------------------------------------------------------------------------


def test_sleep_called_on_retry():
    sleep_calls = []
    mock = MockHttpClient()
    mock.push(
        MockHttpClient.connection_error(should_retry=True),
        MockHttpClient.ok_response(USAGE_RESPONSE),
    )
    config = RetryConfig(max_retries=3)
    client = deepl.DeepLClient(
        AUTH_KEY,
        http_client=mock,
        retry_config=config,
        _sleep_fn=lambda secs: sleep_calls.append(secs),
    )
    client.get_usage()
    assert len(sleep_calls) == 1
    assert sleep_calls[0] >= 0


def test_no_sleep_on_first_success():
    sleep_calls = []
    mock = MockHttpClient()
    mock.push(MockHttpClient.ok_response(USAGE_RESPONSE))
    config = RetryConfig(max_retries=3)
    client = deepl.DeepLClient(
        AUTH_KEY,
        http_client=mock,
        retry_config=config,
        _sleep_fn=lambda secs: sleep_calls.append(secs),
    )
    client.get_usage()
    assert len(sleep_calls) == 0


# ---------------------------------------------------------------------------
# Deprecated http_client globals
# ---------------------------------------------------------------------------


def test_http_client_globals_override_retry_config(monkeypatch):
    """Globals set before construction are picked up into RetryConfig."""
    monkeypatch.setattr(deepl.http_client, "max_network_retries", 2)
    monkeypatch.setattr(deepl.http_client, "min_connection_timeout", 7.0)
    mock = MockHttpClient()
    mock.push(MockHttpClient.ok_response(USAGE_RESPONSE))
    client = deepl.DeepLClient(
        AUTH_KEY, http_client=mock, _sleep_fn=lambda _: None
    )
    assert client._retry_config.max_retries == 2
    assert client._retry_config.min_connection_timeout == 7.0


def test_http_client_globals_emit_deprecation_warning(monkeypatch):
    """Assigning to the legacy globals emits a DeprecationWarning."""
    # Use setitem for cleanup (bypasses __setattr__); assign directly inside
    # pytest.warns so the warning is captured within the context.
    monkeypatch.setitem(
        deepl.http_client.__dict__, "max_network_retries", None
    )
    monkeypatch.setitem(
        deepl.http_client.__dict__, "min_connection_timeout", None
    )
    with pytest.warns(DeprecationWarning, match="max_network_retries"):
        deepl.http_client.max_network_retries = 1
    with pytest.warns(DeprecationWarning, match="min_connection_timeout"):
        deepl.http_client.min_connection_timeout = 5.0


def test_http_client_globals_ignored_after_construction(monkeypatch):
    """Globals set after construction have no effect on the client."""
    mock = MockHttpClient()
    mock.push(MockHttpClient.ok_response(USAGE_RESPONSE))
    client = deepl.DeepLClient(
        AUTH_KEY,
        http_client=mock,
        retry_config=RetryConfig(max_retries=3),
        _sleep_fn=lambda _: None,
    )
    monkeypatch.setattr(deepl.http_client, "max_network_retries", 99)
    assert client._retry_config.max_retries == 3


# ---------------------------------------------------------------------------
# zero max_retries
# ---------------------------------------------------------------------------


def test_zero_max_retries_no_retry():
    mock = MockHttpClient()
    mock.push(
        MockHttpClient.connection_error(should_retry=True),
    )
    client = _make_client(mock, max_retries=0)
    with pytest.raises(ConnectionException):
        client.get_usage()
    assert len(mock.calls) == 1
