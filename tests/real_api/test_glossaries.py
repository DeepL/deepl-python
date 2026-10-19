# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .client import make_translator
from .helpers import get_unique_name, get_when_visible


def test_sends_glossary_requests_create_get_list_entries_and_delete():
    translator = make_translator()
    name = get_unique_name("glossary")
    entries = {"Hello": "Hallo"}

    created = translator.create_glossary(name, "EN", "DE", entries)
    try:
        assert created.glossary_id
        assert created.name == name
        assert (created.source_lang, created.target_lang) == ("EN", "DE")
        assert created.entry_count == 1

        fetched = get_when_visible(
            lambda: translator.get_glossary(created.glossary_id)
        )
        assert fetched.glossary_id == created.glossary_id
        assert fetched.creation_time == created.creation_time

        listed = translator.list_glossaries()
        assert created.glossary_id in [g.glossary_id for g in listed]

        assert translator.get_glossary_entries(created) == entries
    finally:
        translator.delete_glossary(created.glossary_id)
