# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .conftest import example_text, needs_mock_server, needs_real_server
import deepl
import pytest
import re
import time


def test_single_text(translator):
    result = translator.translate_text(example_text["EN"], target_lang="DE")
    assert example_text["DE"] == result.text
    assert "EN" == result.detected_source_lang
    assert example_text["DE"] == str(result)
    assert result.billed_characters == len(example_text["EN"])


@pytest.mark.parametrize(
    "model_type",
    [model_type for model_type in deepl.ModelType],
)
def test_model_type(translator, model_type):
    result = translator.translate_text(
        example_text["EN"], target_lang="DE", model_type=model_type
    )
    assert result.model_type_used is not None


def test_string_list(translator):
    texts = [example_text["FR"], example_text["EN"]]
    result = translator.translate_text(texts, target_lang="DE")
    assert example_text["DE"] == result[0].text
    assert example_text["DE"] == result[1].text


def test_string_generator(translator):
    def gen():
        yield example_text["EN"]
        yield example_text["EN"]
        yield example_text["EN"]

    result = translator.translate_text(gen(), target_lang="DE")
    assert [example_text["DE"]] * 3 == [r.text for r in result]
    assert ["EN"] * 3 == [r.detected_source_lang for r in result]


def test_source_lang(translator):
    def check_result(result):
        assert result.text == example_text["DE"]
        assert result.detected_source_lang == "EN"

    check_result(
        translator.translate_text(example_text["EN"], target_lang="DE")
    )
    check_result(
        translator.translate_text(
            example_text["EN"], source_lang="En", target_lang="DE"
        )
    )
    check_result(
        translator.translate_text(
            example_text["EN"], source_lang="en", target_lang="DE"
        )
    )

    source_languages = translator.get_source_languages()
    source_language_en = next(
        language for language in source_languages if language.code == "EN"
    )
    check_result(
        translator.translate_text(
            example_text["EN"],
            source_lang=source_language_en,
            target_lang="DE",
        )
    )


def test_target_lang(translator):
    def check_result(result):
        assert result.text == example_text["DE"]
        assert result.detected_source_lang == "EN"

    check_result(
        translator.translate_text(example_text["EN"], target_lang="De")
    )
    check_result(
        translator.translate_text(example_text["EN"], target_lang="de")
    )

    target_languages = translator.get_target_languages()
    target_language_de = next(
        language for language in target_languages if language.code == "DE"
    )
    check_result(
        translator.translate_text(
            example_text["EN"],
            target_lang=target_language_de,
        )
    )


@pytest.mark.parametrize("target_lang", ["EN", "PT"])
def test_bare_target_language_accepted(translator, target_lang):
    translator.translate_text(example_text["DE"], target_lang=target_lang)


def test_invalid_language(translator):
    with pytest.raises(
        deepl.DeepLException,
        match="target_lang.*not supported",
    ):
        translator.translate_text(example_text["EN"], target_lang="XX")

    with pytest.raises(
        deepl.DeepLException,
        match="source_lang.*not supported",
    ):
        translator.translate_text(
            example_text["EN"], source_lang="XX", target_lang="DE"
        )


def test_skip_language_check(server):
    translator = deepl.Translator(
        server.auth_key, server_url=server.server_url, skip_language_check=True
    )
    with pytest.raises(deepl.DeepLException, match="target_lang"):
        translator.translate_text(example_text["EN"], target_lang="XX")
    with pytest.raises(deepl.DeepLException, match="source_lang"):
        translator.translate_text(
            example_text["EN"], source_lang="XX", target_lang="DE"
        )


def test_invalid_text(translator):
    with pytest.raises(TypeError, match="text parameter"):
        translator.translate_text(123, target_lang="DE")
    with pytest.raises(TypeError):
        translator.translate_text(target_lang="DE")


@needs_mock_server
def test_translate_with_retries(translator, server):
    server.respond_with_429(2)
    time_before = time.time()
    result = translator.translate_text(example_text["EN"], target_lang="DE")
    time_after = time.time()
    assert example_text["DE"] == result.text
    assert "EN" == result.detected_source_lang
    assert time_after - time_before > 1.0


