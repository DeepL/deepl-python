# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.
import re

from .conftest import (
    _make_translator,
    example_text,
    needs_mock_server,
    needs_real_server,
)
import deepl
import io
import pathlib
import pytest
import time

default_lang_args = {"target_lang": "DE", "source_lang": "EN"}


def test_translate_document_from_filepath(
    translator,
    example_document_path,
    example_document_translation,
    output_document_path,
):
    status = translator.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        **default_lang_args,
    )
    assert example_document_translation == output_document_path.read_text()
    assert status.billed_characters == len(example_text["EN"])
    assert status.status == deepl.DocumentStatus.Status.DONE
    assert status.done

    # Note: cases with invalid file paths are not tested, because standard
    #     library functions are used.


@needs_mock_server
def test_translate_document_with_retry(
    server,
    example_document_path,
    example_document_translation,
    output_document_path,
):
    server.no_response(1)

    translator = _make_translator(
        server,
        retry_config=deepl.RetryConfig(min_connection_timeout=1.0),
    )
    translator.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        **default_lang_args,
    )
    assert example_document_translation == output_document_path.read_text()


@needs_mock_server
def test_translate_document_with_waiting(
    translator,
    server,
    example_document_path,
    example_document_translation,
    output_document_path,
):
    server.set_doc_queue_time(2000)
    server.set_doc_translate_time(2000)

    translator.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        **default_lang_args,
    )
    assert example_document_translation == output_document_path.read_text()


@needs_mock_server
def test_translate_document_with_timeout_succeeds(
    translator,
    server,
    example_document_path,
    example_document_translation,
    output_document_path,
):
    server.set_doc_queue_time(2 * 1000)
    server.set_doc_translate_time(2 * 1000)

    translator.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        timeout_s=10,
        **default_lang_args,
    )
    assert example_document_translation == output_document_path.read_text()


@needs_mock_server
def test_translate_document_with_manual_timeout_fails(
    translator,
    server,
    example_document_path,
    output_document_path,
):
    server.set_doc_queue_time(11 * 1000)
    server.set_doc_translate_time(11 * 1000)

    with pytest.raises(
        deepl.DeepLException,
        match="Manual timeout of 10s exceeded for document translation",
    ):
        translator.translate_document_from_filepath(
            example_document_path,
            output_path=output_document_path,
            timeout_s=10,
            **default_lang_args,
        )


@needs_mock_server
def test_translate_large_document(
    translator, example_large_document_path, example_large_document_translation
):
    with io.BytesIO() as output_file:
        with open(example_large_document_path, "rb") as input_file:
            translator.translate_document(
                input_file, output_file, **default_lang_args
            )

        assert (
            example_large_document_translation
            == output_file.getvalue().decode()
        )


@needs_real_server
def test_translate_document_formality(
    translator, example_document_path, output_document_path
):
    example_document_path.write_text("How are you?")
    translator.translate_document_from_filepath(
        example_document_path,
        output_document_path,
        formality=deepl.Formality.MORE,
        **default_lang_args,
    )
    assert "Ihnen" in output_document_path.read_text()  # Wie geht es Ihnen?"
    translator.translate_document_from_filepath(
        example_document_path,
        output_document_path,
        formality=deepl.Formality.LESS,
        **default_lang_args,
    )
    assert "dir" in output_document_path.read_text()  # Wie geht es dir?
    example_document_path.write_text("How are you?")
    translator.translate_document_from_filepath(
        example_document_path,
        output_document_path,
        formality=deepl.Formality.PREFER_MORE,
        **default_lang_args,
    )
    assert "Ihnen" in output_document_path.read_text()
    translator.translate_document_from_filepath(
        example_document_path,
        output_document_path,
        formality=deepl.Formality.PREFER_LESS,
        **default_lang_args,
    )
    assert "dir" in output_document_path.read_text()


@needs_mock_server
def test_document_output_format(
    translator,
    example_document_path,
    output_dir_path,
):
    # Mock server supports only TXT and HTML files, so translate TXT->HTML
    example_document_path.write_text(example_text["EN"])
    output_document_path = output_dir_path / "example.html"
    translator.translate_document_from_filepath(
        example_document_path,
        output_document_path,
        **default_lang_args,
    )

    output = output_document_path.read_text()
    assert example_text["DE"] == output


