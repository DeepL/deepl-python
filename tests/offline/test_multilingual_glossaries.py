# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
import io

import deepl
import pytest
from deepl.api_data import (
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryDictionaryInfo,
    MultilingualGlossaryInfo,
)

from .client import make_deepl_client, url
from .matchers import bodyless_request, json_request

GLOSSARY_JSON = {
    "glossary_id": "g-1",
    "name": "glossary",
    "creation_time": "2021-08-03T14:16:18.329Z",
    "dictionaries": [
        {"source_lang": "en", "target_lang": "de", "entry_count": 2},
        {"source_lang": "de", "target_lang": "en", "entry_count": 1},
    ],
}
DICTIONARY_JSON = {
    "source_lang": "en",
    "target_lang": "de",
    "entry_count": 2,
}
ENTRIES = MultilingualGlossaryDictionaryEntries(
    "EN-US", "de", {"Hello": "Hallo", " A ": "B "}
)
ENTRIES_BODY = {
    "source_lang": "EN",
    "target_lang": "DE",
    "entries": "Hello\tHallo\nA\tB",
    "entries_format": "tsv",
}
CSV_DATA = "Hello,Hallo,en,de\n"
CSV_ENTRIES_BODY = {
    "source_lang": "EN",
    "target_lang": "DE",
    "entries": "Hello\tHallo",
    "entries_format": "tsv",
}


def glossary_info():
    return MultilingualGlossaryInfo.from_json(GLOSSARY_JSON)


def test_sends_all_dictionaries_when_creating_glossary(mocked):
    mocked.post(
        url("v3/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(
            {
                "name": "glossary",
                "dictionaries": [
                    ENTRIES_BODY,
                    {
                        "source_lang": "DE",
                        "target_lang": "EN",
                        "entries": "Hallo\tHello",
                        "entries_format": "tsv",
                    },
                ],
            }
        ),
    )

    make_deepl_client().create_multilingual_glossary(
        "glossary",
        [
            ENTRIES,
            MultilingualGlossaryDictionaryEntries(
                "DE", "EN-GB", {"Hallo": "Hello"}
            ),
        ],
    )


@pytest.mark.parametrize("csv_data", [CSV_DATA, CSV_DATA.encode("utf-8")])
def test_sends_csv_entries_as_tsv_when_creating_glossary(mocked, csv_data):
    mocked.post(
        url("v3/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(
            {"name": "glossary", "dictionaries": [CSV_ENTRIES_BODY]}
        ),
    )

    make_deepl_client().create_multilingual_glossary_from_csv(
        "glossary", "EN", "DE", csv_data
    )


def test_sends_csv_file_content_as_tsv_when_creating_glossary(mocked):
    mocked.post(
        url("v3/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(
            {"name": "glossary", "dictionaries": [CSV_ENTRIES_BODY]}
        ),
    )

    make_deepl_client().create_multilingual_glossary_from_csv(
        "glossary", "EN", "DE", io.StringIO(CSV_DATA)
    )


def test_raises_when_creating_glossary_with_invalid_input():
    client = make_deepl_client()

    with pytest.raises(ValueError, match="name must not be empty"):
        client.create_multilingual_glossary("", [ENTRIES])
    with pytest.raises(ValueError, match="entries must not be empty"):
        client.create_multilingual_glossary(
            "glossary",
            [ENTRIES, MultilingualGlossaryDictionaryEntries("EN", "DE", {})],
        )
    with pytest.raises(ValueError, match="not a valid string"):
        client.create_multilingual_glossary(
            "glossary",
            [MultilingualGlossaryDictionaryEntries("EN", "DE", {"": "a"})],
        )


def test_raises_when_glossary_csv_has_duplicate_source_terms():
    with pytest.raises(ValueError, match="duplicates source term"):
        make_deepl_client().create_multilingual_glossary_from_csv(
            "glossary", "EN", "DE", "a,b\na,c\n"
        )


