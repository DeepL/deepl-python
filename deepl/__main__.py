# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import argparse
import json
import deepl
import logging
import os
import pathlib
import sys
from typing import List, Optional
from deepl.util import _optional_import

# Program name for integration with click.testing
name = "python -m deepl"

env_auth_key = "DEEPL_AUTH_KEY"
env_server_url = "DEEPL_SERVER_URL"
env_proxy_url = "DEEPL_PROXY_URL"

keyring_key_folder = "deepl"
keyring_key_name = env_auth_key


def action_usage(deepl_client: deepl.DeepLClient):
    """Action function for the usage command."""
    usage_result = deepl_client.get_usage()
    print(usage_result)


def action_languages(deepl_client: deepl.DeepLClient, glossary: bool):
    """Action function for the languages command."""
    if glossary:
        glossary_languages = deepl_client.get_glossary_languages()
        print("Language pairs supported for glossaries: (source, target)")
        for language_pair in glossary_languages:
            print(f"{language_pair.source_lang}, {language_pair.target_lang}")
    else:
        source_languages = deepl_client.get_source_languages()
        target_languages = deepl_client.get_target_languages()

        print("Source languages available:")
        for language in source_languages:
            print(f"{language.code}: {language.name}")
        print("Target languages available:")
        for language in target_languages:
            if language.supports_formality:
                print(f"{language.code}: {language.name} (supports formality)")
            else:
                print(f"{language.code}: {language.name}")


def action_document(
    deepl_client: deepl.DeepLClient,
    file: List[str],
    dest: str,
    output_format: Optional[str],
    **kwargs,
):
    """Action function for the document command."""
    if not os.path.exists(dest):
        os.makedirs(dest, exist_ok=True)
    elif not os.path.isdir(dest):
        raise Exception("Destination already exists, and is not a directory")

    for this_file in file:
        outfile_name = (
            this_file
            if not output_format
            else (os.path.splitext(this_file)[0] + "." + output_format)
        )
        output_path = os.path.join(dest, os.path.basename(outfile_name))
        deepl_client.translate_document_from_filepath(
            this_file, output_path, **kwargs
        )


def action_text(
    deepl_client: deepl.DeepLClient,
    show_detected_source: bool = False,
    show_billed_characters: Optional[bool] = None,
    show_model_type_used: Optional[bool] = None,
    **kwargs,
):
    """Action function for the text command."""

    if show_model_type_used and kwargs.get("model_type") is None:
        # specify model_type so API includes model_type_used response parameter
        kwargs["model_type"] = deepl.ModelType.LATENCY_OPTIMIZED

    translation = deepl_client.translate_text(**kwargs)
    output_list = (
        translation if isinstance(translation, List) else [translation]
    )
    for output in output_list:
        if show_detected_source:
            print(f"Detected source language: {output.detected_source_lang}")
        if show_billed_characters:
            text_value = (
                "unknown"
                if output.billed_characters is None
                else str(output.billed_characters)
            )
            print(f"Billed characters: {text_value}")
        if show_model_type_used:
            text_value = (
                "unknown"
                if output.model_type_used is None
                else output.model_type_used
            )
            print(f"Model type used: {text_value}")

        print(output.text)


def action_rephrase(
    deepl_client: deepl.DeepLClient,
    **kwargs,
):
    """Action function for the rephrase command."""
    improvement = deepl_client.rephrase_text(**kwargs)
    output_list = (
        improvement if isinstance(improvement, List) else [improvement]
    )
    for output in output_list:
        print(output.text)


def action_glossary(
    deepl_client: deepl.DeepLClient,
    subcommand: str,
    **kwargs,
):
    # Call action function corresponding to command with remaining args
    globals()[f"action_glossary_{subcommand}"](deepl_client, **kwargs)
    pass


