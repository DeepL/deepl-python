# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .conftest import example_text, needs_mock_server

DEFAULT_TM_ID = "a74d88fb-ed2a-4943-a664-a4512398b994"


@needs_mock_server
def test_list_translation_memories(deepl_client):
    translation_memories = deepl_client.list_translation_memories()

    assert isinstance(translation_memories, list)
    assert len(translation_memories) > 0
    assert translation_memories[0].translation_memory_id is not None
    assert translation_memories[0].name is not None
    assert translation_memories[0].source_language is not None
    assert isinstance(translation_memories[0].target_languages, list)
    assert isinstance(translation_memories[0].segment_count, int)


@needs_mock_server
def test_translate_text_with_translation_memory(deepl_client):
    _ = deepl_client.translate_text(
        example_text["DE"],
        target_lang="EN-US",
        translation_memory=DEFAULT_TM_ID,
    )


@needs_mock_server
def test_translate_text_with_translation_memory_and_threshold(deepl_client):
    _ = deepl_client.translate_text(
        example_text["DE"],
        target_lang="EN-US",
        translation_memory=DEFAULT_TM_ID,
        translation_memory_threshold=80,
    )


@needs_mock_server
def test_translate_document_with_translation_memory(
    deepl_client,
    example_document_path,
    output_document_path,
):
    example_document_path.write_text(example_text["DE"])
    deepl_client.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        source_lang="DE",
        target_lang="EN-US",
        translation_memory=DEFAULT_TM_ID,
    )


@needs_mock_server
def test_translate_document_with_translation_memory_and_threshold(
    deepl_client,
    example_document_path,
    output_document_path,
):
    example_document_path.write_text(example_text["DE"])
    deepl_client.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        source_lang="DE",
        target_lang="EN-US",
        translation_memory=DEFAULT_TM_ID,
        translation_memory_threshold=80,
    )
