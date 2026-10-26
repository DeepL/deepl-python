# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime

import deepl
import pytest

from .client import make_deepl_client, url
from .matchers import bodyless_request, json_request

SPOKEN_TERMS_JSON = {
    "spoken_terms_id": "st-1",
    "name": "terms",
    "creation_time": "2026-10-23T17:15:53.434769Z",
    "term_lists": [{"lang": "en", "entry_count": 2}],
}


def test_joins_entries_with_newlines_and_splits_them_on_read(mocked):
    mocked.post(
        url("v3/spoken-terms"),
        json=SPOKEN_TERMS_JSON,
        status=201,
        match=json_request(
            {
                "name": "terms",
                "term_lists": [{"lang": "en", "entries": "a\nb"}],
            }
        ),
    )
    mocked.get(
        url("v3/spoken-terms/st-1/entries"),
        json={"lang": "en", "entries": "a\nb\n"},
        match=bodyless_request({"lang": "en"}),
    )
    client = make_deepl_client()

    created = client.create_spoken_terms(
        "terms", [deepl.SpokenTermsEntries("en", ["a", "b"])]
    )
    entries = client.get_spoken_terms_entries(created, "en")

    assert created.creation_time == datetime.datetime(
        2026, 10, 23, 17, 15, 53, 434769, tzinfo=datetime.timezone.utc
    )
    assert entries.entries == ["a", "b"]


def test_sends_only_the_given_fields_when_updating(mocked):
    mocked.patch(
        url("v3/spoken-terms/st-1"),
        json={k: v for k, v in SPOKEN_TERMS_JSON.items() if k != "term_lists"},
        match=json_request({"name": "renamed"}),
    )

    updated = make_deepl_client().update_spoken_terms("st-1", name="renamed")

    assert updated.term_lists == []


def test_rejects_a_term_with_a_newline_without_sending_a_request(mocked):
    with pytest.raises(ValueError, match="invalid character"):
        make_deepl_client().create_spoken_terms(
            "terms", [deepl.SpokenTermsEntries("en", ["a\nb"])]
        )