def action_glossary_create(
    deepl_client: deepl.DeepLClient, entry_list, file, csv, **kwargs
):
    term_separator = None
    if file:
        if entry_list:
            raise deepl.DeepLException(
                "The --file argument cannot be used together with "
                "command-line entries"
            )
        content = pathlib.Path(file).read_text("UTF-8")
    elif entry_list and entry_list[0] == "-":
        content = sys.stdin.read()
    else:
        content = "\n".join(entry_list)
        term_separator = "="
        if csv:
            raise Exception(
                "csv option is not compatible with command-line entries"
            )

    if csv:
        glossary = deepl_client.create_glossary_from_csv(
            csv_data=content, **kwargs
        )
    else:
        if term_separator:
            entry_dict = deepl.convert_tsv_to_dict(content, term_separator)
        else:
            entry_dict = deepl.convert_tsv_to_dict(content)
        glossary = deepl_client.create_glossary(entries=entry_dict, **kwargs)

    print(f"Created {glossary}")
    print_glossaries([glossary])


def print_table(headers, data):
    data = [headers] + data
    col_max_widths = [
        max(len(row[col_num]) for row in data)
        for col_num in range(len(headers))
    ]
    for row in data:
        print(
            "\t".join(
                [col.ljust(width) for col, width in zip(row, col_max_widths)]
            )
        )


def print_glossaries(glossaries):
    print_table(
        [
            "Glossary ID",
            "Name",
            "Ready",
            "Source",
            "Target",
            "Count",
            "Created",
        ],
        [
            [
                glossary.glossary_id,
                glossary.name,
                str(glossary.ready),
                glossary.source_lang,
                glossary.target_lang,
                str(glossary.entry_count),
                str(glossary.creation_time),
            ]
            for glossary in glossaries
        ],
    )


def action_glossary_list(deepl_client: deepl.DeepLClient):
    glossaries = deepl_client.list_glossaries()
    print_glossaries(glossaries)


def action_glossary_get(deepl_client: deepl.DeepLClient, **kwargs):
    glossary = deepl_client.get_glossary(**kwargs)
    print_glossaries([glossary])


def action_glossary_entries(deepl_client: deepl.DeepLClient, glossary_id):
    glossary_entries = deepl_client.get_glossary_entries(glossary=glossary_id)
    print(deepl.convert_dict_to_tsv(glossary_entries))


def action_glossary_delete(
    deepl_client: deepl.DeepLClient, glossary_id_list: str
):
    for glossary_id in glossary_id_list:
        deepl_client.delete_glossary(glossary_id)
        print(f"Glossary with ID {glossary_id} successfully deleted.")


def action_translation_memory(
    deepl_client: deepl.DeepLClient,
    subcommand: str,
    **kwargs,
):
    # Call action function corresponding to command with remaining args
    globals()[f"action_translation_memory_{subcommand}"](
        deepl_client, **kwargs
    )


def print_translation_memories(translation_memories):
    print_table(
        ["Translation Memory ID", "Name", "Source", "Targets", "Segments"],
        [
            [
                tm.translation_memory_id,
                tm.name,
                tm.source_language,
                ",".join(tm.target_languages),
                str(tm.segment_count),
            ]
            for tm in translation_memories
        ],
    )


def print_translation_memory_job(job):
    result = job.result
    print(f"Job {job.job_id} ({job.operation}): {job.status}")
    if result is None:
        return
    if result.required_action:
        print(f"Required action: {result.required_action}")
    if result.translation_memory_id:
        print(f"Translation memory ID: {result.translation_memory_id}")
    if result.skipped_segment_count is not None:
        print(f"Skipped segments: {result.skipped_segment_count}")
    if result.download_url:
        print(f"Download URL: {result.download_url}")
    if result.error_message:
        print(f"Error: {result.error_message}")


def action_translation_memory_list(
    deepl_client: deepl.DeepLClient, page, page_size
):
    translation_memories = deepl_client.list_translation_memories(
        page=page, page_size=page_size
    )
    print_translation_memories(translation_memories)


def action_translation_memory_get(
    deepl_client: deepl.DeepLClient, translation_memory_id
):
    print_translation_memories(
        [deepl_client.get_translation_memory(translation_memory_id)]
    )


