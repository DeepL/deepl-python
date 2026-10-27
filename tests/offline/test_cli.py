# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json
import logging
import re
from unittest.mock import patch

import deepl
import pytest
from click.testing import CliRunner

from ..fixtures import example_tmx
from .client import AUTH_KEY, SERVER_URL, url
from .matchers import (
    bodyless_request,
    json_request,
    multipart_request,
    storage_request,
)

# flake8: noqa: F401
from deepl import __main__

main_function = deepl.__main__

TEXT_BODY = {
    "text": ["proton beam"],
    "target_lang": "DE",
    "show_billed_characters": True,
    "formality": "default",
    "split_sentences": "1",
    "preserve_formatting": False,
    "outline_detection": True,
}
GLOSSARY_JSON = {
    "glossary_id": "g-1",
    "name": "my glossary",
    "ready": True,
    "source_lang": "de",
    "target_lang": "en",
    "creation_time": "2021-08-03T14:16:18.329Z",
    "entry_count": 2,
}
TM_JSON = {
    "translation_memory_id": "tm-1",
    "name": "memory",
    "source_language": "de",
    "target_languages": ["en", "fr"],
    "segment_count": 7,
}
UPLOAD_URL = "https://storage.example.com/tm/upload?signature=abc"
DOWNLOAD_URL = "https://storage.example.com/tm/download?signature=def"


@pytest.fixture(autouse=True)
def isolated_cli_state():
    """Gives each test the CLI's logger configuration and no system keyring."""
    logger = logging.getLogger("deepl")
    level, handlers = logger.level, list(logger.handlers)
    with patch("deepl.__main__._optional_import", return_value=None):
        yield
    logger.setLevel(level)
    logger.handlers = handlers


@pytest.fixture
def runner():
    return CliRunner(
        env={"DEEPL_SERVER_URL": SERVER_URL, "DEEPL_AUTH_KEY": AUTH_KEY}
    )


def invoke(runner, *args, **kwargs):
    return runner.invoke(main_function, list(args), **kwargs)


def reply_with_translation(mocked, body, **fields):
    mocked.post(
        url("v2/translate"),
        json={
            "translations": [
                {
                    "detected_source_language": "EN",
                    "text": "Protonenstrahl",
                    "billed_characters": 11,
                    **fields,
                }
            ]
        },
        match=json_request(body),
    )


def test_prints_help(runner):
    result = invoke(runner, "--help")

    assert result.exit_code == 0, result.output
    assert "usage" in result.output


def test_prints_version(runner):
    result = invoke(runner, "--version")

    assert result.exit_code == 0, result.output
    assert re.match(r"deepl-python v\d+\.\d+\.\d+", result.output)


def test_exits_with_usage_error_without_command(runner):
    result = invoke(runner)

    assert result.exit_code == 2, result.output
    assert "required: command" in result.output


def test_exits_with_error_without_auth_key(runner):
    result = invoke(runner, "usage", env={"DEEPL_AUTH_KEY": None})

    assert result.exit_code == 1, result.output
    assert "DEEPL_AUTH_KEY" in result.output


def test_reads_auth_key_from_keyring(mocked, runner):
    mocked.get(
        url("v2/usage"),
        json={"character_count": 1, "character_limit": 2},
        match=[
            *bodyless_request(),
        ],
    )
    keyring = {"deepl": {"DEEPL_AUTH_KEY": AUTH_KEY}}

    with patch("deepl.__main__._optional_import") as import_mock:
        import_mock.return_value.get_password.side_effect = (
            lambda service, name: keyring[service][name]
        )
        result = invoke(runner, "usage", env={"DEEPL_AUTH_KEY": None})

    assert result.exit_code == 0, result.output
    assert "Usage this billing period" in result.output


def test_prefers_auth_key_argument_over_environment(mocked, runner):
    mocked.get(
        url("v2/usage"),
        json={},
        match=[
            *bodyless_request(),
        ],
    )

    result = invoke(runner, "--auth-key", AUTH_KEY, "usage")

    assert result.exit_code == 0, result.output


def test_logs_requests_when_verbose(mocked, runner):
    mocked.get(url("v2/usage"), json={})

    result = invoke(runner, "-vv", "usage")

    assert result.exit_code == 0, result.output
    assert "Request to DeepL API" in result.output
    assert "Request details" in result.output