def test_formality(translator, server):
    input_text = "How are you?"
    informal = "dir"  # Wie geht's dir?
    formal = "Ihnen"  # Wie geht's Ihnen?

    result = translator.translate_text(
        input_text, target_lang="DE", formality=deepl.Formality.LESS
    )
    if not server.is_mock_server:
        assert informal in result.text
    # Default formality is automatic, so the output may be either
    # formal or informal
    result = translator.translate_text(
        input_text, target_lang="DE", formality=deepl.Formality.DEFAULT
    )
    if not server.is_mock_server:
        assert formal in result.text or informal in result.text
    result = translator.translate_text(
        input_text, target_lang="DE", formality=deepl.Formality.MORE
    )
    if not server.is_mock_server:
        assert formal in result.text

    # Specifying formality as string is also permitted
    result = translator.translate_text(
        input_text, target_lang="DE", formality="less"
    )
    if not server.is_mock_server:
        assert informal in result.text

    result = translator.translate_text(
        input_text, target_lang="DE", formality="default"
    )
    if not server.is_mock_server:
        assert formal in result.text or informal in result.text

    result = translator.translate_text(
        input_text, target_lang="DE", formality="more"
    )
    if not server.is_mock_server:
        assert formal in result.text

    # formality parameter is case-insensitive
    result = translator.translate_text(
        input_text, target_lang="DE", formality="Less"
    )
    if not server.is_mock_server:
        assert informal in result.text

    with pytest.raises(deepl.DeepLException, match=r".*formality.*"):
        _ = translator.translate_text(
            input_text, target_lang="DE", formality="invalid"
        )

    with pytest.raises(
        deepl.DeepLException, match=r".*Target language.*formality.*"
    ):
        _ = translator.translate_text(
            "Test", target_lang="EN-US", formality="more"
        )

    result = translator.translate_text(
        input_text, target_lang="DE", formality=deepl.Formality.PREFER_LESS
    )
    if not server.is_mock_server:
        assert informal in result.text

    result = translator.translate_text(
        input_text, target_lang="DE", formality=deepl.Formality.PREFER_MORE
    )
    if not server.is_mock_server:
        assert formal in result.text

    # Using prefer_ * with a language that does not support formality is not
    # an error
    translator.translate_text(
        input_text, target_lang="TR", formality=deepl.Formality.PREFER_MORE
    )
    with pytest.raises(
        deepl.DeepLException, match=r".*Target language.*formality.*"
    ):
        _ = translator.translate_text(
            input_text, target_lang="TR", formality="more"
        )


def test_preserve_formatting(translator):
    # Note: this test may use the mock server that will not translate the text,
    # therefore we do not check the translated result.
    _ = translator.translate_text(
        example_text["EN"], target_lang="DE", preserve_formatting=True
    )
    _ = translator.translate_text(
        example_text["EN"], target_lang="DE", preserve_formatting=False
    )


def test_context(translator):
    # In German, "scharf" can mean:
    # - spicy/hot when referring to food, or
    # - sharp when referring to other objects such as a knife (Messer).
    text = "Das ist scharf!"
    _ = translator.translate_text(text, target_lang="en-US")
    # Result: "That is hot!"

    _ = translator.translate_text(
        text, target_lang="en-US", context="Das ist ein Messer"
    )
    # Result: "That is sharp!"


def test_split_sentences_basic(translator):
    text = """If the implementation is hard to explain, it's a bad idea.
        If the implementation is easy to explain, it may be a good idea."""

    # Note: this test may use the mock server that will not translate the text,
    # therefore we do not check the translated result.
    _ = translator.translate_text(
        text, target_lang="DE", split_sentences=deepl.SplitSentences.OFF
    )
    _ = translator.translate_text(
        text, target_lang="DE", split_sentences=deepl.SplitSentences.ALL
    )
    _ = translator.translate_text(
        text,
        target_lang="DE",
        split_sentences=deepl.SplitSentences.NO_NEWLINES,
    )
    _ = translator.translate_text(text, target_lang="DE", split_sentences="0")
    _ = translator.translate_text(text, target_lang="DE", split_sentences="1")
    _ = translator.translate_text(
        text, target_lang="DE", split_sentences="nonewlines"
    )

    with pytest.raises(deepl.DeepLException, match=r".*split_sentences.*"):
        _ = translator.translate_text(
            text, target_lang="DE", split_sentences="invalid"
        )


def test_tag_handling_basic(translator):
    text = """
<!DOCTYPE html>
<html>
   <body>
       <p>This is an example sentence.</p>
   </body>
</html>
"""
    # Note: this test may use the mock server that will not translate the text,
    # therefore we do not check the translated result.
    _ = translator.translate_text(text, target_lang="DE", tag_handling="xml")
    _ = translator.translate_text(text, target_lang="DE", tag_handling="html")


