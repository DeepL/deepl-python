# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .conftest import (
    example_text,
    needs_mock_server,
    needs_mock_proxy_server,
    needs_real_server,
)
from requests import Response  # type: ignore
from unittest.mock import patch, Mock
import deepl
import pathlib
import pytest
import os


def test_version():
    assert "1.31.0" == deepl.__version__


def test_remove_regional_variant():
    for lang, expected in [
        ("EN-US", "EN"),
        ("en-GB", "EN"),
        ("de-AT", "DE"),
        (deepl.Language.ENGLISH_AMERICAN, "EN"),
        (deepl.Language.ENGLISH_BRITISH, "EN"),
        (deepl.Language.GERMAN, "DE"),
        (deepl.Language.ACEHNESE, "ACE"),
        (deepl.Language.KURDISH_KURMANJI, "KMR"),
        (deepl.Language.SPANISH_LATIN_AMERICAN, "ES"),
    ]:
        assert deepl.Language.remove_regional_variant(lang) == expected


@pytest.mark.parametrize(
    "lang",
    [k for k in example_text.keys()],
)
def test_example_translation(lang, translator):
    """Tests translations of pre-prepared example texts to ensure translation
    is working.

    The texts are translations of "proton beam"."""

    input_text = example_text[lang]
    source_lang = deepl.Language.remove_regional_variant(lang)
    result = translator.translate_text(
        input_text, source_lang=source_lang, target_lang="EN-US"
    )
    assert "proton" in result.text.lower()
    assert result.billed_characters == len(input_text)


@needs_real_server
def test_mixed_direction_text(translator):
    ar_ignore_part = "<ignore>يجب تجاهل هذا الجزء.</ignore>"
    en_sentence_with_ar_ignore_part = (
        "<p>This is a <b>short</b> <i>sentence</i>.</p>"
        f"{ar_ignore_part} This is another sentence."
    )
    en_result = translator.translate_text(
        en_sentence_with_ar_ignore_part,
        target_lang="en-US",
        tag_handling="xml",
        ignore_tags="ignore",
    )
    assert ar_ignore_part in en_result.text

    en_ignore_part = "<ignore>This part should be ignored.</ignore>"
    ar_sentence_with_en_ignore_part = (
        f"<p>هذه <i>جملة</i> <b>قصيرة</b>. {en_ignore_part} هذه جملة أخرى.</p>"
    )
    ar_result = translator.translate_text(
        ar_sentence_with_en_ignore_part,
        target_lang="ar",
        tag_handling="xml",
        ignore_tags="ignore",
    )
    assert en_ignore_part in ar_result.text


def test_translate_with_enums(translator):
    result = translator.translate_text(
        example_text["EN"],
        source_lang=deepl.Language.ENGLISH,
        target_lang=deepl.Language.GERMAN,
    )
    assert example_text["DE"] == result.text


def test_invalid_authkey(server):
    translator = deepl.Translator("invalid", server_url=server.server_url)
    with pytest.raises(deepl.exceptions.AuthorizationException):
        translator.get_usage()


def test_invalid_server_url(server):
    translator = deepl.Translator("invalid", server_url="http:/api.deepl.com")
    with pytest.raises(deepl.exceptions.DeepLException):
        translator.get_usage()


def test_usage(translator):
    usage = translator.get_usage()
    assert "Usage this billing period" in str(usage)


def test_language(translator):
    source_languages = translator.get_source_languages()
    for source_language in source_languages:
        if source_language.code == "EN":
            assert source_language.name == "English"
        assert str(source_language) == source_language.code
        assert source_language.supports_formality is None

    target_languages = translator.get_target_languages()
    for target_language in target_languages:
        if target_language.code == "DE":
            assert target_language.supports_formality
        assert target_language.supports_formality is not None


def test_glossary_languages(translator):
    glossary_languages = translator.get_glossary_languages()
    assert len(glossary_languages) > 0
    for language_pair in glossary_languages:
        assert len(language_pair.source_lang) > 0
        assert len(language_pair.target_lang) > 0


