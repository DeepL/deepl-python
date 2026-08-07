# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .conftest import needs_real_server
import deepl
import pytest

INVALID_GLOSSARY_ID = "invalid_glossary_id"
NONEXISTENT_GLOSSARY_ID = "96ab91fd-e715-41a1-adeb-5d701f84a483"


def test_glossary_create(
    translator, glossary_name, cleanup_matching_glossaries
):
    source_lang = "EN"
    target_lang = "DE"
    try:
        glossary = translator.create_glossary(
            glossary_name, source_lang, target_lang, {"Hello": "Hallo"}
        )
        assert glossary.name == glossary_name
        assert glossary.source_lang == source_lang
        assert glossary.target_lang == target_lang
        # Note: ready field is indeterminate
        # Note: creation_time according to server might differ from local clock
        assert glossary.entry_count == 1

        get_result = translator.get_glossary(glossary.glossary_id)
        assert get_result.name == glossary.name
        assert get_result.source_lang == glossary.source_lang
        assert get_result.target_lang == glossary.target_lang
        assert get_result.creation_time == glossary.creation_time
        assert get_result.entry_count == glossary.entry_count
    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_create_csv(
    translator,
    glossary_name,
    cleanup_matching_glossaries,
    example_glossary_csv,
    example_glossary_csv_entries,
):
    source_lang = "EN"
    target_lang = "DE"
    try:
        with open(example_glossary_csv, "r") as csv_data:
            glossary = translator.create_glossary_from_csv(
                glossary_name, source_lang, target_lang, csv_data=csv_data
            )
        assert glossary.entry_count == len(example_glossary_csv_entries)

        entries = translator.get_glossary_entries(glossary.glossary_id)
        assert entries == example_glossary_csv_entries
    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_create_invalid(
    translator, glossary_name, cleanup_matching_glossaries
):
    try:
        with pytest.raises(ValueError):
            translator.create_glossary("", "EN", "DE", {"Hello": "Hallo"})
        with pytest.raises(deepl.DeepLException):
            translator.create_glossary(
                glossary_name, "EN", "XX", {"Hello": "Hallo"}
            )
        with pytest.raises(ValueError):
            translator.create_glossary(glossary_name, "EN", "DE", {})

    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name == glossary_name
        )


