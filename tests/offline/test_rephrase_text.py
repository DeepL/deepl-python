# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import pytest
from deepl.api_data import WriteResult

from .client import make_deepl_client, url
from .matchers import json_request

IMPROVEMENT = {
    "text": "improved",
    "detected_source_language": "EN",
    "target_language": "EN-GB",
}


def reply_with_improvement(mocked, body):
    mocked.post(
        url("v2/write/rephrase"),
        json={"improvements": [IMPROVEMENT]},
        match=json_request(body),
    )


def test_sends_text_without_optional_fields(mocked):
    reply_with_improvement(mocked, {"text": ["hello"]})

    make_deepl_client().rephrase_text("hello")


@pytest.mark.parametrize(
    "kwargs, extra_body",
    [
        ({"target_lang": "EN-GB"}, {"target_lang": "EN-GB"}),
        ({"style": "business"}, {"writing_style": "business"}),
        ({"tone": "friendly"}, {"tone": "friendly"}),
        (
            {"style": "casual", "tone": "confident"},
            {"writing_style": "casual", "tone": "confident"},
        ),
    ],
)
def test_sends_option(mocked, kwargs, extra_body):
    reply_with_improvement(mocked, {"text": ["hello"], **extra_body})

    make_deepl_client().rephrase_text("hello", **kwargs)


def test_sends_iterable_text_as_list(mocked):
    reply_with_improvement(mocked, {"text": ["a", "b"]})

    make_deepl_client().rephrase_text(iter(["a", "b"]))


def test_parses_single_text_into_one_write_result(mocked):
    reply_with_improvement(mocked, {"text": ["hello"]})

    result = make_deepl_client().rephrase_text("hello")

    assert isinstance(result, WriteResult)


def test_parses_text_list_into_list_of_write_results(mocked):
    mocked.post(
        url("v2/write/rephrase"),
        json={"improvements": [IMPROVEMENT, {**IMPROVEMENT, "text": "b"}]},
    )

    results = make_deepl_client().rephrase_text(["x", "y"])

    assert len(results) == 2


@pytest.mark.parametrize(
    "text, error, match",
    [
        ("", ValueError, "text must not be empty"),
        (5, TypeError, "string or an iterable"),
    ],
)
def test_raises_for_invalid_text(text, error, match):
    with pytest.raises(error, match=match):
        make_deepl_client().rephrase_text(text)
