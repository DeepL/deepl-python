# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime

import pytest

from .client import make_translator, url
from .matchers import bodyless_request


def test_sends_get_to_usage(mocked):
    mocked.get(
        url("v2/usage"),
        json={"character_count": 1, "character_limit": 2},
        match=bodyless_request(),
    )

    make_translator().get_usage()


def test_parses_usage_counts_and_limits(mocked):
    mocked.get(
        url("v2/usage"),
        json={
            "character_count": 20,
            "character_limit": 20,
            "document_count": 0,
            "document_limit": 1,
            "team_document_count": "3",
            "team_document_limit": 5,
        },
    )

    usage = make_translator().get_usage()

    assert usage.character.count == 20
    assert usage.team_document.count == 3
    assert usage.character.limit_reached
    assert not usage.document.limit_reached
    assert not usage.team_document.limit_reached
    assert usage.any_limit_reached
    assert (
        str(usage) == "Usage this billing period:\n"
        "Characters: 20 of 20\n"
        "Documents: 0 of 1\n"
        "Team documents: 3 of 5"
    )


def test_parses_usage_without_limits(mocked):
    mocked.get(url("v2/usage"), json={"character_count": 4})

    usage = make_translator().get_usage()

    assert not usage.character.valid
    assert not usage.any_limit_reached
    assert str(usage) == "Usage this billing period:\n"


def test_warns_about_deprecated_limit_exceeded(mocked):
    mocked.get(
        url("v2/usage"),
        json={"character_count": 1, "character_limit": 1},
    )

    usage = make_translator().get_usage()

    with pytest.warns(
        DeprecationWarning,
        match="^any_limit_exceeded is deprecated, use any_limit_reached$",
    ):
        assert usage.any_limit_exceeded
    with pytest.warns(
        DeprecationWarning,
        match="^limit_exceeded is deprecated, use limit_reached$",
    ):
        assert usage.character.limit_exceeded


def test_parses_api_pro_usage(mocked):
    mocked.get(
        url("v2/usage"),
        json={
            "character_count": 180118,
            "character_limit": 1250000,
            "products": [
                {
                    "product_type": "write",
                    "billing_unit": "characters",
                    "api_key_unit_count": 0,
                    "account_unit_count": 5643,
                    "api_key_character_count": 0,
                    "character_count": 5643,
                },
                {
                    "product_type": "speechToText",
                    "billing_unit": "minutes",
                    "api_key_unit_count": 30,
                    "account_unit_count": 45,
                },
            ],
            "api_key_character_count": 636,
            "api_key_character_limit": 1000000000000,
            "speech_to_text_milliseconds_count": 0,
            "speech_to_text_milliseconds_limit": 0,
            "speech_to_text_minutes_count": 30,
            "speech_to_text_minutes_limit": 600,
            "speech_to_speech_minutes_count": 12,
            "speech_to_speech_minutes_limit": 600,
            "start_time": "2025-05-13T09:18:42Z",
            "end_time": "2025-06-13T09:18:42Z",
        },
    )

    usage = make_translator().get_usage()

    assert usage.character.count == 180118
    assert usage.character.limit == 1250000
    assert usage.api_key_character.count == 636
    assert usage.api_key_character.limit == 1000000000000
    assert usage.speech_to_text_minutes.count == 30
    assert usage.speech_to_text_minutes.limit == 600
    assert usage.speech_to_speech_minutes.count == 12
    assert usage.speech_to_speech_minutes.limit == 600
    utc = datetime.timezone.utc
    assert usage.start_time == datetime.datetime(
        2025, 5, 13, 9, 18, 42, tzinfo=utc
    )
    assert usage.end_time == datetime.datetime(
        2025, 6, 13, 9, 18, 42, tzinfo=utc
    )
    assert usage.products is not None
    assert [
        (
            p.product_type,
            p.billing_unit,
            p.api_key_unit_count,
            p.account_unit_count,
        )
        for p in usage.products
    ] == [
        ("write", "characters", 0, 5643),
        ("speechToText", "minutes", 30, 45),
    ]
    assert not usage.any_limit_reached
    assert (
        str(usage)
        == "Usage this billing period:\nCharacters: 180118 of 1250000"
    )


def test_parses_free_usage_without_api_pro_fields(mocked):
    mocked.get(
        url("v2/usage"),
        json={"character_count": 20, "character_limit": 500000},
    )

    usage = make_translator().get_usage()

    assert usage.character.count == 20
    assert usage.character.limit == 500000
    assert usage.api_key_character is None
    assert usage.speech_to_text_minutes is None
    assert usage.speech_to_speech_minutes is None
    assert usage.products is None
    assert usage.start_time is None
    assert usage.end_time is None
    assert str(usage) == "Usage this billing period:\nCharacters: 20 of 500000"


def test_skips_non_object_product_entries(mocked):
    mocked.get(
        url("v2/usage"),
        json={
            "products": [
                "translate",
                None,
                {"product_type": "write", "api_key_unit_count": 3},
            ]
        },
    )

    usage = make_translator().get_usage()

    assert usage.products is not None
    assert [
        (p.product_type, p.api_key_unit_count) for p in usage.products
    ] == [("write", 3)]


def test_ignores_unparseable_billing_period(mocked):
    mocked.get(
        url("v2/usage"),
        json={
            "character_count": 20,
            "character_limit": 500000,
            "start_time": "not a timestamp",
            "end_time": "",
        },
    )

    usage = make_translator().get_usage()

    assert usage.character.count == 20
    assert usage.start_time is None
    assert usage.end_time is None