def test_glossary_create_large(translator, glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    entries = {f"Source-${i}": f"Target-${i}" for i in range(10000)}
    with glossary_manager(
        source_lang=source_lang, target_lang=target_lang, entries=entries
    ) as created_glossary:
        assert created_glossary.entry_count == len(entries)

        retrieved_entries = translator.get_glossary_entries(created_glossary)
        assert entries == retrieved_entries


def test_glossary_get(translator, glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    entries = {"Hello": "Hallo"}
    with glossary_manager(
        source_lang=source_lang, target_lang=target_lang, entries=entries
    ) as created_glossary:
        glossary = translator.get_glossary(created_glossary.glossary_id)
        assert glossary.glossary_id == created_glossary.glossary_id
        assert glossary.name == created_glossary.name
        assert glossary.source_lang == source_lang
        assert glossary.target_lang == target_lang
        assert glossary.entry_count == len(entries)

    with pytest.raises(deepl.DeepLException):
        translator.get_glossary(INVALID_GLOSSARY_ID)
    with pytest.raises(deepl.GlossaryNotFoundException):
        translator.get_glossary(NONEXISTENT_GLOSSARY_ID)


def test_glossary_get_entries(translator, glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    entries = {
        "Apple": "Apfel",
        "Banana": "Banane",
        "A%=&": "B&=%",
        "\u0394\u3041": "\u6df1",
        "\U0001faa8": "\U0001fab5",
    }
    with glossary_manager(
        source_lang=source_lang, target_lang=target_lang, entries=entries
    ) as created_glossary:
        assert translator.get_glossary_entries(created_glossary) == entries
        assert (
            translator.get_glossary_entries(created_glossary.glossary_id)
            == entries
        )

    with pytest.raises(deepl.DeepLException):
        translator.get_glossary_entries(INVALID_GLOSSARY_ID)
    with pytest.raises(deepl.GlossaryNotFoundException):
        translator.get_glossary_entries(NONEXISTENT_GLOSSARY_ID)


def test_glossary_list(translator, glossary_manager):
    with glossary_manager("EN", "DE", {"Hello": "Hallo"}) as created_glossary:
        glossaries = translator.list_glossaries()
        assert any(
            glossary.name == created_glossary.name for glossary in glossaries
        )


def test_glossary_delete(translator, glossary_manager):
    with glossary_manager() as created_glossary:
        translator.delete_glossary(created_glossary)
        with pytest.raises(deepl.GlossaryNotFoundException):
            translator.get_glossary(created_glossary.glossary_id)

    with pytest.raises(deepl.DeepLException):
        translator.delete_glossary(INVALID_GLOSSARY_ID)
    with pytest.raises(deepl.GlossaryNotFoundException):
        translator.delete_glossary(NONEXISTENT_GLOSSARY_ID)


@needs_real_server
def test_glossary_translate_text_sentence(translator, glossary_manager):
    source_lang = "EN"
    target_lang = "DE"
    input_text = "The artist was awarded a prize."
    with glossary_manager(
        source_lang=source_lang,
        target_lang=target_lang,
        entries={"artist": "Maler", "prize": "Gewinn"},
    ) as created_glossary:
        result = translator.translate_text(
            input_text,
            source_lang="EN",
            target_lang="DE",
            glossary=created_glossary,
        )
        assert "Maler" in result.text
        assert "Gewinn" in result.text


def test_glossary_translate_text_basic(translator, glossary_manager):
    texts_en = ["Apple", "Banana"]
    texts_de = ["Apfel", "Banane"]
    entries_ende = {en: de for en, de in zip(texts_en, texts_de)}
    entries_deen = {de: en for de, en in zip(texts_de, texts_en)}
    with glossary_manager(
        source_lang="EN",
        target_lang="DE",
        entries=entries_ende,
        glossary_name_suffix="_ende",
    ) as glossary_ende, glossary_manager(
        source_lang="DE",
        target_lang="EN",
        entries=entries_deen,
        glossary_name_suffix="_deen",
    ) as glossary_deen:

        result = translator.translate_text_with_glossary(
            texts_en, glossary_ende
        )
        assert [r.text for r in result] == texts_de

        # Using glossary with target=EN is possible, British English is assumed
        result = translator.translate_text_with_glossary(
            texts_de, glossary_deen
        )
        assert [r.text for r in result] == texts_en

        # Can override to American English
        result = translator.translate_text_with_glossary(
            texts_de, glossary_deen, target_lang="EN-US"
        )
        assert [r.text for r in result] == texts_en

        result = translator.translate_text(
            texts_de,
            source_lang="DE",
            target_lang="EN-US",
            glossary=glossary_deen.glossary_id,
        )
        assert [r.text for r in result] == texts_en
        result = translator.translate_text(
            texts_de,
            source_lang="DE",
            target_lang="EN-US",
            glossary=glossary_deen,
        )
        assert [r.text for r in result] == texts_en


def test_glossary_translate_document(
    translator,
    glossary_manager,
    example_document_path,
    output_document_path,
):
    input_text = "artist\nprize"
    expected_output_text = "Maler\nGewinn"
    example_document_path.write_text(input_text)

    with glossary_manager(
        entries={"artist": "Maler", "prize": "Gewinn"},
        source_lang="EN",
        target_lang="DE",
    ) as glossary:
        translator.translate_document_from_filepath(
            example_document_path,
            output_path=output_document_path,
            source_lang="EN",
            target_lang="DE",
            glossary=glossary,
        )
        assert expected_output_text == output_document_path.read_text()


def test_glossary_ids_translate_text_basic(translator, glossary_manager):
    texts_en = ["Apple", "Banana"]
    texts_de = ["Apfel", "Banane"]
    entries_apple = {"Apple": "Apfel"}
    entries_banana = {"Banana": "Banane"}
    with glossary_manager(
        source_lang="EN",
        target_lang="DE",
        entries=entries_apple,
        glossary_name_suffix="_apple",
    ) as glossary_apple, glossary_manager(
        source_lang="EN",
        target_lang="DE",
        entries=entries_banana,
        glossary_name_suffix="_banana",
    ) as glossary_banana:
        # glossary_ids accepts GlossaryInfo objects
        result = translator.translate_text(
            texts_en,
            source_lang="EN",
            target_lang="DE",
            glossary_ids=[glossary_apple, glossary_banana],
        )
        assert [r.text for r in result] == texts_de

        # glossary_ids accepts raw glossary ID strings
        result = translator.translate_text(
            texts_en,
            source_lang="EN",
            target_lang="DE",
            glossary_ids=[
                glossary_apple.glossary_id,
                glossary_banana.glossary_id,
            ],
        )
        assert [r.text for r in result] == texts_de


def test_glossary_ids_translate_document(
    translator,
    glossary_manager,
    example_document_path,
    output_document_path,
):
    input_text = "artist\nprize"
    expected_output_text = "Maler\nGewinn"
    example_document_path.write_text(input_text)

    with glossary_manager(
        entries={"artist": "Maler"},
        source_lang="EN",
        target_lang="DE",
        glossary_name_suffix="_artist",
    ) as glossary_artist, glossary_manager(
        entries={"prize": "Gewinn"},
        source_lang="EN",
        target_lang="DE",
        glossary_name_suffix="_prize",
    ) as glossary_prize:
        translator.translate_document_from_filepath(
            example_document_path,
            output_path=output_document_path,
            source_lang="EN",
            target_lang="DE",
            glossary_ids=[glossary_artist, glossary_prize],
        )
        assert expected_output_text == output_document_path.read_text()


def test_glossary_ids_translate_text_invalid(translator, glossary_manager):
    text = "Test"
    with glossary_manager(
        source_lang="EN", target_lang="DE", glossary_name_suffix="_ende"
    ) as glossary_ende, glossary_manager(
        source_lang="EN", target_lang="DE", glossary_name_suffix="_ende2"
    ) as glossary_ende2:
        # glossary_ids requires source_lang
        with pytest.raises(ValueError, match="source_lang is required"):
            translator.translate_text(
                text,
                target_lang="DE",
                glossary_ids=[glossary_ende],
            )

        # glossary_ids cannot be combined with glossary
        with pytest.raises(
            ValueError, match="cannot be used together with the glossary"
        ):
            translator.translate_text(
                text,
                source_lang="EN",
                target_lang="DE",
                glossary=glossary_ende,
                glossary_ids=[glossary_ende2],
            )

        # glossary_ids must not contain more than 5 IDs
        with pytest.raises(
            ValueError, match="not contain more than 5 glossary IDs"
        ):
            translator.translate_text(
                text,
                source_lang="EN",
                target_lang="DE",
                glossary_ids=[glossary_ende.glossary_id] * 6,
            )


def test_glossary_translate_text_invalid(translator, glossary_manager):
    text = "Test"
    with glossary_manager(
        source_lang="EN", target_lang="DE", glossary_name_suffix="_ende"
    ) as glossary_ende, glossary_manager(
        source_lang="DE", target_lang="EN", glossary_name_suffix="_deen"
    ) as glossary_deen:
        with pytest.raises(ValueError, match="source_lang is required"):
            translator.translate_text(
                text, target_lang="DE", glossary=glossary_ende
            )

        with pytest.raises(ValueError, match="lang must match glossary"):
            translator.translate_text(
                text,
                source_lang="DE",
                target_lang="EN",
                glossary=glossary_ende,
            )

        with pytest.raises(
            deepl.DeepLException, match='target_lang="EN" is deprecated'
        ):
            translator.translate_text(
                text,
                source_lang="DE",
                target_lang="EN",
                glossary=glossary_deen.glossary_id,
            )

        with pytest.raises(ValueError, match="GlossaryInfo"):
            translator.translate_text_with_glossary(
                text,
                glossary=glossary_deen.glossary_id,
            )