def test_document_failure_during_translation(
    translator, example_document_path, output_document_path
):
    # Translating text from DE to DE will trigger error
    example_document_path.write_text(example_text["DE"])
    with pytest.raises(
        deepl.exceptions.DocumentTranslationException,
    ) as exc_info:
        translator.translate_document_from_filepath(
            example_document_path, output_document_path, target_lang="DE"
        )

    # Ensure that document translation error contains document handle
    exception = exc_info.value
    assert "Source and target language" in str(exception)
    assert exception.document_handle is not None
    match = re.compile("ID: [0-9A-F]{32}, key: [0-9A-F]{64}")
    assert match.search(str(exception)) is not None
    # document_request is a deprecated alias for document_handle
    assert exception.document_request is not None


def test_invalid_document(translator, tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output_dir = tmpdir / "output"
    output_dir.mkdir()
    input_document = tmpdir / "document.invalid"
    input_document.write_text(example_text["EN"])
    output_document = output_dir / "document.invalid"

    with pytest.raises(
        deepl.DeepLException, match="(Invalid file)|(file extension)"
    ):
        translator.translate_document_from_filepath(
            input_document, output_path=output_document, **default_lang_args
        )


@needs_mock_server
def test_translate_document_low_level(
    translator,
    example_document_path,
    example_document_translation,
    output_document_path,
    server,
):
    # Set a small document queue time to attempt downloading a queued document
    server.set_doc_queue_time(100)

    with open(example_document_path, "rb") as infile:
        handle = translator.translate_document_upload(
            infile, **default_lang_args
        )
    status = translator.translate_document_get_status(handle)
    assert status.ok and not status.done

    # Test recreating a document handle from id & key
    doc_id, doc_key = handle.document_id, handle.document_key
    del handle

    handle = deepl.DocumentHandle(doc_id, doc_key)
    status = translator.translate_document_get_status(handle)
    assert status.ok

    while status.ok and not status.done:
        status = translator.translate_document_get_status(handle)
        time.sleep(0.2)

    assert status.ok and status.done
    with open(output_document_path, "wb") as outfile:
        translator.translate_document_download(handle, outfile)

    assert output_document_path.read_text() == example_document_translation


def test_translate_document_string(translator, server):
    input_string = example_text["EN"]
    handle = translator.translate_document_upload(
        input_string,
        source_lang="EN",
        target_lang="DE",
        filename="test.txt",
    )

    status = translator.translate_document_get_status(handle)
    while status.ok and not status.done:
        status = translator.translate_document_get_status(handle)
        time.sleep(status.seconds_remaining or 1)

    assert status.ok
    response = translator.translate_document_download(handle)
    try:
        output = bytes()
        for chunk in response.iter_content(chunk_size=128):
            output += chunk
        output_string = output.decode()
        assert output_string == example_text["DE"]
    finally:
        response.close()


@needs_mock_server
def test_translate_document_request_fields(
    translator, example_document_path, server, output_document_path
):
    server.set_doc_queue_time(2000)
    server.set_doc_translate_time(2000)

    time_before = time.time()
    with open(example_document_path, "rb") as infile:
        handle = translator.translate_document_upload(
            infile, **default_lang_args
        )

    status = translator.translate_document_get_status(handle)
    assert status.ok
    while status.ok and not status.done:
        status = translator.translate_document_get_status(handle)
        assert (
            status.status == deepl.DocumentStatus.Status.QUEUED
            or status.seconds_remaining >= 0
        )
        time.sleep(0.2)

    with open(output_document_path, "wb") as outfile:
        translator.translate_document_download(handle, outfile)

    time_after = time.time()
    assert status.billed_characters == len(example_document_path.read_text())
    assert time_after - time_before > 4.0
    assert example_text["DE"] == output_document_path.read_text()


@needs_mock_server
def test_translate_document_download_generator(
    translator,
    example_large_document_path,
    output_document_path,
    example_large_document_translation,
):
    with open(example_large_document_path, "rb") as infile:
        handle = translator.translate_document_upload(
            infile, **default_lang_args
        )

    status = translator.translate_document_get_status(handle)
    while status.ok and not status.done:
        status = translator.translate_document_get_status(handle)
        time.sleep(0.2)

    assert status.ok and status.done
    response = translator.translate_document_download(handle)
    with open(output_document_path, "wb") as outfile:
        for chunk in response.iter_content(chunk_size=128):
            outfile.write(chunk)

    assert (
        output_document_path.read_text() == example_large_document_translation
    )


@needs_mock_server
def test_recreate_document_handle_invalid(translator):
    doc_id = "12AB" * 8  # IDs are 32 hex characters
    doc_key = "CD34" * 16  # Keys are 64 hex characters
    handle = deepl.DocumentHandle(doc_id, doc_key)
    with pytest.raises(deepl.DeepLException, match="Not found"):
        translator.translate_document_get_status(handle)