def test_server_url_selected_based_on_auth_key(server):
    translator_normal = deepl.Translator("ABCD")
    translator_free = deepl.Translator("ABCD:fx")
    assert translator_normal.server_url == "https://api.deepl.com"
    assert translator_free.server_url == "https://api-free.deepl.com"


@patch("requests.adapters.HTTPAdapter.send")
def test_user_agent(mock_send):
    mock_send.return_value = _build_test_response()
    translator = deepl.Translator(os.environ["DEEPL_AUTH_KEY"])
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert "requests/" in ua_header
    assert " python/" in ua_header
    assert "(" in ua_header


@patch("requests.adapters.HTTPAdapter.send")
def test_user_agent_opt_out(mock_send):
    mock_send.return_value = _build_test_response()
    translator = deepl.Translator(
        os.environ["DEEPL_AUTH_KEY"], send_platform_info=False
    )
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert "requests/" not in ua_header
    assert " python/" not in ua_header
    assert "(" not in ua_header


@patch("requests.adapters.HTTPAdapter.send")
def test_custom_user_agent(mock_send):
    mock_send.return_value = _build_test_response()
    old_user_agent = deepl.http_client.user_agent
    deepl.http_client.user_agent = "my custom user agent"
    translator = deepl.Translator(os.environ["DEEPL_AUTH_KEY"])
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert ua_header == "my custom user agent"
    deepl.http_client.user_agent = old_user_agent


@patch("requests.adapters.HTTPAdapter.send")
def test_user_agent_with_app_info(mock_send):
    mock_send.return_value = _build_test_response()
    translator = deepl.Translator(
        os.environ["DEEPL_AUTH_KEY"],
    ).set_app_info("sample_python_plugin", "1.0.2")
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert "requests/" in ua_header
    assert " python/" in ua_header
    assert "(" in ua_header
    assert " sample_python_plugin/1.0.2" in ua_header


@patch("requests.adapters.HTTPAdapter.send")
def test_user_agent_opt_out_with_app_info(mock_send):
    mock_send.return_value = _build_test_response()
    translator = deepl.Translator(
        os.environ["DEEPL_AUTH_KEY"],
        send_platform_info=False,
    ).set_app_info("sample_python_plugin", "1.0.2")
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert "requests/" not in ua_header
    assert " python/" not in ua_header
    assert "(" not in ua_header
    assert " sample_python_plugin/1.0.2" in ua_header


@patch("requests.adapters.HTTPAdapter.send")
def test_custom_user_agent_with_app_info(mock_send):
    mock_send.return_value = _build_test_response()
    old_user_agent = deepl.http_client.user_agent
    deepl.http_client.user_agent = "my custom user agent"
    translator = deepl.Translator(os.environ["DEEPL_AUTH_KEY"]).set_app_info(
        "sample_python_plugin", "1.0.2"
    )
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert ua_header == "my custom user agent sample_python_plugin/1.0.2"
    deepl.http_client.user_agent = old_user_agent


@patch("requests.adapters.HTTPAdapter.send")
@patch("platform.platform")
def test_user_agent_exception(platform_mock, mock_send):
    mock_send.return_value = _build_test_response()
    platform_mock.side_effect = OSError("mocked test exception")
    translator = deepl.Translator(os.environ["DEEPL_AUTH_KEY"])
    translator.translate_text(example_text["EN"], target_lang="DA")
    ua_header = mock_send.call_args[0][0].headers["User-agent"]
    assert "deepl-python" in ua_header
    assert "requests/" not in ua_header
    assert " python/" not in ua_header
    assert "(" not in ua_header


@needs_mock_proxy_server
def test_proxy_usage(
    server,
    translator_with_random_auth_key,
    translator_with_random_auth_key_and_proxy,
):
    server.expect_proxy()

    translator_with_random_auth_key_and_proxy.get_usage()

    with pytest.raises(deepl.DeepLException):
        translator_with_random_auth_key.get_usage()