def action_translation_memory_segments(
    deepl_client: deepl.DeepLClient,
    translation_memory_id,
    page_size,
    page_cursor,
    filter_text,
    filter_case_sensitive,
    all_pages,
):
    rows = []
    segment_count = 0
    while True:
        page = deepl_client.list_translation_memory_segments(
            translation_memory_id,
            page_size=page_size,
            page_cursor=page_cursor,
            filter_text=filter_text,
            filter_case_sensitive=filter_case_sensitive or None,
        )
        segment_count = page.segment_count
        for segment in page.segments:
            for target in segment.targets:
                rows.append(
                    [
                        segment.source_segment_id,
                        segment.source_text,
                        target.target_language,
                        target.target_text,
                    ]
                )
        page_cursor = page.next_page_cursor
        if not all_pages or not page_cursor:
            break

    print_table(["Segment ID", "Source", "Target lang", "Target"], rows)
    print(f"Total segments in translation memory: {segment_count}")
    if page_cursor:
        print(f"Next page cursor: {page_cursor}")


def action_translation_memory_delete(
    deepl_client: deepl.DeepLClient, translation_memory_id_list
):
    for translation_memory_id in translation_memory_id_list:
        deepl_client.delete_translation_memory(translation_memory_id)
        print(
            f"Translation memory with ID {translation_memory_id} "
            "successfully deleted."
        )


def action_translation_memory_import(
    deepl_client: deepl.DeepLClient, file, name, no_wait, timeout
):
    file_path = pathlib.Path(file)
    if no_wait:
        created = deepl_client.create_translation_memory_import(
            file_name=file_path.name,
            content_length=file_path.stat().st_size,
            display_name=name,
        )
        with open(file_path, "rb") as input_file:
            deepl_client.upload_translation_memory_file(created, input_file)
        print(f"Uploaded {file}, import job ID {created.job_id}")
        return

    job = deepl_client.import_translation_memory_from_filepath(
        file_path, display_name=name, timeout_s=timeout
    )
    print_translation_memory_job(job)


def action_translation_memory_export(
    deepl_client: deepl.DeepLClient,
    translation_memory_id,
    output_file,
    timeout,
):
    job = deepl_client.export_translation_memory_to_filepath(
        translation_memory_id, output_file, timeout_s=timeout
    )
    print(f"Exported translation memory to {output_file}")
    print_translation_memory_job(job)


def action_translation_memory_job(deepl_client: deepl.DeepLClient, job_id):
    print_translation_memory_job(
        deepl_client.get_translation_memory_job(job_id)
    )


