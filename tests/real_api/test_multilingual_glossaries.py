# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.api_data import MultilingualGlossaryDictionaryEntries

from .client import make_deepl_client
from .helpers import get_unique_name, get_when_visible


def test_sends_multilingual_glossary_requests_from_create_to_delete():
    client = make_deepl_client()
    name = get_unique_name("multilingual-glossary")
    renamed = get_unique_name("multilingual-glossary-renamed")
    english_to_german = MultilingualGlossaryDictionaryEntries(
        "EN", "DE", {"Hello": "Hallo"}
    )
    german_to_english = MultilingualGlossaryDictionaryEntries(
        "DE", "EN", {"Hallo": "Hello"}
    )

    created = client.create_multilingual_glossary(
        name, [english_to_german, german_to_english]
    )
    try:
        assert created.glossary_id
        assert created.name == name
        assert {
            (d.source_lang, d.target_lang) for d in created.dictionaries
        } == {
            ("EN", "DE"),
            ("DE", "EN"),
        }

        fetched = get_when_visible(
            lambda: client.get_multilingual_glossary(created.glossary_id)
        )
        assert fetched.glossary_id == created.glossary_id

        listed = client.list_multilingual_glossaries()
        assert created.glossary_id in [g.glossary_id for g in listed]

        entries = client.get_multilingual_glossary_entries(created, "EN", "DE")
        assert [
            (d.source_lang.upper(), d.target_lang.upper())
            for d in entries.dictionaries
        ] == [("EN", "DE")]

        assert (
            client.update_multilingual_glossary_name(created, renamed).name
            == renamed
        )

        replaced = client.replace_multilingual_glossary_dictionary(
            created,
            MultilingualGlossaryDictionaryEntries(
                "EN", "DE", {"Goodbye": "Tschuess", "Yes": "Ja"}
            ),
        )
        assert replaced.entry_count == 2

        client.delete_multilingual_glossary_dictionary(
            created, source_lang="DE", target_lang="EN"
        )
    finally:
        client.delete_multilingual_glossary(created.glossary_id)
