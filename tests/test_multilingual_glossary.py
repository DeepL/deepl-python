# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl import util
from deepl.api_data import MultilingualGlossaryDictionaryEntries
from .conftest import needs_real_server
import deepl
import pytest

INVALID_GLOSSARY_ID = "invalid_glossary_id"
NONEXISTENT_GLOSSARY_ID = "96ab91fd-e715-41a1-adeb-5d701f84a483"


def test_glossary_create(
    deepl_client, glossary_name, cleanup_matching_glossaries
):
    try:
        glossary_dicts = []
        glossary_dicts.append(
            MultilingualGlossaryDictionaryEntries(
                "EN", "DE", {"Hello": "Hallo"}
            )
        )
        glossary_dicts.append(
            MultilingualGlossaryDictionaryEntries(
                "DE", "EN", {"Hallo": "Hello"}
            )
        )
        glossary = deepl_client.create_multilingual_glossary(
            glossary_name, glossary_dicts
        )
        assert glossary.name == glossary_name
        assert len(glossary.dictionaries) == len(glossary_dicts)
        for i in range(len(glossary.dictionaries)):
            assert (
                glossary.dictionaries[i].source_lang
                == glossary_dicts[i].source_lang
            )
            assert (
                glossary.dictionaries[i].target_lang
                == glossary_dicts[i].target_lang
            )
            assert glossary.dictionaries[i].entry_count == len(
                glossary_dicts[i].entries
            )

        get_result = deepl_client.get_multilingual_glossary(
            glossary.glossary_id
        )
        assert get_result.name == glossary.name
        assert get_result.creation_time == glossary.creation_time
        assert len(get_result.dictionaries) == len(glossary.dictionaries)
        for i in range(len(get_result.dictionaries)):
            assert (
                get_result.dictionaries[i].source_lang
                == glossary.dictionaries[i].source_lang
            )
            assert (
                get_result.dictionaries[i].target_lang
                == glossary.dictionaries[i].target_lang
            )
            assert (
                get_result.dictionaries[i].entry_count
                == glossary.dictionaries[i].entry_count
            )
    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_dictionary_update(
    deepl_client, glossary_name, cleanup_matching_glossaries
):
    try:
        dict_ende = MultilingualGlossaryDictionaryEntries(
            "EN", "DE", {"Hello": "Hallo"}
        )
        dict_deen = MultilingualGlossaryDictionaryEntries(
            "DE", "EN", {"Hallo": "Hello"}
        )
        glossary_dicts = [dict_deen, dict_ende]
        created_glossary = deepl_client.create_multilingual_glossary(
            glossary_name, glossary_dicts
        )
        updated_entries = {"Hello": "Guten Tag", "Apple": "Apfel"}
        updated_glossary = (
            deepl_client.update_multilingual_glossary_dictionary(
                created_glossary,
                MultilingualGlossaryDictionaryEntries(
                    "EN", "DE", updated_entries
                ),
            )
        )

        assert updated_glossary.name == created_glossary.name
        assert len(updated_glossary.dictionaries) == len(glossary_dicts)
        assert updated_glossary.dictionaries
        for glossary_dict in updated_glossary.dictionaries:
            if (
                glossary_dict.source_lang == "EN"
                and glossary_dict.target_lang == "DE"
            ):
                assert glossary_dict.entry_count == len(updated_entries)
            else:
                assert glossary_dict.source_lang == "DE"
                assert glossary_dict.target_lang == "EN"
                assert glossary_dict.entry_count == len(dict_deen.entries)
    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == updated_glossary.name
        )


def test_glossary_name_update(
    deepl_client, glossary_name, cleanup_matching_glossaries
):
    try:
        glossary_dicts = [
            MultilingualGlossaryDictionaryEntries(
                "EN", "DE", {"Hello": "Hallo"}
            )
        ]
        glossary = deepl_client.create_multilingual_glossary(
            glossary_name, glossary_dicts
        )
        new_name = "New Glossary Name"
        updated_glossary = deepl_client.update_multilingual_glossary_name(
            glossary, new_name
        )
        assert updated_glossary.name == new_name

        get_result = deepl_client.get_multilingual_glossary(
            glossary.glossary_id
        )

        assert get_result.name == updated_glossary.name

        with pytest.raises(ValueError):
            deepl_client.update_multilingual_glossary_name(glossary, "")
    finally:
        cleanup_matching_glossaries(lambda glossary: glossary.name == new_name)