def get_parser(prog_name):
    """Constructs and returns the argument parser for all commands."""
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Translate text using the DeepL API "
        "(https://www.deepl.com/docs-api).",
        epilog="If you encounter issues while using this program, please "
        "report them at https://github.com/DeepLcom/deepl-python/issues",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"deepl-python v{deepl.__version__}",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        dest="verbose",
        default=0,
        help="print additional information, can be supplied multiple times "
        "for more verbose output",
    )
    parser.add_argument(
        "--no-platform-info",
        default=False,
        action="store_true",
        dest="noplatforminfo",
        help="if this flag is enabled, do not send additional information "
        "about the platform with API requests.",
    )

    parser.add_argument(
        "--auth-key",
        default=None,
        help="authentication key as given in your DeepL account; the "
        f"{env_auth_key} environment variable is used as secondary fallback; "
        f"the key {keyring_key_name} in {keyring_key_folder} is used "
        "as tertiary fallback",
    )
    parser.add_argument(
        "--server-url",
        default=None,
        metavar="URL",
        help=f"alternative server URL for testing; the {env_server_url} "
        f"environment variable may be used as secondary fallback",
    )
    parser.add_argument(
        "--proxy-url",
        default=None,
        metavar="URL",
        help="proxy server URL to use for all connections; the "
        f"{env_proxy_url} environment variable may be used as secondary "
        "fallback",
    )

    subparsers = parser.add_subparsers(
        metavar="command", dest="command", required=True
    )

    def add_common_arguments(subparser: argparse.ArgumentParser):
        """Adds arguments shared between text and document commands to the
        subparser."""
        subparser.add_argument(
            "--to",
            "--target-lang",
            dest="target_lang",
            required=True,
            help="language into which the text should be translated",
        )
        subparser.add_argument(
            "--from",
            "--source-lang",
            dest="source_lang",
            help="language of the text to be translated; unless using a "
            "glossary, this argument is optional and if it is omitted DeepL "
            "will auto-detect the source language.",
        )
        subparser.add_argument(
            "--formality",
            type=str,
            choices=[enum.value for enum in deepl.Formality],
            default=deepl.Formality.DEFAULT.value,
            help="desired formality for translation",
        )
        subparser.add_argument(
            "--glossary-id",
            dest="glossary",
            type=str,
            help="ID of glossary to use for translation",
        )
        subparser.add_argument(
            "--glossary-ids",
            dest="glossary_ids",
            action="append",
            type=str,
            metavar="id",
            help="ID of a glossary to use for translation; may be repeated to "
            "use up to 5 glossaries, applied in order. Requires --from and "
            "cannot be combined with --glossary-id",
        )
        subparser.add_argument(
            "--extra-body-parameters",
            dest="extra_body_parameters",
            type=json.loads,
            default=None,
            help="additional body parameters to include in the API request, "
            "specified as a JSON object string, for example: "
            '\'{"tag_handling": "xml", "show_billed_characters": true}\'',
        )

    # create the parser for the "text" command
    parser_text = subparsers.add_parser(
        "text",
        help="translate text(s)",
        description="translate text(s)",
        aliases=["translate"],
    )
    add_common_arguments(parser_text)
    parser_text.add_argument(
        "--context",
        type=str,
        help="additional contextual text to improve translations, see API docs"
        " for information",
    )
    parser_text.add_argument(
        "--split-sentences",
        type=str,
        choices=[enum.value for enum in deepl.SplitSentences],
        default=deepl.SplitSentences.DEFAULT.value,
        help="control sentence splitting before translation, see API for "
        "information",
    )
    parser_text.add_argument(
        "--preserve-formatting",
        action="store_true",
        help="leave original formatting unchanged during translation",
    )
    parser_text.add_argument(
        "--show-billed-characters",
        dest="show_billed_characters",
        action="store_true",
        help="print billed characters for each text",
    )
    parser_text.add_argument(
        "--show-model-type-used",
        dest="show_model_type_used",
        action="store_true",
        help="print the model type used for each text",
    )
    parser_text.add_argument(
        "--model-type",
        type=str,
        choices=[enum.value for enum in deepl.ModelType],
        default=None,
        help="control model used for translation, see API for information",
    )
    parser_text.add_argument(
        "--style-id",
        dest="style_rule",
        type=str,
        help="ID of style rule to use for translation",
    )
    parser_text.add_argument(
        "--translation-memory-id",
        dest="translation_memory",
        type=str,
        help="ID of translation memory to use for translation",
    )
    parser_text.add_argument(
        "--translation-memory-threshold",
        dest="translation_memory_threshold",
        type=int,
        help="minimum matching percentage (0-100) for translation memory "
        "fuzzy matches, recommended minimum is 75",
    )
    parser_text.add_argument(
        "--custom-instructions",
        dest="custom_instructions",
        action="append",
        type=str,
        help="custom instructions to guide translation (can be specified "
        "multiple times, max 10 instructions, each max 300 characters)",
    )
    parser_text.add_argument(
        "text",
        nargs="+",
        type=str,
        help="text to be translated. Wrap text in quotes to prevent the shell "
        'from splitting sentences into words. Alternatively, use "-" to read '
        "from standard-input.",
    )
    parser_text.add_argument(
        "--show-detected-source",
        action="store_true",
        help="print detected source language for each text",
    )

    tag_handling_group = parser_text.add_argument_group(
        "tag-handling",
        description="Arguments controlling tag handling, for example XML. "
        "The -tags arguments accept multiple arguments, as comma-"
        "separated lists and as repeated arguments. For example, these are "
        'equivalent: "--ignore-tags a --ignore-tags b,c" and "--ignore-tags '
        'a,b,c".',
    )
    tag_handling_group.add_argument(
        "--tag-handling",
        type=str,
        choices=["xml", "html"],
        default=None,
        help="activate processing of formatting tags, for example 'xml'",
    )
    tag_handling_group.add_argument(
        "--tag-handling-version",
        type=str,
        choices=["v1", "v2"],
        default=None,
        help="specify which version of the tag handling algorithm to use",
    )
    tag_handling_group.add_argument(
        "--outline-detection-off",
        dest="outline_detection",
        default=True,
        action="store_false",
        help="disable automatic tag selection",
    )
    tag_handling_group.add_argument(
        "--non-splitting-tags",
        type=str,
        action="append",
        metavar="tag",
        help="specify tags that may occur within sentences",
    )
    tag_handling_group.add_argument(
        "--splitting-tags",
        type=str,
        action="append",
        metavar="tag",
        help="specify tags that separate text into sentences",
    )
    tag_handling_group.add_argument(
        "--ignore-tags",
        type=str,
        action="append",
        metavar="tag",
        help="specify tags containing text that should not be translated",
    )

    # create the parser for the "rephrase" command
    parser_rephrase = subparsers.add_parser(
        "rephrase", help="rephrase text(s)", description="rephrase text(s)"
    )
    parser_rephrase.add_argument(
        "--to",
        "--target-lang",
        dest="target_lang",
        required=True,
        help="language into which the text should be rewritten",
    )
    parser_rephrase.add_argument(
        "text",
        nargs="+",
        type=str,
        help="text to be rewritten. Wrap text in quotes to prevent the shell "
        'from splitting sentences into words. Alternatively, use "-" to read '
        "from standard-input.",
    )
    parser_rephrase.add_argument(
        "--show-detected-source",
        action="store_true",
        help="print detected source language for each text",
    )

    # create the parser for the "document" command
    parser_document = subparsers.add_parser(
        "document",
        help="translate document(s)",
        description="translate document(s)",
    )
    add_common_arguments(parser_document)
    parser_document.add_argument(
        "--style-id",
        dest="style_rule",
        type=str,
        help="ID of style rule to use for translation",
    )
    parser_document.add_argument(
        "--translation-memory-id",
        dest="translation_memory",
        type=str,
        help="ID of translation memory to use for translation",
    )
    parser_document.add_argument(
        "--translation-memory-threshold",
        dest="translation_memory_threshold",
        type=int,
        help="minimum matching percentage (0-100) for translation memory "
        "fuzzy matches, recommended minimum is 75",
    )
    parser_document.add_argument(
        "file", nargs="+", help="file(s) to be translated."
    )
    parser_document.add_argument(
        "--output-format", type=str, default=None, help="output file extension"
    )
    parser_document.add_argument(
        "dest", help="destination directory to store translated files."
    )

    # create the parser for the "usage" command
    usage_help_str = "print usage information for the current billing period"
    subparsers.add_parser(
        "usage", help=usage_help_str, description=usage_help_str
    )

    # create the parser for the "languages" command
    languages_help_str = "print available languages"
    parser_languages = subparsers.add_parser(
        "languages", help=languages_help_str, description=languages_help_str
    )
    parser_languages.add_argument(
        "--glossary",
        help="list language pairs supported for glossaries.",
        action="store_true",
    )

    # create the parser for the "glossary" command
    parser_glossary = subparsers.add_parser(
        "glossary",
        help="create, list, and remove glossaries",
        description="manage glossaries using subcommands",
    )

    glossary_subparsers = parser_glossary.add_subparsers(
        metavar="subcommand", dest="subcommand", required=True
    )
    parser_glossary_create = glossary_subparsers.add_parser(
        "create",
        help="create a new glossary",
        description="create a new glossary using entries provided via command-"
        "line, standard-input, or specified in a TSV or CSV file",
    )
    parser_glossary_create.add_argument(
        "--name", required=True, help="name to be associated with glossary."
    )
    parser_glossary_create.add_argument(
        "--from",
        "--source-lang",
        dest="source_lang",
        required=True,
        help="language in which source entries of the glossary are specified.",
    )
    parser_glossary_create.add_argument(
        "--to",
        "--target-lang",
        dest="target_lang",
        required=True,
        help="language in which target entries of the glossary are specified.",
    )
    parser_glossary_create.add_argument(
        "entry_list",
        nargs="*",
        type=str,
        metavar="SOURCE=TARGET",
        help="one or more entries to add to glossary, may be repeated. "
        'Alternatively, use "-" to read entries from standard-input in TSV or '
        "CSV format (see --file argument for formatting information). These "
        "arguments cannot be used together with the --file argument.",
    )
    parser_glossary_create.add_argument(
        "--file",
        type=str,
        help="file to read glossary entries from. Unless --csv is specified, "
        "file format is expected to be tab-separated values (TSV) format: one "
        "entry-pair per line, each line contains the source entry, a tab, "
        "then the target entry. Empty lines are ignored.",
    )
    parser_glossary_create.add_argument(
        "--csv",
        action="store_true",
        help="the provided --file option or standard-input should be "
        "interpreted as a CSV file. Information about the expected CSV format "
        "can be found in the API documentation: "
        "https://www.deepl.com/docs-api/managing-glossaries/supported-glossary-formats/.",  # noqa
    )

    parser_glossary_list = glossary_subparsers.add_parser(
        "list",
        help="list available glossaries",
        description="list available glossaries",
    )
    _ = parser_glossary_list  # Suppress unused variable warning

    parser_glossary_get = glossary_subparsers.add_parser(
        "get",
        help="print details about one glossary",
        description="print details about one glossary",
    )
    parser_glossary_get.add_argument(
        "glossary_id",
        metavar="id",
        type=str,
        help="ID of glossary to retrieve",
    )

    parser_glossary_entries = glossary_subparsers.add_parser(
        "entries",
        help="get entries contained in a glossary",
        description="get entries contained in a glossary, and print them to "
        "standard-output in tab-separated values (TSV) format: one entry-pair "
        "per line, each line contains the source entry, a tab, then the "
        "target entry.",
    )
    parser_glossary_entries.add_argument(
        "glossary_id",
        metavar="id",
        type=str,
        help="ID of glossary to retrieve",
    )

    parser_glossary_delete = glossary_subparsers.add_parser(
        "delete",
        help="delete one or more glossaries",
        description="delete one or more glossaries",
    )
    parser_glossary_delete.add_argument(
        "glossary_id_list",
        metavar="id",
        nargs="+",
        type=str,
        help="ID of glossary to delete",
    )

    # create the parser for the "translation-memory" command
    parser_tm = subparsers.add_parser(
        "translation-memory",
        help="list, inspect, import, export, and remove translation memories",
        description="manage translation memories using subcommands",
    )

    tm_subparsers = parser_tm.add_subparsers(
        metavar="subcommand", dest="subcommand", required=True
    )

    parser_tm_list = tm_subparsers.add_parser(
        "list",
        help="list available translation memories",
        description="list available translation memories",
    )
    parser_tm_list.add_argument(
        "--page",
        type=int,
        default=None,
        help="page number to retrieve, 0-indexed",
    )
    parser_tm_list.add_argument(
        "--page-size",
        type=int,
        default=None,
        help="number of translation memories per page",
    )

    parser_tm_get = tm_subparsers.add_parser(
        "get",
        help="print details about one translation memory",
        description="print details about one translation memory",
    )
    parser_tm_get.add_argument(
        "translation_memory_id",
        metavar="id",
        type=str,
        help="ID of translation memory to retrieve",
    )

    parser_tm_segments = tm_subparsers.add_parser(
        "segments",
        help="list the segments of a translation memory",
        description="list the segments of a translation memory, one row per "
        "source segment and target language",
    )
    parser_tm_segments.add_argument(
        "translation_memory_id",
        metavar="id",
        type=str,
        help="ID of translation memory whose segments to list",
    )
    parser_tm_segments.add_argument(
        "--page-size",
        type=int,
        default=None,
        help="maximum segments per page (1-100, defaults to 50)",
    )
    parser_tm_segments.add_argument(
        "--page-cursor",
        type=str,
        default=None,
        help="cursor from a previous response, to fetch the next page",
    )
    parser_tm_segments.add_argument(
        "--filter-text",
        type=str,
        default=None,
        help="substring filter across source and target text, at least 2 "
        "characters",
    )
    parser_tm_segments.add_argument(
        "--filter-case-sensitive",
        action="store_true",
        help="make --filter-text case-sensitive",
    )
    parser_tm_segments.add_argument(
        "--all",
        dest="all_pages",
        action="store_true",
        help="page through all segments instead of returning a single page",
    )

    parser_tm_delete = tm_subparsers.add_parser(
        "delete",
        help="delete one or more translation memories",
        description="delete one or more translation memories",
    )
    parser_tm_delete.add_argument(
        "translation_memory_id_list",
        metavar="id",
        nargs="+",
        type=str,
        help="ID of translation memory to delete",
    )

    parser_tm_import = tm_subparsers.add_parser(
        "import",
        help="import a TMX file as a new translation memory",
        description="import a TMX file as a new translation memory: creates "
        "the import job, uploads the file, and waits for processing to finish",
    )
    parser_tm_import.add_argument(
        "file",
        type=str,
        help="path of the TMX file to import",
    )
    parser_tm_import.add_argument(
        "--name",
        type=str,
        default=None,
        help="name for the resulting translation memory, defaults to the "
        "file name",
    )
    parser_tm_import.add_argument(
        "--no-wait",
        action="store_true",
        help="upload the file and print the job ID without waiting for "
        "processing to finish",
    )
    parser_tm_import.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="maximum number of seconds to wait for the import to finish",
    )

    parser_tm_export = tm_subparsers.add_parser(
        "export",
        help="export a translation memory to a TMX file",
        description="export a translation memory to a TMX file: creates the "
        "export job, waits for it to finish, and writes the result",
    )
    parser_tm_export.add_argument(
        "translation_memory_id",
        metavar="id",
        type=str,
        help="ID of translation memory to export",
    )
    parser_tm_export.add_argument(
        "output_file",
        metavar="file",
        type=str,
        help="path to write the exported TMX file to",
    )
    parser_tm_export.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="maximum number of seconds to wait for the export to finish",
    )

    parser_tm_job = tm_subparsers.add_parser(
        "job",
        help="print the status of an import or export job",
        description="print the status of a translation memory import or "
        "export job",
    )
    parser_tm_job.add_argument(
        "job_id",
        metavar="id",
        type=str,
        help="ID of the job to query",
    )

    return parser, parser_glossary


