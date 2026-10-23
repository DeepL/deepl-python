# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import time

import deepl
import pytest

from .client import make_deepl_client
from .helpers import get_unique_name


def get_spoken_terms_when_visible(client, spoken_terms_id):
    """A collection that was just created can be briefly invisible."""
    for _ in range(9):
        try:
            return client.get_spoken_terms(spoken_terms_id)
        except deepl.DeepLException as e:
            if e.http_status_code != 404:
                raise
            time.sleep(1)
    return client.get_spoken_terms(spoken_terms_id)


def term_lists(spoken_terms):
    return [(t.lang, t.entry_count) for t in spoken_terms.term_lists]


def test_sends_spoken_terms_requests_from_create_to_delete():
    client = make_deepl_client()
    name = get_unique_name("spokenTerms")

    created = client.create_spoken_terms(
        name, [deepl.SpokenTermsEntries("en", ["DeepL", "webhook"])]
    )
    try:
        assert created.name == name
        assert term_lists(created) == [("en", 2)]

        fetched = get_spoken_terms_when_visible(
            client, created.spoken_terms_id
        )
        assert fetched.spoken_terms_id == created.spoken_terms_id
        assert created.spoken_terms_id in [
            s.spoken_terms_id for s in client.list_spoken_terms()
        ]

        updated = client.update_spoken_terms(
            created,
            term_lists=[deepl.SpokenTermsEntries("en", ["authentication"])],
        )
        assert term_lists(updated) == [("en", 3)]
        assert set(client.get_spoken_terms_entries(created, "en").entries) == {
            "DeepL",
            "authentication",
            "webhook",
        }

        replaced = client.replace_spoken_terms_list(
            created, deepl.SpokenTermsEntries("en", ["API"])
        )
        assert replaced.entry_count == 1
        assert client.get_spoken_terms_entries(created, "en").entries == [
            "API"
        ]

        client.replace_spoken_terms_list(
            created, deepl.SpokenTermsEntries("de", ["Schnittstelle"])
        )
        client.delete_spoken_terms_list(created, "de")
        assert term_lists(client.get_spoken_terms(created)) == [("en", 1)]
    finally:
        client.delete_spoken_terms(created.spoken_terms_id)

    with pytest.raises(deepl.DeepLException) as error:
        client.get_spoken_terms(created.spoken_terms_id)
    assert error.value.http_status_code == 404
