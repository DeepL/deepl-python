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


def test_url_encodes_the_id_in_the_path(mocked):
    mocked.delete(url("v3/spoken-terms/a%2Fb%3Fc"), status=204)

    make_deepl_client().delete_spoken_terms("a/b?c")


def test_strips_terms_before_sending(mocked):
    mocked.put(
        url("v3/spoken-terms/st-1/term-lists"),
        json={"lang": "en", "entry_count": 2},
        match=json_request({"lang": "en", "entries": "DeepL\nwebhook"}),
    )

    make_deepl_client().replace_spoken_terms_list(
        "st-1", deepl.SpokenTermsEntries("en", [" DeepL ", "webhook\t"])
    )


def test_rejects_a_whitespace_only_term(mocked):
    with pytest.raises(ValueError, match="not a valid string"):
        make_deepl_client().create_spoken_terms(
            "terms", [deepl.SpokenTermsEntries("en", ["a", "  "])]
        )


@pytest.mark.parametrize(
    "method, path, body, call",
    [
        (
            "POST",
            "v3/spoken-terms",
            {"name": "terms"},
            lambda c: c.create_spoken_terms("terms", []),
        ),
        (
            "GET",
            "v3/spoken-terms/st-1",
            {**SPOKEN_TERMS_JSON, "creation_time": "yesterday"},
            lambda c: c.get_spoken_terms("st-1"),
        ),
        (
            "PATCH",
            "v3/spoken-terms/st-1",
            "not json",
            lambda c: c.update_spoken_terms("st-1", name="renamed"),
        ),
        (
            "GET",
            "v3/spoken-terms",
            {"spoken_terms": [{"name": "terms"}]},
            lambda c: c.list_spoken_terms(),
        ),
        (
            "GET",
            "v3/spoken-terms/st-1/entries",
            "not json",
            lambda c: c.get_spoken_terms_entries("st-1", "en"),
        ),
        (
            "PUT",
            "v3/spoken-terms/st-1/term-lists",
            {"lang": "en", "entry_count": "many"},
            lambda c: c.replace_spoken_terms_list(
                "st-1", deepl.SpokenTermsEntries("en", ["a"])
            ),
        ),
    ],
)
def test_raises_deepl_exception_on_a_malformed_response(
    mocked, method, path, body, call
):
    if isinstance(body, dict):
        mocked.add(method, url(path), json=body)
    else:
        mocked.add(method, url(path), body=body)

    with pytest.raises(deepl.DeepLException, match="Malformed"):
        call(make_deepl_client())


def test_sends_extra_body_parameters_last(mocked):
    mocked.post(
        url("v3/spoken-terms"),
        json=SPOKEN_TERMS_JSON,
        status=201,
        match=json_request({"name": "override", "term_lists": [], "x": 1}),
    )
    mocked.patch(
        url("v3/spoken-terms/st-1"),
        json=SPOKEN_TERMS_JSON,
        match=json_request({"name": "renamed", "x": True}),
    )
    mocked.put(
        url("v3/spoken-terms/st-1/term-lists"),
        json={"lang": "de", "entry_count": 1},
        match=json_request({"lang": "de", "entries": "a", "x": None}),
    )
    client = make_deepl_client()

    client.create_spoken_terms(
        "terms", [], extra_body_parameters={"name": "override", "x": 1}
    )
    client.update_spoken_terms(
        "st-1", name="renamed", extra_body_parameters={"x": True}
    )
    client.replace_spoken_terms_list(
        "st-1",
        deepl.SpokenTermsEntries("en", ["a"]),
        extra_body_parameters={"lang": "de", "x": None},
    )
