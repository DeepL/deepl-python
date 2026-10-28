# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import re
import warnings
from unittest.mock import patch

import deepl
import pytest
from responses import matchers

from .client import (
    AUTH_HEADER,
    make_admin_client,
    make_deepl_client,
    make_translator,
    url,
)
from .matchers import bodyless_request

PLATFORM_USER_AGENT = re.compile(r"^deepl-python/\S+ \(.+\) python/\S+$")
LIBRARY_USER_AGENT = f"deepl-python/{deepl.__version__}"


def reply_with_usage(mocked, user_agent):
    mocked.get(
        url("v2/usage"),
        json={},
        match=[
            matchers.header_matcher(
                {"User-Agent": user_agent, "Authorization": AUTH_HEADER}
            )
        ],
    )


def test_sends_platform_information_in_user_agent(mocked):
    reply_with_usage(mocked, PLATFORM_USER_AGENT)

    make_translator().get_usage()


def test_sends_only_library_version_in_user_agent_when_opted_out(mocked):
    reply_with_usage(mocked, LIBRARY_USER_AGENT)

    make_translator(send_platform_info=False).get_usage()


def test_sends_custom_user_agent(mocked, monkeypatch):
    monkeypatch.setattr(deepl.http_client, "user_agent", "my custom agent")
    reply_with_usage(mocked, "my custom agent")

    make_translator().get_usage()


@pytest.mark.parametrize(
    "kwargs, user_agent",
    [
        (
            {},
            re.compile(PLATFORM_USER_AGENT.pattern[:-1] + r" my_plugin/1\.0$"),
        ),
        ({"send_platform_info": False}, f"{LIBRARY_USER_AGENT} my_plugin/1.0"),
    ],
)
def test_appends_app_info_to_user_agent(mocked, kwargs, user_agent):
    reply_with_usage(mocked, user_agent)

    make_translator(**kwargs).set_app_info("my_plugin", "1.0").get_usage()


def test_appends_app_info_to_custom_user_agent(mocked, monkeypatch):
    monkeypatch.setattr(deepl.http_client, "user_agent", "my custom agent")
    reply_with_usage(mocked, "my custom agent my_plugin/1.0")

    make_translator().set_app_info("my_plugin", "1.0").get_usage()


@pytest.mark.parametrize(
    "make_client, path, call",
    [
        (make_translator, "v2/usage", lambda c: c.get_usage()),
        (make_deepl_client, "v2/usage", lambda c: c.get_usage()),
        (
            make_admin_client,
            "v2/admin/developer-keys",
            lambda c: c.get_developer_keys(),
        ),
    ],
)
def test_sends_headers_option(mocked, make_client, path, call):
    mocked.get(url(path), json=[])
    client = make_client(
        headers={
            "X-Custom": "value",
            "user-agent": "my agent",
            "authorization": "DeepL-Auth-Key other",
        }
    )

    call(client)

    headers = mocked.calls[0].request.headers
    assert headers["X-Custom"] == "value"
    assert headers["User-Agent"] == "my agent"
    assert headers["Authorization"] == AUTH_HEADER


@pytest.mark.parametrize(
    "make_client, path, call",
    [
        (make_translator, "v2/usage", lambda c: c.get_usage()),
        (make_deepl_client, "v2/usage", lambda c: c.get_usage()),
        (
            make_admin_client,
            "v2/admin/developer-keys",
            lambda c: c.get_developer_keys(),
        ),
    ],
)
def test_appends_app_info_option_to_user_agent(
    mocked, make_client, path, call
):
    mocked.get(
        url(path),
        json=[],
        match=[
            matchers.header_matcher(
                {"User-Agent": f"{LIBRARY_USER_AGENT} my_plugin/1.0"}
            )
        ],
    )
    client = make_client(
        send_platform_info=False,
        app_info=deepl.AppInfo("my_plugin", "1.0"),
    )

    call(client)