@needs_mock_server
def test_usage_no_response(translator, server, monkeypatch):
    server.no_response(2)

    # Lower the retry count and timeout for this test, and restore after test
    monkeypatch.setattr(deepl.http_client, "max_network_retries", 0)
    monkeypatch.setattr(deepl.http_client, "min_connection_timeout", 1.0)

    with pytest.raises(deepl.exceptions.ConnectionException):
        translator.get_usage()


@needs_mock_server
def test_translate_too_many_requests(translator, server, monkeypatch):
    server.respond_with_429(2)
    # Lower the retry count and timeout for this test, and restore after test
    monkeypatch.setattr(deepl.http_client, "max_network_retries", 1)
    monkeypatch.setattr(deepl.http_client, "min_connection_timeout", 1.0)

    with pytest.raises(deepl.exceptions.TooManyRequestsException):
        translator.translate_text(example_text["EN"], target_lang="DE")


@needs_mock_server
def test_usage_overrun(translator_with_random_auth_key, server, tmpdir):
    character_limit = 20
    document_limit = 1
    server.init_character_limit(character_limit)
    server.init_document_limit(document_limit)

    translator = translator_with_random_auth_key
    usage = translator.get_usage()
    assert usage.character.limit == character_limit
    assert usage.document.limit == document_limit
    assert "Characters: 0 of 20" in str(usage)
    assert "Documents: 0 of 1" in str(usage)

    tmpdir = pathlib.Path(tmpdir)
    input_path = tmpdir / "example_document.txt"
    input_path.write_text("a" * character_limit)
    output_path = tmpdir / "example_document_output.txt"
    translator.translate_document_from_filepath(
        input_path, output_path, target_lang="DE"
    )

    usage = translator.get_usage()
    assert usage.any_limit_reached
    assert usage.document.limit_reached
    assert usage.character.limit_reached
    assert not usage.team_document.limit_reached
    # Test deprecated properties as well
    assert usage.any_limit_exceeded
    assert usage.document.limit_exceeded
    assert usage.character.limit_exceeded
    assert not usage.team_document.limit_exceeded

    with pytest.raises(deepl.exceptions.QuotaExceededException):
        translator.translate_document_from_filepath(
            input_path, output_path, target_lang="DE"
        )

    with pytest.raises(deepl.exceptions.QuotaExceededException):
        translator.translate_text(example_text["EN"], target_lang="DE")


@needs_mock_server
def test_usage_team_document_limit(
    translator_with_random_auth_key, server, tmpdir
):
    team_document_limit = 1
    server.init_character_limit(0)
    server.init_document_limit(0)
    server.init_team_document_limit(team_document_limit)

    translator = translator_with_random_auth_key
    usage = translator.get_usage()
    assert not usage.any_limit_reached
    assert "Characters" not in str(usage)
    assert "Documents" not in str(usage)
    assert "Team documents: 0 of 1" in str(usage)

    tmpdir = pathlib.Path(tmpdir)
    input_path = tmpdir / "example_document.txt"
    input_path.write_text("a")
    output_path = tmpdir / "example_document_output.txt"
    translator.translate_document_from_filepath(
        input_path, output_path, target_lang="DE"
    )

    usage = translator.get_usage()
    assert usage.any_limit_reached
    assert not usage.document.limit_reached
    assert not usage.character.limit_reached
    assert usage.team_document.limit_reached


def _build_test_response():
    response = Mock(spec=Response)
    response.status_code = 200
    response.text = (
        '{"translations": [{'
        '"detected_source_language": "EN", '
        '"text": "protonstråle", '
        f'"billed_characters": {len(example_text["EN"])}'
        "}]}"
    )
    response.headers = {
        "Content-Type": "application/json",
        "Server": "nginx",
        "Content-Length": str(len(response.text.encode("utf-8"))),
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    response.encoding = "utf-8"
    response.history = None
    response.raw = None
    response.is_redirect = False
    response.stream = False
    response.url = "https://api.deepl.com/v2/translate"
    return response
