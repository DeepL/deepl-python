# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import pytest
from deepl import DeepLException
from deepl.api_data import Language, WriteResult

from .client import make_deepl_client, url
from .matchers import json_request

IMPROVEMENT = {
    "text": "corrected",
    "detected_source_language": "EN",
    "target_language": "EN-US",
}


def reply_with_improvement(mocked, body):
    mocked.post(
        url("v2/write/correct"),
        json={"improvements": [IMPROVEMENT] * len(body["text"])},
        match=json_request(body),
    )


def test_sends_text_without_target_language(mocked):
    reply_with_improvement(mocked, {"text": ["helo"]})

    make_deepl_client().correct_text("helo")


def test_sends_target_language(mocked):
    reply_with_improvement(mocked, {"text": ["helo"], "target_lang": "EN-US"})

    make_deepl_client().correct_text("helo", target_lang="EN-US")


def test_sends_target_language_object_as_code(mocked):
    reply_with_improvement(mocked, {"text": ["helo"], "target_lang": "en-US"})

    make_deepl_client().correct_text(
        "helo", target_lang=Language("en-US", "English (American)")
    )


def test_sends_iterable_text_as_list(mocked):
    reply_with_improvement(mocked, {"text": ["a", "b"]})

    make_deepl_client().correct_text(iter(["a", "b"]))


def test_parses_single_text_into_one_write_result(mocked):
    reply_with_improvement(mocked, {"text": ["helo"]})

    result = make_deepl_client().correct_text("helo")

    assert isinstance(result, WriteResult)


def test_parses_text_list_into_list_of_write_results(mocked):
    reply_with_improvement(mocked, {"text": ["helo"]})

    results = make_deepl_client().correct_text(["helo"])

    assert len(results) == 1
    assert isinstance(results[0], WriteResult)


@pytest.mark.parametrize(
    "text, error, match",
    [
        ("", ValueError, "text must not be empty"),
        (5, TypeError, "string or an iterable"),
    ],
)
def test_raises_for_invalid_text(text, error, match):
    with pytest.raises(error, match=match):
        make_deepl_client().correct_text(text)


@pytest.mark.parametrize(
    "text, body",
    [
        ("helo", {}),
        ("helo", {"improvements": []}),
        ("helo", {"improvements": [None]}),
        ("helo", {"improvements": [{"text": 5}]}),
        (["a", "b"], {"improvements": [IMPROVEMENT]}),
    ],
)
def test_raises_deepl_exception_for_malformed_improvements(mocked, text, body):
    mocked.post(url("v2/write/correct"), json=body)

    with pytest.raises(DeepLException, match="Unexpected response"):
        make_deepl_client().correct_text(text)