def test_prints_usage(mocked, runner):
    mocked.get(
        url("v2/usage"),
        json={"character_count": 3, "character_limit": 10},
        match=bodyless_request(),
    )

    result = invoke(runner, "usage")

    assert result.exit_code == 0, result.output
    assert "Characters: 3 of 10" in result.output


def test_prints_source_and_target_languages(mocked, runner):
    mocked.get(
        url("v3/languages"),
        json=[
            {
                "lang": "de",
                "name": "German",
                "usable_as_source": True,
                "usable_as_target": True,
                "status": "stable",
                "features": {"formality": {"status": "stable"}},
            },
            {
                "lang": "en-US",
                "name": "English (American)",
                "usable_as_source": False,
                "usable_as_target": True,
                "status": "stable",
                "features": {},
            },
        ],
        match=bodyless_request({"resource": "translate_text"}),
    )

    result = invoke(runner, "languages")

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Source languages available:",
        "DE: German",
        "Target languages available:",
        "DE: German (supports formality)",
        "EN-US: English (American)",
    ]


def test_prints_glossary_language_pairs(mocked, runner):
    mocked.get(
        url("v3/languages"),
        json=[
            {"lang": "de", "usable_as_source": True, "usable_as_target": True},
            {"lang": "en", "usable_as_source": True, "usable_as_target": True},
        ],
        match=bodyless_request({"resource": "glossary"}),
    )

    result = invoke(runner, "languages", "--glossary")

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Language pairs supported for glossaries: (source, target)",
        "de, en",
        "en, de",
    ]


def test_translates_text_and_prints_requested_details(mocked, runner):
    reply_with_translation(
        mocked,
        {**TEXT_BODY, "model_type": "latency_optimized"},
        model_type_used="latency_optimized",
    )

    result = invoke(
        runner,
        "text",
        "--to",
        "DE",
        "--show-detected-source",
        "--show-billed-characters",
        "--show-model-type-used",
        "proton beam",
    )

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Detected source language: EN",
        "Billed characters: 11",
        "Model type used: latency_optimized",
        "Protonenstrahl",
    ]


def test_prints_unknown_when_model_type_used_is_missing(mocked, runner):
    reply_with_translation(
        mocked,
        {**TEXT_BODY, "model_type": "quality_optimized"},
    )

    result = invoke(
        runner,
        "text",
        "--to",
        "DE",
        "--model-type",
        "quality_optimized",
        "--show-model-type-used",
        "proton beam",
    )

    assert result.exit_code == 0, result.output
    assert "Model type used: unknown" in result.output


def test_translate_is_an_alias_of_text(mocked, runner):
    reply_with_translation(mocked, TEXT_BODY)

    result = invoke(runner, "translate", "--to", "DE", "proton beam")

    assert result.exit_code == 0, result.output


def test_reads_text_from_standard_input(mocked, runner):
    reply_with_translation(mocked, TEXT_BODY)

    result = invoke(runner, "text", "--to", "DE", "-", input="proton beam")

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "args, extra_body",
    [
        (["--from", "EN"], {"source_lang": "EN"}),
        (["--formality", "prefer_less"], {"formality": "prefer_less"}),
        (
            ["--split-sentences", "nonewlines"],
            {"split_sentences": "nonewlines"},
        ),
        (["--preserve-formatting"], {"preserve_formatting": True}),
        (["--context", "greeting"], {"context": "greeting"}),
        (
            ["--tag-handling", "xml", "--tag-handling-version", "v2"],
            {"tag_handling": "xml", "tag_handling_version": "v2"},
        ),
        (["--outline-detection-off"], {"outline_detection": False}),
        (
            ["--ignore-tags", "a,b", "--ignore-tags", "c"],
            {"ignore_tags": ["a", "b", "c"]},
        ),
        (
            ["--splitting-tags", "a,b", "--splitting-tags", "c"],
            {"splitting_tags": ["a", "b", "c"]},
        ),
        (
            ["--non-splitting-tags", "a,b", "--non-splitting-tags", "c"],
            {"non_splitting_tags": ["a", "b", "c"]},
        ),
        (
            ["--model-type", "quality_optimized"],
            {"model_type": "quality_optimized"},
        ),
        (
            ["--from", "EN", "--glossary-id", "g1"],
            {"source_lang": "EN", "glossary_id": "g1"},
        ),
        (
            ["--from", "EN", "--glossary-ids", "g1", "--glossary-ids", "g2"],
            {"source_lang": "EN", "glossary_ids": ["g1", "g2"]},
        ),
        (["--style-id", "style-1"], {"style_id": "style-1"}),
        (["--style-profile-id", "sp-1"], {"style_profile_id": "sp-1"}),
        (
            [
                "--translation-memory-id",
                "tm-1",
                "--translation-memory-threshold",
                "80",
            ],
            {
                "translation_memory_id": "tm-1",
                "translation_memory_threshold": 80,
            },
        ),
        (
            ["--custom-instructions", "a", "--custom-instructions", "b"],
            {"custom_instructions": ["a", "b"]},
        ),
        (
            ["--extra-body-parameters", '{"new_option": true}'],
            {"new_option": True},
        ),
    ],
)
def test_sends_text_option(mocked, runner, args, extra_body):
    reply_with_translation(mocked, {**TEXT_BODY, **extra_body})

    result = invoke(runner, "text", "--to", "DE", *args, "proton beam")

    assert result.exit_code == 0, result.output


