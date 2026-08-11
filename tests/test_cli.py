# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from click.testing import CliRunner
from .conftest import example_text, needs_mock_server, needs_real_server

# flake8: noqa: F401
from deepl import __main__
import deepl
import pathlib
import pytest
import re
from unittest.mock import patch


main_function = deepl.__main__


@pytest.fixture
def runner(server):
    env = {
        "DEEPL_SERVER_URL": server.server_url,
        "DEEPL_AUTH_KEY": server.auth_key,
    }
    return CliRunner(env=env)


def test_help(runner):
    result = runner.invoke(main_function, "--help")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "usage" in result.output


def test_version(runner):
    result = runner.invoke(main_function, "--version")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "deepl-python v" in result.output
    version_regex = re.compile(r"deepl-python v\d+\.\d+\.\d+")
    assert version_regex.match(result.output) is not None


def test_verbose(runner):
    # verbose = info
    result = runner.invoke(main_function, "--verbose usage")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Request to DeepL API" in result.output

    # verbose = debug
    result = runner.invoke(main_function, "-vv usage")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Request to DeepL API" in result.output
    assert "Request details" in result.output


def test_no_auth(runner):
    result = runner.invoke(
        main_function, "usage", env={"DEEPL_AUTH_KEY": None}
    )
    assert result.exit_code == 1, f"exit: {result.exit_code}\n {result.output}"
    assert "DEEPL_AUTH_KEY" in result.output


