# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import pytest

from .client import make_translator, url
from .matchers import json_request

BASE_BODY = {
    "text": ["hello"],
    "target_lang": "DE",
    "show_billed_characters": True,
}

CREATION_TIME = "2021-08-03T14:16:18.329Z"


def reply_with_translation(mocked, body):
    mocked.post(
        url("v2/translate"),
        json={
            "translations": [
                {
                    "detected_source_language": "EN",
                    "text": "hallo",
                    "billed_characters": 5,
                }
            ]
        },
        match=json_request(body),
    )


def glossary_info(source_lang="EN", target_lang="DE"):
    return deepl.GlossaryInfo.from_json(
        {
            "glossary_id": "g-v2",
            "name": "glossary",
            "ready": True,
            "source_lang": source_lang.lower(),
            "target_lang": target_lang.lower(),
            "creation_time": CREATION_TIME,
            "entry_count": 1,
        }
    )


def multilingual_glossary_info():
    return deepl.api_data.MultilingualGlossaryInfo.from_json(
        {
            "glossary_id": "g-v3",
            "name": "glossary",
            "creation_time": CREATION_TIME,
            "dictionaries": [
                {"source_lang": "en", "target_lang": "de", "entry_count": 1}
            ],
        }
    )


def style_rule_info(language="en"):
    return deepl.api_data.StyleRuleInfo.from_json(
        {
            "style_id": "style-1",
            "name": "style",
            "creation_time": CREATION_TIME,
            "updated_time": CREATION_TIME,
            "language": language,
            "version": 1,
        }
    )


def translation_memory_info():
    return deepl.api_data.TranslationMemoryInfo.from_json(
        {
            "translation_memory_id": "tm-1",
            "name": "memory",
            "source_language": "en",
            "target_languages": ["de"],
            "segment_count": 1,
        }
    )


def test_sends_text_and_target_language(mocked):
    reply_with_translation(mocked, BASE_BODY)

    make_translator().translate_text("hello", target_lang="de")


@pytest.mark.parametrize(
    "kwargs, extra_body",
    [
        ({"source_lang": "en"}, {"source_lang": "EN"}),
        ({"context": "greeting"}, {"context": "greeting"}),
        (
            {"split_sentences": deepl.SplitSentences.NO_NEWLINES},
            {"split_sentences": "nonewlines"},
        ),
        ({"split_sentences": "0"}, {"split_sentences": "0"}),
        ({"preserve_formatting": True}, {"preserve_formatting": True}),
        ({"preserve_formatting": False}, {"preserve_formatting": False}),
        ({"formality": deepl.Formality.MORE}, {"formality": "more"}),
        ({"formality": "Prefer_Less"}, {"formality": "prefer_less"}),
        (
            {"tag_handling": "xml", "tag_handling_version": "v2"},
            {"tag_handling": "xml", "tag_handling_version": "v2"},
        ),
        ({"outline_detection": False}, {"outline_detection": False}),
        ({"non_splitting_tags": "a,b"}, {"non_splitting_tags": ["a", "b"]}),
        (
            {"splitting_tags": ["a,b", "c"]},
            {"splitting_tags": ["a", "b", "c"]},
        ),
        ({"ignore_tags": ("a", "b,c")}, {"ignore_tags": ["a", "b", "c"]}),
        (
            {"model_type": deepl.ModelType.QUALITY_OPTIMIZED},
            {"model_type": "quality_optimized"},
        ),
        (
            {"model_type": "prefer_quality_optimized"},
            {"model_type": "prefer_quality_optimized"},
        ),
        (
            {"custom_instructions": ["Be brief", "Be kind"]},
            {"custom_instructions": ["Be brief", "Be kind"]},
        ),
        (
            {"extra_body_parameters": {"new_option": [1, 2]}},
            {"new_option": [1, 2]},
        ),
        (
            {"extra_body_parameters": {"target_lang": "FR", "text": ["x"]}},
            {"target_lang": "FR", "text": ["x"]},
        ),
    ],
)
def test_sends_option(mocked, kwargs, extra_body):
    reply_with_translation(mocked, {**BASE_BODY, **extra_body})

    make_translator().translate_text("hello", target_lang="DE", **kwargs)


@pytest.mark.parametrize(
    "glossary, body",
    [
        ("g-str", {"glossary_id": "g-str"}),
        (glossary_info(), {"glossary_id": "g-v2"}),
        (multilingual_glossary_info(), {"glossary_id": "g-v3"}),
    ],
)
def test_sends_glossary_id(mocked, glossary, body):
    reply_with_translation(mocked, {**BASE_BODY, **body, "source_lang": "EN"})

    make_translator().translate_text(
        "hello", source_lang="EN", target_lang="DE", glossary=glossary
    )


def test_sends_glossary_ids_in_order(mocked):
    reply_with_translation(
        mocked,
        {
            **BASE_BODY,
            "source_lang": "EN",
            "glossary_ids": ["g-str", "g-v2", "g-v3"],
        },
    )

    make_translator().translate_text(
        "hello",
        source_lang="EN",
        target_lang="DE",
        glossary_ids=["g-str", glossary_info(), multilingual_glossary_info()],
    )


@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_style_rule_id(mocked, style_rule):
    reply_with_translation(
        mocked, {**BASE_BODY, "target_lang": "EN-US", "style_id": "style-1"}
    )

    make_translator().translate_text(
        "hello", target_lang="EN-US", style_rule=style_rule
    )