def test_rejects_glossary_id_together_with_glossary_ids(runner):
    result = invoke(
        runner,
        "text",
        "--to",
        "DE",
        "--from",
        "EN",
        "--glossary-id",
        "g1",
        "--glossary-ids",
        "g2",
        "proton beam",
    )

    assert result.exit_code == 1, result.output
    assert "glossary_ids cannot be used together" in result.output


def test_prints_error_and_exits_when_api_rejects_text(mocked, runner):
    mocked.post(url("v2/translate"), status=403)

    result = invoke(runner, "text", "--to", "DE", "proton beam")

    assert result.exit_code == 1, result.output
    assert "Error: Authorization failure" in result.output


def test_rephrases_text_and_prints_detected_source(mocked, runner):
    mocked.post(
        url("v2/write/rephrase"),
        json={
            "improvements": [
                {
                    "text": "better",
                    "detected_source_language": "EN",
                    "target_language": "EN-GB",
                }
            ]
        },
        match=json_request({"text": ["helo"], "target_lang": "EN-GB"}),
    )

    result = invoke(
        runner, "rephrase", "--to", "EN-GB", "--show-detected-source", "helo"
    )

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Detected source language: EN",
        "better",
    ]


def reply_with_document_translation(mocked, data, filename="document.txt"):
    mocked.post(
        url("v2/document"),
        json={"document_id": "doc-1", "document_key": "key-1"},
        match=multipart_request({"file": (filename, b"hello")}, data),
    )
    mocked.post(
        url("v2/document/doc-1"),
        json={"status": "done", "billed_characters": 5},
        match=json_request({"document_key": "key-1"}),
    )
    mocked.post(
        url("v2/document/doc-1/result"),
        body=b"translated",
        match=json_request({"document_key": "key-1"}),
    )


def test_translates_document_into_destination_directory(
    mocked, runner, tmp_path
):
    input_path = tmp_path / "document.txt"
    input_path.write_text("hello")
    output_dir = tmp_path / "output"
    reply_with_document_translation(
        mocked, {"target_lang": "DE", "formality": "default"}
    )

    result = invoke(
        runner, "document", "--to", "DE", str(input_path), str(output_dir)
    )

    assert result.exit_code == 0, result.output
    assert (output_dir / "document.txt").read_bytes() == b"translated"


def test_sends_document_options(mocked, runner, tmp_path):
    input_path = tmp_path / "document.txt"
    input_path.write_text("hello")
    reply_with_document_translation(
        mocked,
        {
            "target_lang": "DE",
            "source_lang": "EN",
            "formality": "more",
            "glossary_ids": "g1,g2",
            "style_id": "style-1",
            "style_profile_id": "sp-1",
            "translation_memory_id": "tm-1",
            "translation_memory_threshold": 80,
        },
    )

    result = invoke(
        runner,
        "document",
        "--to",
        "DE",
        "--from",
        "EN",
        "--formality",
        "more",
        "--glossary-ids",
        "g1",
        "--glossary-ids",
        "g2",
        "--style-id",
        "style-1",
        "--style-profile-id",
        "sp-1",
        "--translation-memory-id",
        "tm-1",
        "--translation-memory-threshold",
        "80",
        str(input_path),
        str(tmp_path / "output"),
    )

    assert result.exit_code == 0, result.output