def test_parses_glossary_info_with_dictionaries(mocked):
    mocked.get(url("v3/glossaries/g-1"), json=GLOSSARY_JSON)

    glossary = make_deepl_client().get_multilingual_glossary("g-1")

    assert glossary.creation_time == datetime.datetime(
        2021, 8, 3, 14, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert [(d.source_lang, d.target_lang) for d in glossary.dictionaries] == [
        ("EN", "DE"),
        ("DE", "EN"),
    ]
    assert str(glossary) == 'MultilingualGlossary "glossary" (g-1)'


def test_sends_get_when_getting_glossary(mocked):
    mocked.get(
        url("v3/glossaries/g-1"),
        json=GLOSSARY_JSON,
        match=bodyless_request(),
    )

    make_deepl_client().get_multilingual_glossary("g-1")


def test_parses_glossary_list(mocked):
    mocked.get(
        url("v3/glossaries"),
        json={"glossaries": [GLOSSARY_JSON, {**GLOSSARY_JSON, "name": "b"}]},
        match=bodyless_request(),
    )

    glossaries = make_deepl_client().list_multilingual_glossaries()

    assert len(glossaries) == 2


@pytest.mark.parametrize("glossary", ["g-1", glossary_info()])
def test_sends_new_name_when_renaming_glossary(mocked, glossary):
    mocked.patch(
        url("v3/glossaries/g-1"),
        json=GLOSSARY_JSON,
        match=json_request({"name": "new name"}),
    )

    make_deepl_client().update_multilingual_glossary_name(glossary, "new name")


def test_raises_when_renaming_glossary_to_empty_name():
    with pytest.raises(ValueError, match="name must not be empty"):
        make_deepl_client().update_multilingual_glossary_name("g-1", "")


@pytest.mark.parametrize("glossary", ["g-1", glossary_info()])
def test_sends_dictionary_when_updating_glossary_dictionary(mocked, glossary):
    mocked.patch(
        url("v3/glossaries/g-1"),
        json=GLOSSARY_JSON,
        match=json_request({"dictionaries": [ENTRIES_BODY]}),
    )

    make_deepl_client().update_multilingual_glossary_dictionary(
        glossary, ENTRIES
    )


def test_sends_csv_entries_when_updating_glossary_dictionary(mocked):
    mocked.patch(
        url("v3/glossaries/g-1"),
        json=GLOSSARY_JSON,
        match=json_request({"dictionaries": [CSV_ENTRIES_BODY]}),
    )

    make_deepl_client().update_multilingual_glossary_dictionary_from_csv(
        glossary_info(), "EN", "DE", CSV_DATA
    )


@pytest.mark.parametrize("glossary", ["g-1", glossary_info()])
def test_sends_put_when_replacing_glossary_dictionary(mocked, glossary):
    mocked.put(
        url("v3/glossaries/g-1/dictionaries"),
        json=DICTIONARY_JSON,
        match=json_request(ENTRIES_BODY),
    )

    result = make_deepl_client().replace_multilingual_glossary_dictionary(
        glossary, ENTRIES
    )

    assert isinstance(result, MultilingualGlossaryDictionaryInfo)
    assert (result.source_lang, result.target_lang) == ("EN", "DE")


def test_sends_csv_entries_when_replacing_glossary_dictionary(mocked):
    mocked.put(
        url("v3/glossaries/g-1/dictionaries"),
        json=DICTIONARY_JSON,
        match=json_request(CSV_ENTRIES_BODY),
    )

    make_deepl_client().replace_multilingual_glossary_dictionary_from_csv(
        "g-1", "EN-US", "DE", CSV_DATA.encode("utf-8")
    )


def test_raises_when_changing_dictionary_without_entries():
    client = make_deepl_client()
    empty = MultilingualGlossaryDictionaryEntries("EN", "DE", {})

    with pytest.raises(ValueError, match="entries must not be empty"):
        client.update_multilingual_glossary_dictionary("g-1", empty)
    with pytest.raises(ValueError, match="entries must not be empty"):
        client.replace_multilingual_glossary_dictionary("g-1", empty)


def test_raises_when_changing_dictionary_without_glossary_id():
    client = make_deepl_client()

    with pytest.raises(ValueError, match="glossary id must not be empty"):
        client.update_multilingual_glossary_dictionary("", ENTRIES)
    with pytest.raises(ValueError, match="glossary id must not be empty"):
        client.replace_multilingual_glossary_dictionary("", ENTRIES)


@pytest.mark.parametrize("glossary", ["g-1", glossary_info()])
def test_sends_base_languages_when_getting_dictionary_entries(
    mocked, glossary
):
    mocked.get(
        url("v3/glossaries/g-1/entries"),
        json={
            "dictionaries": [
                {
                    "source_lang": "en",
                    "target_lang": "de",
                    "entries": "Hello\tHallo",
                }
            ]
        },
        match=bodyless_request({"source_lang": "EN", "target_lang": "DE"}),
    )

    response = make_deepl_client().get_multilingual_glossary_entries(
        glossary, "EN-US", "DE"
    )

    assert len(response.dictionaries) == 1


@pytest.mark.parametrize("glossary", ["g-1", glossary_info()])
def test_sends_delete_when_deleting_glossary(mocked, glossary):
    mocked.delete(
        url("v3/glossaries/g-1"), status=204, match=bodyless_request()
    )

    assert make_deepl_client().delete_multilingual_glossary(glossary) is None


def test_sends_language_pair_when_deleting_dictionary(mocked):
    mocked.delete(
        url("v3/glossaries/g-1/dictionaries"),
        status=204,
        match=bodyless_request({"source_lang": "EN", "target_lang": "DE"}),
    )

    make_deepl_client().delete_multilingual_glossary_dictionary(
        glossary_info(), source_lang="EN", target_lang="DE"
    )


def test_prefers_dictionary_over_languages_when_deleting_dictionary(mocked):
    mocked.delete(
        url("v3/glossaries/g-1/dictionaries"),
        status=204,
        match=bodyless_request({"source_lang": "DE", "target_lang": "EN"}),
    )
    dictionary = glossary_info().dictionaries[1]

    make_deepl_client().delete_multilingual_glossary_dictionary(
        "g-1", dictionary, source_lang="EN", target_lang="DE"
    )


def test_raises_when_deleting_dictionary_without_language_pair():
    with pytest.raises(ValueError, match="must provide dictionary or both"):
        make_deepl_client().delete_multilingual_glossary_dictionary("g-1")


@pytest.mark.parametrize(
    "method, path, call",
    [
        (
            "GET",
            "v3/glossaries/g-1",
            lambda c: c.get_multilingual_glossary("g-1"),
        ),
        (
            "DELETE",
            "v3/glossaries/g-1",
            lambda c: c.delete_multilingual_glossary("g-1"),
        ),
        (
            "PATCH",
            "v3/glossaries/g-1",
            lambda c: c.update_multilingual_glossary_name("g-1", "n"),
        ),
        (
            "PUT",
            "v3/glossaries/g-1/dictionaries",
            lambda c: c.replace_multilingual_glossary_dictionary(
                "g-1", ENTRIES
            ),
        ),
    ],
)
def test_raises_glossary_not_found_when_server_returns_404(
    mocked, method, path, call
):
    mocked.add(method, url(path), status=404, json={"message": "gone"})

    with pytest.raises(
        deepl.GlossaryNotFoundException, match="Glossary not found.*gone"
    ):
        call(make_deepl_client())