def test_sends_library_version_when_platform_lookup_fails(mocked):
    reply_with_usage(mocked, f"{LIBRARY_USER_AGENT} failing_platform/1.0")

    with patch("platform.platform", side_effect=OSError("no platform")):
        make_translator().set_app_info("failing_platform", "1.0").get_usage()


@pytest.mark.parametrize("auth_key", ["", " \t\n"])
def test_raises_for_empty_auth_key(auth_key):
    with pytest.raises(ValueError, match="auth_key must not be empty"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            deepl.Translator(auth_key)
    with pytest.raises(ValueError, match="auth_key must not be empty"):
        deepl.DeepLClient(auth_key)


def test_trims_auth_key(mocked):
    mocked.get(
        "https://api-free.deepl.com/v2/usage",
        json={},
        match=[
            matchers.header_matcher({"Authorization": "DeepL-Auth-Key k:fx"})
        ],
    )

    deepl.DeepLClient(" k:fx\n").get_usage()


def test_admin_client_trims_admin_key(mocked):
    mocked.get(
        url("v2/admin/developer-keys"),
        json=[],
        match=[matchers.header_matcher({"Authorization": AUTH_HEADER})],
    )

    deepl.DeepLAdminClient(" k\n").get_developer_keys()


def test_keeps_path_prefix_of_server_url(mocked):
    mocked.get("http://localhost:3000/prefix/v2/usage", json={})

    make_deepl_client(server_url="http://localhost:3000/prefix").get_usage()


def test_sends_requests_to_free_server_for_free_auth_key(mocked):
    mocked.get(
        "https://api-free.deepl.com/v2/usage",
        json={},
        match=[
            matchers.header_matcher({"Authorization": "DeepL-Auth-Key k:fx"})
        ],
    )

    deepl.Translator("k:fx").get_usage()


def test_sends_requests_to_given_server_url(mocked):
    mocked.get(
        "http://localhost:3000/v2/usage", json={}, match=bodyless_request()
    )

    make_translator(server_url="http://localhost:3000").get_usage()


def test_raises_for_malformed_server_url():
    with pytest.raises(deepl.DeepLException, match="preparing request"):
        make_translator(server_url="http:/api.deepl.com").get_usage()


def test_deepl_client_applies_the_same_options(mocked):
    mocked.get(
        "http://localhost:3000/v2/usage", json={}, match=bodyless_request()
    )

    make_deepl_client(server_url="http://localhost:3000").get_usage()


def test_passes_verify_ssl_to_requests(mocked):
    mocked.get(url("v2/usage"), json={})

    make_translator(verify_ssl=False).get_usage()

    assert mocked.calls[0].request.req_kwargs["verify"] is False


def test_passes_proxy_url_to_requests_for_http_and_https(mocked):
    mocked.get(url("v2/usage"), json={})

    make_translator(proxy="http://proxy.example.com:8080").get_usage()

    assert mocked.calls[0].request.req_kwargs["proxies"] == {
        "http": "http://proxy.example.com:8080",
        "https": "http://proxy.example.com:8080",
    }


def test_passes_proxy_dictionary_to_requests(mocked):
    mocked.get(url("v2/usage"), json={})
    proxies = {"https": "http://proxy.example.com:8080"}

    make_translator(proxy=proxies).get_usage()

    assert mocked.calls[0].request.req_kwargs["proxies"] == proxies


def test_raises_for_proxy_of_invalid_type():
    with pytest.raises(ValueError, match="proxy may be specified"):
        make_translator(proxy=["http://proxy.example.com"])


@pytest.mark.parametrize("client_class", [deepl.Translator, deepl.DeepLClient])
@pytest.mark.parametrize("skip_language_check", [True, False])
def test_warns_about_deprecated_skip_language_check(
    client_class, skip_language_check
):
    with pytest.warns(
        DeprecationWarning, match="^skip_language_check is deprecated"
    ) as w:
        client_class("k", skip_language_check=skip_language_check)

    assert len(w) == 1
    assert w[0].filename == __file__