def test_names_output_file_after_output_format(mocked, runner, tmp_path):
    input_path = tmp_path / "document.txt"
    input_path.write_text("hello")
    output_dir = tmp_path / "output"
    reply_with_document_translation(
        mocked,
        {"target_lang": "DE", "formality": "default", "output_format": "pdf"},
    )

    result = invoke(
        runner,
        "document",
        "--to",
        "DE",
        "--output-format",
        "pdf",
        str(input_path),
        str(output_dir),
    )

    assert result.exit_code == 0, result.output
    assert (output_dir / "document.pdf").exists()


def test_rejects_destination_that_is_a_file(runner, tmp_path):
    input_path = tmp_path / "document.txt"
    input_path.write_text("hello")
    destination = tmp_path / "output"
    destination.touch()

    result = invoke(
        runner, "document", "--to", "DE", str(input_path), str(destination)
    )

    assert result.exit_code == 1, result.output
    assert "already exists" in result.output


def test_prints_error_and_leaves_no_output_when_api_rejects_document(
    mocked, runner, tmp_path
):
    input_path = tmp_path / "document.invalid"
    input_path.write_text("hello")
    output_dir = tmp_path / "output"
    mocked.post(
        url("v2/document"),
        status=400,
        json={"message": "Invalid file extension"},
    )

    result = invoke(
        runner, "document", "--to", "DE", str(input_path), str(output_dir)
    )

    assert result.exit_code == 1, result.output
    assert "Bad request, message: Invalid file extension" in result.output
    assert not (output_dir / "document.invalid").exists()


def test_exits_with_usage_error_without_glossary_subcommand(runner):
    result = invoke(runner, "glossary")

    assert result.exit_code == 2, result.output
    assert "required: subcommand" in result.output


def glossary_create_body(entries, entries_format="tsv", **fields):
    return {
        "name": "my glossary",
        "source_lang": "DE",
        "target_lang": "EN",
        "entries_format": entries_format,
        "entries": entries,
        **fields,
    }


@pytest.mark.parametrize(
    "args, kwargs, body",
    [
        (
            ["Hallo=Hello", "Maler=Artist"],
            {},
            glossary_create_body("Hallo\tHello\nMaler\tArtist"),
        ),
        (
            ["-"],
            {"input": "Hallo\tHello\nMaler\tArtist\n"},
            glossary_create_body("Hallo\tHello\nMaler\tArtist"),
        ),
    ],
)
def test_creates_glossary_from_arguments_and_standard_input(
    mocked, runner, args, kwargs, body
):
    mocked.post(
        url("v2/glossaries"), json=GLOSSARY_JSON, match=json_request(body)
    )

    result = invoke(
        runner,
        "glossary",
        "create",
        "--name",
        "my glossary",
        "--from",
        "DE",
        "--to",
        "EN",
        *args,
        **kwargs,
    )

    assert result.exit_code == 0, result.output
    assert 'Created Glossary "my glossary" (g-1)' in result.output
    assert "Glossary ID" in result.output


@pytest.mark.parametrize(
    "csv_flag, content, body",
    [
        ([], "Hallo\tHello\n", glossary_create_body("Hallo\tHello")),
        (
            ["--csv"],
            "Hallo,Hello\n",
            glossary_create_body("Hallo,Hello\n", "csv"),
        ),
    ],
)
def test_creates_glossary_from_file(
    mocked, runner, tmp_path, csv_flag, content, body
):
    path = tmp_path / "entries"
    path.write_text(content)
    mocked.post(
        url("v2/glossaries"), json=GLOSSARY_JSON, match=json_request(body)
    )

    result = invoke(
        runner,
        "glossary",
        "create",
        "--name",
        "my glossary",
        "--from",
        "DE",
        "--to",
        "EN",
        "--file",
        str(path),
        *csv_flag,
    )

    assert result.exit_code == 0, result.output