def test_glossary_dictionary_replace(
    deepl_client, glossary_name, cleanup_matching_glossaries
):
    try:
        entries = {"Hello": "Hallo"}
        source_lang = "EN"
        target_lang = "DE"
        glossary_dicts = [
            MultilingualGlossaryDictionaryEntries(
                source_lang, target_lang, entries
            )
        ]
        created_glossary = deepl_client.create_multilingual_glossary(
            glossary_name, glossary_dicts
        )
        entries = {"Apple": "Apfel"}
        updated_glossary_dict = (
            deepl_client.replace_multilingual_glossary_dictionary(
                created_glossary,
                MultilingualGlossaryDictionaryEntries(
                    source_lang, target_lang, entries
                ),
            )
        )

        assert updated_glossary_dict.entry_count == len(entries)

        entries_response = deepl_client.get_multilingual_glossary_entries(
            created_glossary.glossary_id, source_lang, target_lang
        )
        assert len(entries_response.dictionaries) == len(glossary_dicts)
        assert entries_response.dictionaries[
            0
        ].entries == util.convert_dict_to_tsv(entries)

    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_create_csv(
    deepl_client,
    glossary_name,
    cleanup_matching_glossaries,
    example_glossary_csv,
    example_glossary_csv_entries,
):
    source_lang = "EN"
    target_lang = "DE"
    try:
        with open(example_glossary_csv, "r") as csv_data:
            glossary = deepl_client.create_multilingual_glossary_from_csv(
                glossary_name, source_lang, target_lang, csv_data=csv_data
            )
        assert len(glossary.dictionaries) == 1
        assert glossary.dictionaries[0].entry_count == len(
            example_glossary_csv_entries
        )
        assert glossary.dictionaries[0].source_lang == source_lang
        assert glossary.dictionaries[0].target_lang == target_lang

        entries_response = deepl_client.get_multilingual_glossary_entries(
            glossary.glossary_id, source_lang, target_lang
        )
        assert len(entries_response.dictionaries) == 1
        assert (
            util.convert_tsv_to_dict(entries_response.dictionaries[0].entries)
            == example_glossary_csv_entries
        )
    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_create_invalid(
    deepl_client, glossary_name, cleanup_matching_glossaries
):
    try:
        with pytest.raises(ValueError):
            glossary_dict = MultilingualGlossaryDictionaryEntries(
                "EN", "DE", {"Hello": "Hallo"}
            )
            deepl_client.create_multilingual_glossary("", [glossary_dict])
        with pytest.raises(deepl.DeepLException):
            glossary_dict = MultilingualGlossaryDictionaryEntries(
                "EN", "XX", {"Hallo": "Hello"}
            )
            deepl_client.create_multilingual_glossary(
                glossary_name, [glossary_dict]
            )
        with pytest.raises(ValueError):
            glossary_dict = MultilingualGlossaryDictionaryEntries(
                "EN", "XX", {}
            )
            deepl_client.create_multilingual_glossary(
                glossary_name, [glossary_dict]
            )

    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_create_large(deepl_client, multilingual_glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    entries = {f"Source-${i}": f"Target-${i}" for i in range(10000)}
    glossary_dicts = [
        MultilingualGlossaryDictionaryEntries(
            source_lang, target_lang, entries
        )
    ]
    with multilingual_glossary_manager(glossary_dicts) as created_glossary:
        assert len(created_glossary.dictionaries) == len(glossary_dicts)
        assert created_glossary.dictionaries[0].entry_count == len(entries)

        glossary_dicts = deepl_client.get_multilingual_glossary_entries(
            created_glossary, source_lang, target_lang
        ).dictionaries
        assert entries == util.convert_tsv_to_dict(glossary_dicts[0].entries)


def test_glossary_get(deepl_client, multilingual_glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    entries = {"Hello": "Hallo"}
    dictionaries = [
        MultilingualGlossaryDictionaryEntries(
            source_lang, target_lang, entries
        )
    ]
    with multilingual_glossary_manager(
        dictionaries=dictionaries
    ) as created_glossary:
        glossary = deepl_client.get_multilingual_glossary(
            created_glossary.glossary_id
        )
        assert glossary.glossary_id == created_glossary.glossary_id
        assert glossary.name == created_glossary.name

    with pytest.raises(deepl.DeepLException):
        deepl_client.get_multilingual_glossary(INVALID_GLOSSARY_ID)
    with pytest.raises(deepl.GlossaryNotFoundException):
        deepl_client.get_multilingual_glossary(NONEXISTENT_GLOSSARY_ID)


def test_glossary_get_entries(deepl_client, multilingual_glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    entries = {
        "Apple": "Apfel",
        "Banana": "Banane",
        "A%=&": "B&=%",
        "\u0394\u3041": "\u6df1",
        "\U0001faa8": "\U0001fab5",
    }
    glossary_dicts = [
        MultilingualGlossaryDictionaryEntries(
            source_lang, target_lang, entries
        )
    ]
    with multilingual_glossary_manager(glossary_dicts) as created_glossary:
        result = deepl_client.get_multilingual_glossary_entries(
            created_glossary, source_lang, target_lang
        ).dictionaries
        assert util.convert_tsv_to_dict(result[0].entries) == entries
        get_by_id_result = deepl_client.get_multilingual_glossary_entries(
            created_glossary.glossary_id, source_lang, target_lang
        ).dictionaries
        assert len(get_by_id_result) == len(glossary_dicts)
        assert util.convert_tsv_to_dict(get_by_id_result[0].entries) == entries

    with pytest.raises(deepl.DeepLException):
        deepl_client.get_multilingual_glossary_entries(
            INVALID_GLOSSARY_ID, source_lang, target_lang
        )
    with pytest.raises(deepl.GlossaryNotFoundException):
        deepl_client.get_multilingual_glossary_entries(
            NONEXISTENT_GLOSSARY_ID, source_lang, target_lang
        )


def test_glossary_list(deepl_client, multilingual_glossary_manager):
    glossary_dict = MultilingualGlossaryDictionaryEntries(
        "EN", "DE", {"Hello": "Hallo"}
    )
    with multilingual_glossary_manager([glossary_dict]) as created_glossary:
        glossaries = deepl_client.list_multilingual_glossaries()
        assert any(
            glossary.name == created_glossary.name for glossary in glossaries
        )


def test_glossary_delete(deepl_client, multilingual_glossary_manager):
    glossary_dicts = [
        MultilingualGlossaryDictionaryEntries("EN", "DE", {"Hello": "Hallo"})
    ]
    with multilingual_glossary_manager(glossary_dicts) as created_glossary:
        deepl_client.delete_multilingual_glossary(created_glossary)
        with pytest.raises(deepl.GlossaryNotFoundException):
            deepl_client.get_multilingual_glossary(
                created_glossary.glossary_id
            )

    with pytest.raises(deepl.DeepLException):
        deepl_client.delete_multilingual_glossary(INVALID_GLOSSARY_ID)
    with pytest.raises(deepl.GlossaryNotFoundException):
        deepl_client.delete_multilingual_glossary(NONEXISTENT_GLOSSARY_ID)


def test_glossary_dictionary_delete(
    deepl_client, multilingual_glossary_manager
):
    to_be_deleted = MultilingualGlossaryDictionaryEntries(
        "EN", "DE", {"Hello": "Hallo"}
    )
    to_remain = MultilingualGlossaryDictionaryEntries(
        "DE", "EN", {"Hallo": "Hello"}
    )
    glossary_dicts = [to_be_deleted, to_remain]
    with multilingual_glossary_manager(glossary_dicts) as created_glossary:
        deepl_client.delete_multilingual_glossary_dictionary(
            created_glossary,
            source_lang=to_be_deleted.source_lang,
            target_lang=to_be_deleted.target_lang,
        )
        get_result = deepl_client.get_multilingual_glossary(
            created_glossary.glossary_id
        )
        assert len(get_result.dictionaries) == len(glossary_dicts) - 1
        assert get_result.dictionaries[0].source_lang == to_remain.source_lang
        assert get_result.dictionaries[0].target_lang == to_remain.target_lang

    with pytest.raises(deepl.DeepLException):
        deepl_client.delete_multilingual_glossary_dictionary(
            INVALID_GLOSSARY_ID, source_lang="EN", target_lang="DE"
        )
    with pytest.raises(deepl.GlossaryNotFoundException):
        deepl_client.delete_multilingual_glossary_dictionary(
            NONEXISTENT_GLOSSARY_ID, source_lang="EN", target_lang="DE"
        )
    with pytest.raises(
        ValueError,
        match="must provide dictionary or both source_lang and target_lang",
    ):
        deepl_client.delete_multilingual_glossary_dictionary(created_glossary)


@needs_real_server
def test_glossary_translate_text_sentence(
    deepl_client, multilingual_glossary_manager
):
    source_lang = "EN"
    target_lang = "DE"
    input_text = "The artist was awarded a prize."
    glossary_dict = MultilingualGlossaryDictionaryEntries(
        source_lang, target_lang, {"artist": "Maler", "prize": "Gewinn"}
    )
    with multilingual_glossary_manager(
        [glossary_dict],
    ) as created_glossary:
        result = deepl_client.translate_text(
            input_text,
            source_lang="EN",
            target_lang="DE",
            glossary=created_glossary,
        )
        assert "Maler" in result.text
        assert "Gewinn" in result.text


def test_glossary_translate_text_basic(
    deepl_client, multilingual_glossary_manager
):
    texts_en = ["Apple", "Banana"]
    texts_de = ["Apfel", "Banane"]
    entries_ende = {en: de for en, de in zip(texts_en, texts_de)}
    entries_deen = {de: en for de, en in zip(texts_de, texts_en)}

    ende_dict = MultilingualGlossaryDictionaryEntries("EN", "DE", entries_ende)
    deen_dict = MultilingualGlossaryDictionaryEntries("DE", "EN", entries_deen)
    glossary_dicts = [ende_dict, deen_dict]
    with multilingual_glossary_manager(glossary_dicts) as created_glossary:

        result = deepl_client.translate_text(
            texts_de,
            source_lang="DE",
            target_lang="EN-US",
            glossary=created_glossary.glossary_id,
        )
        assert [r.text for r in result] == texts_en
        result = deepl_client.translate_text(
            texts_de,
            source_lang="DE",
            target_lang="EN-US",
            glossary=created_glossary,
        )
        assert [r.text for r in result] == texts_en


def test_glossary_translate_document(
    deepl_client,
    multilingual_glossary_manager,
    example_document_path,
    output_document_path,
):
    input_text = "artist\nprize"
    expected_output_text = "Maler\nGewinn"
    example_document_path.write_text(input_text)
    entries = {"artist": "Maler", "prize": "Gewinn"}
    glossary_dict = MultilingualGlossaryDictionaryEntries("EN", "DE", entries)
    with multilingual_glossary_manager([glossary_dict]) as glossary:
        deepl_client.translate_document_from_filepath(
            example_document_path,
            output_path=output_document_path,
            source_lang="EN",
            target_lang="DE",
            glossary=glossary,
        )
        assert expected_output_text == output_document_path.read_text()


def test_glossary_translate_text_invalid(
    deepl_client, multilingual_glossary_manager
):
    text = "Test"

    ende_dict = MultilingualGlossaryDictionaryEntries(
        "EN", "DE", {"Hello": "Hallo"}
    )
    deen_dict = MultilingualGlossaryDictionaryEntries(
        "DE", "EN", {"Hallo": "Hello"}
    )
    glossary_dicts = [ende_dict, deen_dict]
    with multilingual_glossary_manager(glossary_dicts) as glossary:
        with pytest.raises(ValueError, match="source_lang is required"):
            deepl_client.translate_text(
                text, target_lang="DE", glossary=glossary
            )

        with pytest.raises(
            ValueError,
            match="must have a glossary with a "
            "dictionary for the given source_lang and target_lang",
        ):
            deepl_client.translate_text(
                text, source_lang="ES", target_lang="DE", glossary=glossary
            )

        with pytest.raises(ValueError, match="GlossaryInfo"):
            deepl_client.translate_text_with_glossary(
                text,
                glossary=glossary.glossary_id,
            )
