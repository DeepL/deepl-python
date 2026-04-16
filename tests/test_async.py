# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import pytest

pytest.importorskip("aiohttp")

import deepl  # noqa: E402
from deepl.retry_config import RetryConfig  # noqa: E402

from .conftest import (  # noqa: E402
    _make_async_client,
    example_text,
    needs_mock_server,
)

pytestmark = pytest.mark.asyncio

default_lang_args = {"target_lang": "DE", "source_lang": "EN"}


async def test_translate_text(async_translator):
    result = await async_translator.translate_text(
        example_text["EN"], target_lang="DE"
    )
    assert example_text["DE"] == result.text
    assert "EN" == result.detected_source_lang


async def test_usage(async_translator):
    usage = await async_translator.get_usage()
    assert "Usage this billing period" in str(usage)


async def test_translate_with_enums(async_translator):
    result = await async_translator.translate_text(
        example_text["EN"],
        source_lang=deepl.Language.ENGLISH,
        target_lang=deepl.Language.GERMAN,
    )
    assert example_text["DE"] == result.text


async def test_invalid_authkey(server):
    async with deepl.DeepLClientAsync(
        "invalid", server_url=server.server_url
    ) as translator:
        with pytest.raises(deepl.exceptions.AuthorizationException):
            await translator.get_usage()


@needs_mock_server
async def test_translate_document_from_filepath(
    server,
    example_document_path,
    example_document_translation,
    output_document_path,
):
    server.set_doc_queue_time(2000)
    server.set_doc_translate_time(2000)
    translator = _make_async_client(
        server, retry_config=RetryConfig(min_connection_timeout=1.0)
    )
    async with translator:
        status = await translator.translate_document_from_filepath(
            example_document_path,
            output_path=output_document_path,
            **default_lang_args,
        )
    assert example_document_translation == output_document_path.read_text()
    assert status.done


@needs_mock_server
async def test_translate_document_with_retry(
    server,
    example_document_path,
    example_document_translation,
    output_document_path,
):
    server.no_response(1)
    server.set_doc_queue_time(2000)
    server.set_doc_translate_time(2000)

    translator = _make_async_client(
        server, retry_config=RetryConfig(min_connection_timeout=1.0)
    )
    async with translator:
        await translator.translate_document_from_filepath(
            example_document_path,
            output_path=output_document_path,
            **default_lang_args,
        )
    assert example_document_translation == output_document_path.read_text()


@needs_mock_server
async def test_translate_document_low_level(
    async_translator,
    example_document_path,
    example_document_translation,
    output_document_path,
    server,
):
    server.set_doc_queue_time(100)

    with open(example_document_path, "rb") as infile:
        handle = await async_translator.translate_document_upload(
            infile, **default_lang_args
        )
    status = await async_translator.translate_document_get_status(handle)
    assert status.ok and not status.done

    doc_id, doc_key = handle.document_id, handle.document_key
    del handle

    handle = deepl.DocumentHandle(doc_id, doc_key)
    status = await async_translator.translate_document_get_status(handle)
    assert status.ok

    while status.ok and not status.done:
        status = await async_translator.translate_document_get_status(handle)

    assert status.ok and status.done
    with open(output_document_path, "wb") as outfile:
        await async_translator.translate_document_download(handle, outfile)

    assert output_document_path.read_text() == example_document_translation


async def test_source_and_target_languages(async_translator):
    source_languages = await async_translator.get_source_languages()
    for lang in source_languages:
        if lang.code == "EN":
            assert lang.name == "English"

    target_languages = await async_translator.get_target_languages()
    for lang in target_languages:
        if lang.code == "DE":
            assert lang.supports_formality


async def test_glossary_languages(async_translator):
    pairs = await async_translator.get_glossary_languages()
    assert len(pairs) > 0


async def test_create_and_delete_glossary(async_translator, glossary_name):
    entries = {"Hello": "Hallo", "world": "Welt"}
    glossary = await async_translator.create_glossary(
        glossary_name, source_lang="EN", target_lang="DE", entries=entries
    )
    assert glossary.name == glossary_name
    assert glossary.entry_count == len(entries)

    returned = await async_translator.get_glossary(glossary.glossary_id)
    assert returned.glossary_id == glossary.glossary_id

    glossaries = await async_translator.list_glossaries()
    assert any(g.glossary_id == glossary.glossary_id for g in glossaries)

    returned_entries = await async_translator.get_glossary_entries(glossary)
    assert returned_entries == entries

    await async_translator.delete_glossary(glossary)

    with pytest.raises(deepl.GlossaryNotFoundException):
        await async_translator.get_glossary(glossary.glossary_id)