@needs_real_server
def test_tag_handling_xml(translator):
    text = """
<document>
    <meta>
        <title>A document's title</title>
    </meta>
    <content>
        <par>
        <span>This is a sentence split</span>
        <span>across two &lt;span&gt; tags that should be treated as one.
        </span>
        </par>
        <par>Here is a sentence. Followed by a second one.</par>
        <raw>This sentence will not be translated.</raw>
    </content>
</document>
    """

    result = translator.translate_text(
        text,
        target_lang="DE",
        tag_handling="xml",
        outline_detection=False,
        non_splitting_tags="span",
        splitting_tags=["title", "par"],
        ignore_tags=["raw"],
    )

    assert "<raw>This sentence will not be translated.</raw>" in result.text
    assert re.compile("<title>.*Der Titel.*</title>").search(result.text)


@needs_real_server
def test_tag_handling_html(translator):
    text = """
<!DOCTYPE html>
<html>
   <body>
       <h1>My First Heading</h1>
       <p translate="no">My first paragraph.</p>
   </body>
</html>
"""

    result = translator.translate_text(
        text, target_lang="DE", tag_handling="html"
    )
    assert "<h1>Meine erste Überschrift</h1>" in result.text
    assert '<p translate="no">My first paragraph.</p>' in result.text


def test_empty_auth_key(server):
    with pytest.raises(ValueError, match=r"auth_key must not be empty"):
        deepl.Translator("", server_url=server.server_url)


def test_invalid_auth_key(server):
    translator = deepl.Translator("invalid", server_url=server.server_url)
    with pytest.raises(
        deepl.AuthorizationException, match=r".*Authorization failure.*"
    ):
        translator.translate_text("Hello, world!", target_lang="DE")


def test_empty_text(translator):
    with pytest.raises(ValueError, match=r".*empty.*"):
        translator.translate_text("", target_lang="DE")


def test_mixed_case_languages(translator):
    result = translator.translate_text(example_text["DE"], target_lang="en-us")
    assert example_text["EN-US"] == result.text.lower()
    assert "DE" == result.detected_source_lang

    result = translator.translate_text(example_text["DE"], target_lang="EN-us")
    assert example_text["EN-US"] == result.text.lower()
    assert "DE" == result.detected_source_lang

    result = translator.translate_text(
        example_text["DE"], source_lang="de", target_lang="EN-US"
    )
    assert example_text["EN-US"] == result.text.lower()
    assert "DE" == result.detected_source_lang

    result = translator.translate_text(
        example_text["DE"], source_lang="dE", target_lang="EN-US"
    )
    assert example_text["EN-US"] == result.text.lower()
    assert "DE" == result.detected_source_lang


def test_extra_body_params(translator):
    # Checks `target_lang` is overwritten, does not check
    # debug is actually sent
    extra = {"target_lang": "FR", "debug": "1"}
    res = translator.translate_text(
        example_text["EN"],
        target_lang="DE",
        extra_body_parameters=extra,
    )
    assert isinstance(res, deepl.TextResult)
    assert example_text["FR"] == res.text
    assert "EN" == res.detected_source_lang
    assert res.billed_characters == len(example_text["EN"])


@needs_real_server
def test_custom_instructions(translator):
    text = "I am testing if custom instructions are working correctly."
    no_custom_instructions_result = translator.translate_text(
        text,
        target_lang="DE",
    )

    custom_instructions_result = translator.translate_text(
        text,
        target_lang="DE",
        custom_instructions=["Use informal language", "Be concise"],
    )

    assert isinstance(custom_instructions_result, deepl.TextResult)
    assert custom_instructions_result.text is not None
    assert len(custom_instructions_result.text) > 0
    assert custom_instructions_result.detected_source_lang == "EN"

    # Check that applying custom instructions results in different translations
    assert (
        custom_instructions_result.text != no_custom_instructions_result.text
    )


@needs_real_server
def test_tag_handling_version_v1(translator):
    text = "<p>Hello world</p>"
    result = translator.translate_text(
        text, target_lang="DE", tag_handling="html", tag_handling_version="v1"
    )
    assert isinstance(result, deepl.TextResult)
    assert result.text is not None
    assert len(result.text) > 0


@needs_real_server
def test_tag_handling_version_v2(translator):
    text = "<p>Hello world</p>"
    result = translator.translate_text(
        text, target_lang="DE", tag_handling="html", tag_handling_version="v2"
    )
    assert isinstance(result, deepl.TextResult)
    assert result.text is not None
    assert len(result.text) > 0
