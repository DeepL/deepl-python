# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import pathlib
import pytest

from .conftest import example_text, needs_mock_server

DEFAULT_TM_ID = "a74d88fb-ed2a-4943-a664-a4512398b994"

EXAMPLE_TMX = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<tmx version="1.4"><body>'
    '<tu><tuv xml:lang="de"><seg>Hallo</seg></tuv>'
    '<tuv xml:lang="en"><seg>Hello</seg></tuv></tu>'
    "</body></tmx>\n"
)


@pytest.fixture
def example_tmx_path(tmpdir):
    path = pathlib.Path(tmpdir) / "example.tmx"
    path.write_text(EXAMPLE_TMX)
    return path


@pytest.fixture
def imported_translation_memory(deepl_client, example_tmx_path):
    """Imports a translation memory and yields its ID, deleting it
    afterwards."""
    job = deepl_client.import_translation_memory_from_filepath(
        example_tmx_path, display_name="Test TM"
    )
    translation_memory_id = job.result.translation_memory_id
    yield translation_memory_id
    try:
        deepl_client.delete_translation_memory(translation_memory_id)
    except deepl.DeepLException:
        pass


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


@needs_mock_server
def test_get_translation_memory(deepl_client):
    translation_memory = deepl_client.get_translation_memory(DEFAULT_TM_ID)

    assert translation_memory.translation_memory_id == DEFAULT_TM_ID
    assert translation_memory.name
    assert translation_memory.source_language
    assert isinstance(translation_memory.target_languages, list)
    assert isinstance(translation_memory.segment_count, int)
    assert translation_memory.creation_time is not None
    assert translation_memory.updated_time is not None


@needs_mock_server
def test_get_translation_memory_accepts_info_object(deepl_client):
    listed = deepl_client.list_translation_memories()[0]

    translation_memory = deepl_client.get_translation_memory(listed)

    assert (
        translation_memory.translation_memory_id
        == listed.translation_memory_id
    )


@needs_mock_server
def test_get_translation_memory_not_found(deepl_client):
    with pytest.raises(deepl.DeepLException):
        deepl_client.get_translation_memory(
            "00000000-0000-0000-0000-000000000000"
        )


@needs_mock_server
def test_list_translation_memory_segments(deepl_client):
    page = deepl_client.list_translation_memory_segments(DEFAULT_TM_ID)

    assert len(page.segments) > 0
    assert page.segment_count > 0
    segment = page.segments[0]
    assert segment.source_segment_id
    assert segment.source_text
    assert len(segment.targets) > 0
    assert segment.targets[0].target_language
    assert segment.targets[0].target_text


@needs_mock_server
def test_list_translation_memory_segments_pagination(deepl_client):
    first = deepl_client.list_translation_memory_segments(
        DEFAULT_TM_ID, page_size=5
    )

    assert len(first.segments) == 5
    assert first.next_page_cursor is not None

    second = deepl_client.list_translation_memory_segments(
        DEFAULT_TM_ID, page_size=5, page_cursor=first.next_page_cursor
    )

    assert len(second.segments) > 0
    first_ids = {segment.source_segment_id for segment in first.segments}
    second_ids = {segment.source_segment_id for segment in second.segments}
    assert first_ids.isdisjoint(second_ids)


@needs_mock_server
def test_list_translation_memory_segments_filter(deepl_client):
    unfiltered = deepl_client.list_translation_memory_segments(DEFAULT_TM_ID)
    filtered = deepl_client.list_translation_memory_segments(
        DEFAULT_TM_ID, filter_text="Nummer 7"
    )

    assert len(filtered.segments) < len(unfiltered.segments)
    # segment_count is TM-level metadata and unaffected by the filter
    assert filtered.segment_count == unfiltered.segment_count