def test_rejects_glossary_file_together_with_entries(runner, tmp_path):
    path = tmp_path / "entries"
    path.write_text("Hallo\tHello\n")

    result = invoke(
        runner,
        "glossary",
        "create",
        "--name",
        "my glossary",
        "--from",
        "DE",
        "--to",
        "EN",
        "--file",
        str(path),
        "Hallo=Hello",
    )

    assert result.exit_code == 1, result.output
    assert "--file argument" in result.output


def test_rejects_csv_flag_with_entries_from_arguments(runner):
    result = invoke(
        runner,
        "glossary",
        "create",
        "--name",
        "my glossary",
        "--from",
        "DE",
        "--to",
        "EN",
        "--csv",
        "Hallo=Hello",
    )

    assert result.exit_code == 1, result.output
    assert "csv option is not compatible" in result.output


def test_prints_glossary_list_get_and_entries(mocked, runner):
    mocked.get(
        url("v2/glossaries"),
        json={"glossaries": [GLOSSARY_JSON]},
        match=bodyless_request(),
    )
    mocked.get(
        url("v2/glossaries/g-1"),
        json=GLOSSARY_JSON,
        match=bodyless_request(),
    )
    mocked.get(url("v2/glossaries/g-1/entries"), body="Hallo\tHello\n")

    listed = invoke(runner, "glossary", "list")
    got = invoke(runner, "glossary", "get", "g-1")
    entries = invoke(runner, "glossary", "entries", "g-1")

    for result in (listed, got):
        assert result.exit_code == 0, result.output
        header, row = result.output.splitlines()
        assert [col.strip() for col in header.split("\t")[:3]] == [
            "Glossary ID",
            "Name",
            "Ready",
        ]
        assert [col.strip() for col in row.split("\t")[:3]] == [
            "g-1",
            "my glossary",
            "True",
        ]
    assert entries.exit_code == 0, entries.output
    assert entries.output == "Hallo\tHello\n"


def test_deletes_every_given_glossary(mocked, runner):
    mocked.delete(url("v2/glossaries/g-1"), status=204)
    mocked.delete(url("v2/glossaries/g-2"), status=204)

    result = invoke(runner, "glossary", "delete", "g-1", "g-2")

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Glossary with ID g-1 successfully deleted.",
        "Glossary with ID g-2 successfully deleted.",
    ]


def test_exits_with_usage_error_without_translation_memory_subcommand(runner):
    result = invoke(runner, "translation-memory")

    assert result.exit_code == 2, result.output
    assert "required: subcommand" in result.output


def test_lists_and_gets_translation_memories(mocked, runner):
    mocked.get(
        url("v3/translation_memories"),
        json={"translation_memories": [TM_JSON]},
        match=bodyless_request({"page": "1", "page_size": "5"}),
    )
    mocked.get(
        url("v3/translation_memories/tm-1"),
        json=TM_JSON,
        match=bodyless_request(),
    )

    listed = invoke(
        runner, "translation-memory", "list", "--page", "1", "--page-size", "5"
    )
    got = invoke(runner, "translation-memory", "get", "tm-1")

    for result in (listed, got):
        assert result.exit_code == 0, result.output
        header, row = result.output.splitlines()
        assert header.split("\t")[0].strip() == "Translation Memory ID"
        assert row.split("\t")[0].strip() == "tm-1"
        assert row.split("\t")[3].strip() == "en,fr"


def reply_with_segments(mocked, query, next_page_cursor=None):
    mocked.get(
        url("v3/translation_memories/tm-1/segments"),
        json={
            "segment_count": 2,
            "next_page_cursor": next_page_cursor,
            "segments": [
                {
                    "source_segment_id": f"s-{len(query)}",
                    "source_text": "Hallo",
                    "targets": [
                        {
                            "target_segment_id": "t-1",
                            "target_language": "en",
                            "target_text": "Hello",
                        }
                    ],
                }
            ],
        },
        match=bodyless_request(query),
    )


def test_prints_one_page_of_segments_with_next_cursor(mocked, runner):
    reply_with_segments(
        mocked,
        {
            "page_size": "1",
            "filter_text": "Hal",
            "filter_case_sensitive": "true",
        },
        next_page_cursor="c1",
    )

    result = invoke(
        runner,
        "translation-memory",
        "segments",
        "tm-1",
        "--page-size",
        "1",
        "--filter-text",
        "Hal",
        "--filter-case-sensitive",
    )

    assert result.exit_code == 0, result.output
    assert "Total segments in translation memory: 2" in result.output
    assert "Next page cursor: c1" in result.output