def main(args=None, prog_name=None):
    parser, parser_glossary = get_parser(prog_name)
    args = parser.parse_args(args)

    logger = logging.getLogger("deepl")
    if args.verbose == 1:
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())
    elif args.verbose >= 2:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())
    else:
        logger.setLevel(logging.WARNING)

    server_url = args.server_url or os.getenv(env_server_url)
    proxy_url = args.proxy_url or os.getenv(env_proxy_url)

    auth_key = args.auth_key or os.getenv(env_auth_key)
    keyring = _optional_import("keyring")
    if keyring:
        keyring_pw = None
        try:
            keyring_pw = keyring.get_password(
                keyring_key_folder, keyring_key_name
            )
        except keyring.errors.NoKeyringError:
            pass
        auth_key = auth_key or keyring_pw

    try:
        if auth_key is None:
            raise Exception(
                f"Please provide authentication key via the {env_auth_key} "
                "environment variable or --auth-key argument or via "
                f"{keyring_key_name} in {keyring_key_folder} in keyring"
            )

        # Note: the get_languages() call to verify language codes is skipped
        #       because the CLI makes one API call per execution.
        deepl_client = deepl.DeepLClient(
            auth_key=auth_key,
            server_url=server_url,
            proxy=proxy_url,
            skip_language_check=True,
            send_platform_info=not args.noplatforminfo,
        )

        if args.command in ["text", "translate", "rephrase"]:
            if len(args.text) == 1 and args.text[0] == "-":
                args.text = [sys.stdin.read()]

        # Remove global args so they are not unrecognised in action functions
        del (
            args.verbose,
            args.server_url,
            args.auth_key,
            args.proxy_url,
            args.noplatforminfo,
        )
        args = vars(args)
        # Call action function corresponding to command with remaining args
        # ("translation-memory" maps to action_translation_memory).
        command = args.pop("command").replace("-", "_")
        globals()[f"action_{command}"](deepl_client, **args)

    except Exception as exception:
        sys.stderr.write(f"Error: {exception}\n")
        sys.exit(1)


if __name__ == "__main__":
    main(prog_name="deepl")
