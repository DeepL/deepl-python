# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

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

    with pytest.warns(DeprecationWarning):
        assert usage.any_limit_exceeded
    with pytest.warns(DeprecationWarning):
        assert usage.character.limit_exceeded