@needs_mock_server
def test_import_translation_memory_from_filepath(
    deepl_client, example_tmx_path
):
    job = deepl_client.import_translation_memory_from_filepath(
        example_tmx_path, display_name="Imported TM"
    )

    assert job.operation == "import"
    assert job.product == "translation_memory"
    assert job.done
    assert job.ok
    assert job.result.status == "completed"
    assert job.result.translation_memory_id

    imported = deepl_client.get_translation_memory(
        job.result.translation_memory_id
    )
    assert imported.name == "Imported TM"

    deepl_client.delete_translation_memory(imported)


@needs_mock_server
def test_create_translation_memory_import_awaits_upload(
    deepl_client, example_tmx_path
):
    created = deepl_client.create_translation_memory_import(
        file_name=example_tmx_path.name,
        content_length=example_tmx_path.stat().st_size,
        display_name="Awaiting Upload TM",
    )

    assert created.job_id
    assert created.upload_url

    job = deepl_client.get_translation_memory_job(created.job_id)
    assert job.status == "awaiting_input"
    assert job.result.required_action
    assert not job.done


@needs_mock_server
def test_create_translation_memory_import_rejects_invalid_file(deepl_client):
    with pytest.raises(ValueError):
        deepl_client.create_translation_memory_import("", 100)
    with pytest.raises(ValueError):
        deepl_client.create_translation_memory_import("example.tmx", 0)


@needs_mock_server
def test_export_translation_memory_to_filepath(
    deepl_client, imported_translation_memory, tmpdir
):
    output_path = pathlib.Path(tmpdir) / "exported.tmx"

    job = deepl_client.export_translation_memory_to_filepath(
        imported_translation_memory, output_path
    )

    assert job.operation == "export"
    assert job.done
    assert job.ok
    assert output_path.exists()
    assert "<tmx" in output_path.read_text()


@needs_mock_server
def test_create_translation_memory_export_reuses_completed_job(
    deepl_client, imported_translation_memory
):
    created = deepl_client.create_translation_memory_export(
        imported_translation_memory
    )
    assert not created.reused_existing
    assert created.translation_memory_id == imported_translation_memory
    deepl_client.wait_until_translation_memory_job_done(created.job_id)

    reused = deepl_client.create_translation_memory_export(
        imported_translation_memory
    )
    assert reused.reused_existing
    assert reused.job_id == created.job_id


@needs_mock_server
def test_get_translation_memory_job_not_found(deepl_client):
    with pytest.raises(deepl.DeepLException):
        deepl_client.get_translation_memory_job(
            "00000000-0000-0000-0000-000000000000"
        )


@needs_mock_server
def test_delete_translation_memory(deepl_client, example_tmx_path):
    job = deepl_client.import_translation_memory_from_filepath(
        example_tmx_path
    )
    translation_memory_id = job.result.translation_memory_id

    deepl_client.delete_translation_memory(translation_memory_id)

    with pytest.raises(deepl.DeepLException):
        deepl_client.get_translation_memory(translation_memory_id)


@needs_mock_server
def test_import_polls_through_awaiting_input(
    server, deepl_client, example_tmx_path
):
    """The API detects the uploaded file asynchronously, so an import job keeps
    reporting "awaiting_input" for a while after the upload. The wait loop must
    poll through that status rather than treating it as an error."""
    # Two polls: one consumed by the explicit check below, one that forces
    # wait_until_translation_memory_job_done to actually loop.
    server.set_tm_job_processing_polls(2)

    created = deepl_client.create_translation_memory_import(
        file_name=example_tmx_path.name,
        content_length=example_tmx_path.stat().st_size,
        display_name="Polling TM",
    )
    with open(example_tmx_path, "rb") as input_file:
        deepl_client.upload_translation_memory_file(created, input_file)

    # Still awaiting_input immediately after the upload, exactly as in
    # production, where this persists for roughly 30 seconds.
    assert (
        deepl_client.get_translation_memory_job(created.job_id).status
        == "awaiting_input"
    )

    job = deepl_client.wait_until_translation_memory_job_done(
        created.job_id, timeout_s=60
    )

    assert job.status == "completed"
    assert job.result.translation_memory_id
    deepl_client.delete_translation_memory(job.result.translation_memory_id)