def test_prints_all_pages_of_segments(mocked, runner):
    reply_with_segments(mocked, {}, next_page_cursor="c1")
    reply_with_segments(mocked, {"page_cursor": "c1"})

    result = invoke(runner, "translation-memory", "segments", "tm-1", "--all")

    assert result.exit_code == 0, result.output
    assert result.output.count("Hello") == 2
    assert "Next page cursor" not in result.output


def test_deletes_every_given_translation_memory(mocked, runner):
    mocked.delete(url("v3/translation_memories/tm-1"), status=204)
    mocked.delete(url("v3/translation_memories/tm-2"), status=204)

    result = invoke(runner, "translation-memory", "delete", "tm-1", "tm-2")

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Translation memory with ID tm-1 successfully deleted.",
        "Translation memory with ID tm-2 successfully deleted.",
    ]


def declare_tm_import(mocked, size, display_name=None):
    body = {
        "source_file": {"file_name": "example.tmx", "content_length": size}
    }
    if display_name is not None:
        body["parameters"] = {"display_name": display_name}
    mocked.post(
        url("v3/translation_memories/import"),
        json={"job_id": "job-1", "upload_url": UPLOAD_URL},
        match=json_request(body),
    )
    mocked.put(
        UPLOAD_URL, match=storage_request("application/xml", example_tmx)
    )


def test_imports_translation_memory_and_prints_job(mocked, runner, tmp_path):
    path = tmp_path / "example.tmx"
    path.write_text(example_tmx)
    declare_tm_import(mocked, path.stat().st_size, "CLI TM")
    mocked.get(
        url("v3/translation_memories/jobs/job-1"),
        json={
            "job_id": "job-1",
            "operation": "import",
            "results": [
                {
                    "status": "completed",
                    "translation_memory_id": "tm-1",
                    "skipped_segment_count": 0,
                }
            ],
        },
    )

    result = invoke(
        runner, "translation-memory", "import", str(path), "--name", "CLI TM"
    )

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Job job-1 (import): completed",
        "Translation memory ID: tm-1",
        "Skipped segments: 0",
    ]


def test_imports_translation_memory_without_waiting(mocked, runner, tmp_path):
    path = tmp_path / "example.tmx"
    path.write_text(example_tmx)
    declare_tm_import(mocked, path.stat().st_size)

    result = invoke(
        runner, "translation-memory", "import", str(path), "--no-wait"
    )

    assert result.exit_code == 0, result.output
    assert "import job ID job-1" in result.output


def test_exports_translation_memory_to_file(mocked, runner, tmp_path):
    output_path = tmp_path / "exported.tmx"
    mocked.post(
        url("v3/translation_memories/tm-1/export"),
        status=202,
        json={"job_id": "job-1"},
    )
    mocked.get(
        url("v3/translation_memories/jobs/job-1"),
        json={
            "job_id": "job-1",
            "operation": "export",
            "results": [{"status": "completed", "download_url": DOWNLOAD_URL}],
        },
    )
    mocked.get(DOWNLOAD_URL, body=example_tmx, match=storage_request())

    result = invoke(
        runner, "translation-memory", "export", "tm-1", str(output_path)
    )

    assert result.exit_code == 0, result.output
    assert f"Exported translation memory to {output_path}" in result.output
    assert f"Download URL: {DOWNLOAD_URL}" in result.output
    assert output_path.read_text() == example_tmx


def test_prints_translation_memory_job(mocked, runner):
    mocked.get(
        url("v3/translation_memories/jobs/job-1"),
        json={
            "job_id": "job-1",
            "operation": "import",
            "results": [
                {
                    "status": "failed",
                    "status_metadata": {"required_action": "upload"},
                    "error": {"message": "invalid TMX"},
                }
            ],
        },
        match=bodyless_request(),
    )

    result = invoke(runner, "translation-memory", "job", "job-1")

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "Job job-1 (import): failed",
        "Required action: upload",
        "Error: invalid TMX",
    ]
