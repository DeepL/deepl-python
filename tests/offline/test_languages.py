# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import pytest
from deepl.api_data import LanguageInclude, LanguageResource

from .client import make_deepl_client, url
from .matchers import bodyless_request

LANGUAGES_JSON = [
    {
        "lang": "de",
        "name": "German",
        "usable_as_source": True,
        "usable_as_target": True,
        "status": "stable",
        "features": {"formality": {"status": "stable"}},
    },
    {
        "lang": "en-US",
        "name": "English (American)",
        "usable_as_source": False,
        "usable_as_target": True,
        "status": "beta",
        "features": {},
    },
    {
        "lang": "en",
        "name": "English",
        "usable_as_source": True,
        "usable_as_target": False,
        "status": "stable",
        "features": {},
    },
]


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


def test_parses_source_languages(mocked):
    mocked.get(
        url("v3/languages"),
        json=LANGUAGES_JSON,
        match=bodyless_request({"resource": "translate_text"}),
    )

    languages = make_deepl_client().get_source_languages()

    assert [(lang.code, lang.name) for lang in languages] == [
        ("DE", "German"),
        ("EN", "English"),
    ]
    assert all(lang.supports_formality is None for lang in languages)
    assert str(languages[0]) == "DE"


def test_parses_target_languages_with_formality_support(mocked):
    mocked.get(
        url("v3/languages"),
        json=LANGUAGES_JSON,
        match=bodyless_request({"resource": "translate_text"}),
    )

    languages = make_deepl_client().get_target_languages()

    assert [(lang.code, lang.supports_formality) for lang in languages] == [
        ("DE", True),
        ("EN-US", False),
    ]


@pytest.mark.parametrize(
    "method", ["get_source_languages", "get_target_languages"]
)
@pytest.mark.parametrize("skip_cache", [True, False])
def test_warns_about_deprecated_skip_cache(mocked, method, skip_cache):
    mocked.get(url("v3/languages"), json=LANGUAGES_JSON)

    with pytest.warns(
        DeprecationWarning, match="^skip_cache is deprecated"
    ) as w:
        getattr(make_deepl_client(), method)(skip_cache=skip_cache)

    assert w[0].filename == __file__


def test_returns_no_languages_for_unexpected_reply(mocked):
    mocked.get(url("v3/languages"), json={"message": "unexpected"})

    assert make_deepl_client().get_source_languages() == []


def test_derives_glossary_pairs_from_usable_languages(mocked):
    mocked.get(
        url("v3/languages"),
        json=[
            {"lang": "de", "usable_as_source": True, "usable_as_target": True},
            {"lang": "en", "usable_as_source": True, "usable_as_target": True},
            {
                "lang": "fr",
                "usable_as_source": False,
                "usable_as_target": True,
            },
        ],
        match=bodyless_request({"resource": "glossary"}),
    )

    pairs = make_deepl_client().get_glossary_languages()

    assert [(pair.source_lang, pair.target_lang) for pair in pairs] == [
        ("de", "en"),
        ("de", "fr"),
        ("en", "de"),
        ("en", "fr"),
    ]


@pytest.mark.parametrize(
    "resource, include, query",
    [
        (
            "write",
            None,
            {"resource": "write"},
        ),
        (
            LanguageResource.GLOSSARY,
            [LanguageInclude.BETA, "external"],
            {"resource": "glossary", "include": ["beta", "external"]},
        ),
    ],
)
def test_sends_resource_and_include_when_getting_languages(
    mocked, resource, include, query
):
    mocked.get(
        url("v3/languages"),
        json=LANGUAGES_JSON,
        match=bodyless_request(query),
    )

    make_deepl_client().get_languages_for_resource(resource, include=include)


def test_parses_languages_for_resource(mocked):
    mocked.get(url("v3/languages"), json=LANGUAGES_JSON)

    first, second, _ = make_deepl_client().get_languages_for_resource(
        "translate_text"
    )

    assert first.code == "de"
    assert first.supports("formality")
    assert not second.supports("formality")
    assert str(first) == "German (de)"


def test_raises_when_getting_languages_for_empty_resource():
    with pytest.raises(ValueError, match="resource must not be empty"):
        make_deepl_client().get_languages_for_resource("")


def test_parses_language_resources(mocked):
    mocked.get(
        url("v3/languages/resources"),
        json=[
            {
                "name": "translate_text",
                "features": [
                    {
                        "name": "glossary",
                        "needs_source_support": True,
                        "needs_target_support": True,
                    },
                    {"name": "formality"},
                ],
            },
            {"name": "voice"},
        ],
        match=bodyless_request(),
    )

    translate_text, voice = make_deepl_client().get_language_resources()

    assert translate_text.resource == "translate_text"
    assert translate_text.supports("glossary")
    assert not translate_text.supports("nonexistent")
    glossary = translate_text.features["glossary"]
    assert translate_text.features["formality"].needs_source_support is None
    assert str(glossary) == "glossary"
    assert voice.features == {}