@pytest.mark.parametrize("memory", ["tm-1", translation_memory_info()])
def test_sends_translation_memory_id_and_threshold(mocked, memory):
    reply_with_translation(
        mocked,
        {
            **BASE_BODY,
            "translation_memory_id": "tm-1",
            "translation_memory_threshold": 80,
        },
    )

    make_translator().translate_text(
        "hello",
        target_lang="DE",
        translation_memory=memory,
        translation_memory_threshold=80,
    )


def test_sends_translation_memory_without_threshold(mocked):
    reply_with_translation(
        mocked, {**BASE_BODY, "translation_memory_id": "tm-1"}
    )

    make_translator().translate_text(
        "hello", target_lang="DE", translation_memory="tm-1"
    )


@pytest.mark.parametrize("target_lang", ["EN", "PT", "en-us", "PT-BR"])
def test_accepts_target_language_without_regional_variant(mocked, target_lang):
    reply_with_translation(
        mocked, {**BASE_BODY, "target_lang": target_lang.upper()}
    )

    make_translator().translate_text("hello", target_lang=target_lang)


def test_sends_language_enums_as_codes(mocked):
    reply_with_translation(
        mocked, {**BASE_BODY, "source_lang": "EN", "target_lang": "DE"}
    )

    make_translator().translate_text(
        "hello",
        source_lang=deepl.Language.ENGLISH,
        target_lang=deepl.Language.GERMAN,
    )


def test_sends_iterable_text_as_list(mocked):
    reply_with_translation(mocked, {**BASE_BODY, "text": ["a", "b"]})

    make_translator().translate_text(
        (text for text in ["a", "b"]), target_lang="DE"
    )


def test_accepts_skip_language_check_without_effect(mocked):
    reply_with_translation(mocked, BASE_BODY)

    make_translator(skip_language_check=True).translate_text(
        "hello", target_lang="DE"
    )


def test_parses_single_text_into_one_result(mocked):
    mocked.post(
        url("v2/translate"),
        json={
            "translations": [
                {
                    "detected_source_language": "EN",
                    "text": "hallo",
                    "billed_characters": "5",
                }
            ]
        },
    )

    result = make_translator().translate_text("hello", target_lang="DE")

    assert isinstance(result, deepl.TextResult)
    assert result.billed_characters == 5


def test_parses_text_list_into_list_of_results(mocked):
    mocked.post(
        url("v2/translate"),
        json={
            "translations": [
                {"text": "a", "billed_characters": 1},
                {"text": "b", "billed_characters": 2},
            ]
        },
    )

    results = make_translator().translate_text(["x", "y"], target_lang="DE")

    assert len(results) == 2
    assert all(isinstance(result, deepl.TextResult) for result in results)


def test_returns_list_for_single_item_list(mocked):
    mocked.post(
        url("v2/translate"),
        json={"translations": [{"text": "a", "billed_characters": 1}]},
    )

    results = make_translator().translate_text(["x"], target_lang="DE")

    assert isinstance(results, list)


def test_sends_glossary_target_language_for_translate_with_glossary(mocked):
    reply_with_translation(
        mocked,
        {
            **BASE_BODY,
            "source_lang": "EN",
            "target_lang": "EN-GB",
            "glossary_id": "g-v2",
        },
    )

    make_translator().translate_text_with_glossary(
        "hello", glossary_info(source_lang="EN", target_lang="EN")
    )


def test_sends_explicit_target_language_for_translate_with_glossary(mocked):
    reply_with_translation(
        mocked,
        {
            **BASE_BODY,
            "source_lang": "EN",
            "target_lang": "EN-US",
            "glossary_id": "g-v2",
            "formality": "less",
        },
    )

    make_translator().translate_text_with_glossary(
        "hello",
        glossary_info(source_lang="EN", target_lang="EN"),
        target_lang="EN-US",
        formality="less",
    )


def test_raises_when_translating_with_glossary_id_string():
    with pytest.raises(ValueError, match="instance of GlossaryInfo"):
        make_translator().translate_text_with_glossary(
            "hello", "g-str"  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "text, error, match",
    [
        ("", ValueError, "text must not be empty"),
        (5, TypeError, "string or an iterable"),
    ],
)
def test_raises_for_invalid_text(text, error, match):
    with pytest.raises(error, match=match):
        make_translator().translate_text(text, target_lang="DE")


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"glossary": "g"}, "source_lang is required if using a glossary"),
        (
            {"glossary_ids": ["g"]},
            "source_lang is required if using glossary_ids",
        ),
        (
            {"glossary": "g", "glossary_ids": ["h"], "source_lang": "EN"},
            "cannot be used together",
        ),
        (
            {"glossary_ids": list("abcdef"), "source_lang": "EN"},
            "more than 5 glossary IDs",
        ),
        (
            {"glossary": glossary_info("EN", "DE"), "source_lang": "FR"},
            "must match glossary",
        ),
        (
            {"glossary": glossary_info("EN", "FR"), "source_lang": "EN"},
            "must match glossary",
        ),
        (
            {
                "glossary": multilingual_glossary_info(),
                "source_lang": "FR",
            },
            "must have a glossary with a dictionary",
        ),
        (
            {"style_rule": style_rule_info("fr")},
            "must match style rule language",
        ),
        (
            {"translation_memory_threshold": 80},
            "requires translation_memory",
        ),
        (
            {"translation_memory": "tm", "translation_memory_threshold": -1},
            "between 0 and 100",
        ),
        (
            {"translation_memory": "tm", "translation_memory_threshold": 101},
            "between 0 and 100",
        ),
    ],
)
def test_raises_for_invalid_options(kwargs, match):
    with pytest.raises(ValueError, match=match):
        make_translator().translate_text("hello", target_lang="DE", **kwargs)