# Unfortunately there is no secure way to use the keyring module in our CI,
# so we have to mock the module's behavior here
# For the reason, see https://github.com/jaraco/keyring/issues/477
@patch("deepl.__main__._optional_import")
def test_keyring_auth(import_mock, runner):
    mocked_keyring = {
        "deepl": {"DEEPL_AUTH_KEY": runner.env["DEEPL_AUTH_KEY"]}
    }

    def get_pw_mock(service_name, username):
        return mocked_keyring[service_name][username]

    import_mock.return_value.get_password.side_effect = get_pw_mock
    result = runner.invoke(
        main_function, "usage", env={"DEEPL_AUTH_KEY": None}
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Usage this billing period" in result.output


@patch("importlib.import_module")
def test_no_auth_no_keyring(mock, runner):
    mock.side_effect = ImportError("Keyring module not available in this test")

    result = runner.invoke(
        main_function, "usage", env={"DEEPL_AUTH_KEY": None}
    )
    assert result.exit_code == 1, f"exit: {result.exit_code}\n {result.output}"
    assert "DEEPL_AUTH_KEY" in result.output


@patch("importlib.import_module")
def test_env_auth_no_keyring(mock, runner):
    mock.side_effect = ImportError("Keyring module not available in this test")

    result = runner.invoke(main_function, "usage")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Usage this billing period" in result.output


def test_no_command(runner):
    result = runner.invoke(main_function, "")
    assert result.exit_code == 2, f"exit: {result.exit_code}\n {result.output}"
    assert "required: command" in result.output


def test_usage(runner):
    result = runner.invoke(main_function, "usage")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Usage this billing period" in result.output


def test_languages(runner):
    result = runner.invoke(main_function, "languages")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Source languages" in result.output
    assert "Target languages" in result.output
    assert "DE: German" in result.output
    assert "EN: English" in result.output

    result = runner.invoke(deepl.__main__, "languages --glossary")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "supported for glossaries" in result.output
    assert "de, en" in result.output


def test_text(runner):
    result = runner.invoke(
        main_function,
        'text --to DE "proton beam" --show-detected-source '
        "--show-model-type-used --model-type quality_optimized",
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert example_text["DE"] in result.output
    assert "Detected source" in result.output
    assert "Model type used: quality_optimized" in result.output

    # Test text options
    extra_options = [
        ("--formality more", "'formality': 'more'"),
        ("--formality prefer_less", "'formality': 'prefer_less'"),
        ("--split-sentences 0", "'split_sentences': '0'"),
        ("--preserve-formatting", "'preserve_formatting': True"),
        ("--tag-handling xml", "'tag_handling': 'xml'"),
        ("--outline-detection-off", "'outline_detection': False"),
        (
            "--ignore-tags a,b --ignore-tags c",
            "'ignore_tags': ['a', 'b', 'c']",
        ),
        (
            "--splitting-tags a,b --splitting-tags c",
            "'splitting_tags': ['a', 'b', 'c']",
        ),
        (
            "--non-splitting-tags a,b --non-splitting-tags c",
            "'non_splitting_tags': ['a', 'b', 'c']",
        ),
        (
            "--model-type quality_optimized",
            "'model_type': 'quality_optimized'",
        ),
    ]
    for args, search_str in extra_options:
        result = runner.invoke(
            main_function, f'-vv text --to DE "proton beam" {args}'
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        request_details = next(
            line
            for line in result.output.splitlines()
            if line.startswith("Request details data")
        )
        assert search_str in request_details


def test_text_stdin(runner):
    result = runner.invoke(
        main_function,
        "text --to DE --show-detected-source -",
        input=example_text["EN"],
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert example_text["DE"] in result.output
    assert "Detected source" in result.output


@needs_real_server
def test_text_preserve_formatting(runner):
    result = runner.invoke(
        main_function, 'text --to DE --preserve-formatting "proton beam"'
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert example_text["DE"].lower() in result.output.lower()


def test_text_split_sentences(runner):
    result = runner.invoke(
        main_function,
        '-vv text --to DE --split-sentences nonewlines "proton beam"',
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    # Check split_sentences parameter is sent in HTTP request
    regex = re.compile("Request details.*split_sentences.*nonewlines.*")
    assert any(
        regex.match(line) is not None for line in result.output.split("\n")
    ), f"output:\n{result.output}"


def test_text_tags(runner):
    result = runner.invoke(
        main_function,
        "-vv text --to DE --tag-handling xml --splitting-tags split "
        '--ignore-tags a,b --ignore-tags c --ignore-tags d "proton beam"',
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    # Check ignore_tags parameter is sent in HTTP request
    regex = re.compile(
        "Request details.*'ignore_tags': \\['a', 'b', 'c', 'd']"
    )
    assert any(
        regex.match(line) is not None for line in result.output.split("\n")
    ), f"output:\n{result.output}"
    # Check splitting_tags parameter is sent in HTTP request
    regex = re.compile("Request details.*'splitting_tags': \\['split']")
    assert any(
        regex.match(line) is not None for line in result.output.split("\n")
    ), f"output:\n{result.output}"


def test_text_html_tag_handling(runner):
    result = runner.invoke(
        main_function,
        '-vv text --to DE --tag-handling html "<html><p>Test</p></html>"',
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"


def test_text_glossary_ids(runner):
    # Fake glossary IDs are rejected by the server, but we only need to verify
    # the CLI maps --glossary-ids to a glossary_ids array request field.
    result = runner.invoke(
        main_function,
        "-vv text --to DE --from EN "
        "--glossary-ids gid1 --glossary-ids gid2 "
        '"proton beam"',
    )
    # Check glossary_ids parameter is sent in HTTP request as an array
    regex = re.compile(r"Request details.*'glossary_ids': \['gid1', 'gid2'\]")
    assert any(
        regex.match(line) is not None for line in result.output.split("\n")
    ), f"output:\n{result.output}"


def test_text_glossary_ids_conflicts_with_glossary_id(runner):
    result = runner.invoke(
        main_function,
        "text --to DE --from EN "
        "--glossary-id gid1 --glossary-ids gid2 "
        '"proton beam"',
    )
    assert result.exit_code == 1, f"exit: {result.exit_code}\n {result.output}"
    assert "glossary_ids cannot be used together" in result.output


def test_document(runner, tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output_dir = tmpdir / "output"
    input_document = tmpdir / "document.txt"
    input_document.write_text(example_text["EN"])
    output_document = output_dir / "document.txt"

    result = runner.invoke(
        main_function, f"-vv document --to DE {input_document} {output_dir}"
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert example_text["DE"] == output_document.read_text()


def test_document_glossary_ids(runner, tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output_dir = tmpdir / "output"
    input_document = tmpdir / "document.txt"
    input_document.write_text(example_text["EN"])

    # Fake glossary IDs are rejected by the server, but we only need to verify
    # the CLI maps --glossary-ids to the glossary_ids field. The document
    # endpoint is multipart/form-data, so it is sent comma-separated.
    result = runner.invoke(
        main_function,
        f"-vv document --to DE --from EN "
        f"--glossary-ids gid1 --glossary-ids gid2 "
        f"{input_document} {output_dir}",
    )
    # Check glossary_ids parameter is sent in the document upload request
    regex = re.compile("Request details.*'glossary_ids': 'gid1,gid2'")
    assert any(
        regex.match(line) is not None for line in result.output.split("\n")
    ), f"output:\n{result.output}"


def test_document_style_and_translation_memory(runner, tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output_dir = tmpdir / "output"
    input_document = tmpdir / "document.txt"
    input_document.write_text(example_text["EN"])

    # Fake IDs are rejected by the server, but we only need to verify the CLI
    # maps the new document flags to the corresponding request fields.
    result = runner.invoke(
        main_function,
        f"-vv document --to DE "
        f"--style-id style1 "
        f"--translation-memory-id tm1 "
        f"--translation-memory-threshold 80 "
        f"{input_document} {output_dir}",
    )
    request_details = next(
        line
        for line in result.output.splitlines()
        if line.startswith("Request details data")
    )
    assert "'style_id': 'style1'" in request_details
    assert "'translation_memory_id': 'tm1'" in request_details
    assert "'translation_memory_threshold': 80" in request_details


def test_document_occupied_output(runner, tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output_dir = tmpdir / "output"
    input_document = tmpdir / "document.txt"
    input_document.write_text(example_text["EN"])
    # Create a file in place of the output directory
    output_dir.touch()

    result = runner.invoke(
        main_function, f"-vv document --to DE {input_document} {output_dir}"
    )
    assert result.exit_code == 1, f"exit: {result.exit_code}\n {result.output}"
    assert "already exists" in result.output


def test_invalid_document(runner, tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output_dir = tmpdir / "output"
    input_document = tmpdir / "document.invalid"
    input_document.write_text(example_text["EN"])

    result = runner.invoke(
        main_function, f"-vv document --to DE {input_document} {output_dir}"
    )
    assert result.exit_code == 1, f"exit: {result.exit_code}\n {result.output}"
    assert "Invalid file" in result.output or "file extension" in result.output


def test_glossary_no_subcommand(runner):
    result = runner.invoke(main_function, "glossary")
    assert result.exit_code == 2, f"exit: {result.exit_code}\n {result.output}"
    assert "required: subcommand" in result.output


def test_glossary_create(
    runner,
    glossary_name,
    tmpdir,
    cleanup_matching_glossaries,
    example_glossary_csv,
):
    name_cli = f"{glossary_name}-cli"
    name_stdin = f"{glossary_name}-stdin"
    name_file = f"{glossary_name}-file"
    name_csv = f"{glossary_name}-csv"
    entries = {"Hallo": "Hello", "Maler": "Artist"}
    entries_tsv = deepl.convert_dict_to_tsv(entries)
    entries_cli = "\n".join(f"{s}={t}" for s, t in entries.items())
    file = tmpdir / "glossary_entries"
    file.write(entries_tsv)

    try:
        result = runner.invoke(
            main_function,
            f'-vv glossary create --name "{name_cli}" --from DE --to EN '
            f"{entries_cli}",
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        result = runner.invoke(
            main_function,
            f'-vv glossary create --name "{name_stdin}" --from DE --to EN -',
            input=entries_tsv,
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        result = runner.invoke(
            main_function,
            f'-vv glossary create --name "{name_file}" --from DE --to EN '
            f"--file {file}",
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        result = runner.invoke(
            main_function,
            f'-vv glossary create --name "{name_csv}" --from EN --to DE '
            f"--file {example_glossary_csv} --csv",
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"

        result = runner.invoke(main_function, "-vv glossary list")
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        assert name_cli in result.output
        assert name_stdin in result.output
        assert name_file in result.output
        assert name_csv in result.output

        # Cannot use --file option together with entries
        result = runner.invoke(
            main_function,
            f'-vv glossary create --name "{name_file}" --from DE --to EN '
            f"--file {file} {entries_cli}",
        )
        assert (
            result.exit_code == 1
        ), f"exit: {result.exit_code}\n {result.output}"
        assert "--file argument" in result.output

    finally:
        cleanup_matching_glossaries(
            lambda glossary: glossary.name
            in [name_file, name_cli, name_stdin, name_csv]
        )


def test_glossary_get(translator, runner, glossary_manager):
    with glossary_manager() as created_glossary:
        created_id = created_glossary.glossary_id

        result = runner.invoke(main_function, f"-vv glossary get {created_id}")
        print(result.output)
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        assert created_id in result.output
        assert created_glossary.name in result.output


def test_glossary_list(translator, runner, glossary_manager):
    with glossary_manager(glossary_name_suffix="1") as g1, glossary_manager(
        glossary_name_suffix="2"
    ) as g2, glossary_manager(glossary_name_suffix="3") as g3:
        glossary_list = [g1, g2, g3]

        result = runner.invoke(main_function, "-vv glossary list")
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        for glossary in glossary_list:
            assert glossary.name in result.output


def test_glossary_entries(translator, runner, glossary_manager):
    entries = {"Hallo": "Hello", "Maler": "Artist"}
    with glossary_manager(entries=entries) as created_glossary:
        created_id = created_glossary.glossary_id
        result = runner.invoke(
            main_function, f"-vv glossary entries {created_id}"
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        for source, target in entries.items():
            assert f"{source}\t{target}" in result.output


def test_glossary_delete(translator, runner, glossary_manager):
    with glossary_manager() as created_glossary:
        created_id = created_glossary.glossary_id
        result = runner.invoke(main_function, "glossary list")
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        assert created_id in result.output

        # Remove the created glossary
        result = runner.invoke(
            main_function, f'glossary delete "{created_id}"'
        )
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"

        result = runner.invoke(main_function, "glossary list")
        assert (
            result.exit_code == 0
        ), f"exit: {result.exit_code}\n {result.output}"
        assert created_id not in result.output


TM_DEFAULT_ID = "a74d88fb-ed2a-4943-a664-a4512398b994"

TM_EXAMPLE_TMX = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<tmx version="1.4"><body>'
    '<tu><tuv xml:lang="de"><seg>Hallo</seg></tuv>'
    '<tuv xml:lang="en"><seg>Hello</seg></tuv></tu>'
    "</body></tmx>\n"
)


@pytest.fixture
def cli_tmx_path(tmpdir):
    path = pathlib.Path(tmpdir) / "example.tmx"
    path.write_text(TM_EXAMPLE_TMX)
    return path


def test_translation_memory_no_subcommand(runner):
    result = runner.invoke(main_function, "translation-memory")
    assert result.exit_code == 2, f"exit: {result.exit_code}\n {result.output}"
    assert "required: subcommand" in result.output


@needs_mock_server
def test_translation_memory_list_and_get(runner):
    result = runner.invoke(main_function, "translation-memory list")
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert TM_DEFAULT_ID in result.output

    result = runner.invoke(
        main_function, f"translation-memory get {TM_DEFAULT_ID}"
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert TM_DEFAULT_ID in result.output


@needs_mock_server
def test_translation_memory_segments(runner):
    result = runner.invoke(
        main_function,
        f"translation-memory segments {TM_DEFAULT_ID} --page-size 5",
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Total segments in translation memory:" in result.output
    assert "Next page cursor:" in result.output

    result = runner.invoke(
        main_function, f"translation-memory segments {TM_DEFAULT_ID} --all"
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "Next page cursor:" not in result.output


@needs_mock_server
def test_translation_memory_import_export_delete(runner, cli_tmx_path, tmpdir):
    result = runner.invoke(
        main_function,
        f'translation-memory import "{cli_tmx_path}" --name "CLI TM"',
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "completed" in result.output

    match = re.search(r"Translation memory ID: (\S+)", result.output)
    assert match is not None, result.output
    translation_memory_id = match.group(1)

    output_path = pathlib.Path(tmpdir) / "exported.tmx"
    result = runner.invoke(
        main_function,
        f'translation-memory export {translation_memory_id} "{output_path}"',
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert output_path.exists()
    assert "<tmx" in output_path.read_text()

    result = runner.invoke(
        main_function, f"translation-memory delete {translation_memory_id}"
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"

    result = runner.invoke(main_function, "translation-memory list")
    assert translation_memory_id not in result.output


@needs_mock_server
def test_translation_memory_import_no_wait_and_job(runner, cli_tmx_path):
    result = runner.invoke(
        main_function,
        f'translation-memory import "{cli_tmx_path}" --no-wait',
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"

    match = re.search(r"import job ID (\S+)", result.output)
    assert match is not None, result.output

    result = runner.invoke(
        main_function, f"translation-memory job {match.group(1)}"
    )
    assert result.exit_code == 0, f"exit: {result.exit_code}\n {result.output}"
    assert "(import)" in result.output

    # Clean up the translation memory the upload created, so it does not leak
    # into the listings other tests assert on.
    created = re.search(r"Translation memory ID: (\S+)", result.output)
    if created is not None:
        runner.invoke(
            main_function, f"translation-memory delete {created.group(1)}"
        )
