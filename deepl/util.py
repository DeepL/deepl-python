# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.
import csv
import datetime
import importlib
import io
import itertools
import logging
import re
import warnings
from typing import Any, BinaryIO, Dict, Optional, TextIO, Union

logger = logging.getLogger("deepl")


def _optional_import(module_name: str):
    """Tries importing the specified module and returns it if successful,
    else None.
    Example:

    keyring = _optional_import('keyring')
    if keyring:
        keyring.get_password(...)
    else:
        # Code to handle the module not being present
        pass

    :param module_name: str containing the exact module name
    :return: The module, if the import was successful, or None
    """
    try:
        module = importlib.import_module(module_name)
        return module
    except ImportError:
        return None


def _get_log_text(message, **kwargs):
    return (
        message
        + " "
        + " ".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
    )


def log_debug(message, **kwargs):
    text = _get_log_text(message, **kwargs)
    logger.debug(text)


def log_info(message, **kwargs):
    text = _get_log_text(message, **kwargs)
    logger.info(text)


def get_int_safe(d: Optional[dict], key: str) -> Optional[int]:
    """Returns value in dictionary with given key as int, or None."""
    try:
        return int(d.get(key) if d else None)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def get_float_safe(d: Optional[dict], key: str) -> Optional[float]:
    """Returns value in dictionary with given key as float, or None."""
    try:
        return float(d.get(key) if d else None)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def is_free_account_auth_key(auth_key: str) -> bool:
    """Returns True if the given authentication key belongs to a DeepL API Free
    account, otherwise False."""
    return auth_key.strip().endswith(":fx")


def auth_key_is_free_account(auth_key: str) -> bool:
    """Returns True if the given authentication key belongs to a DeepL API Free
    account, otherwise False.

    .. deprecated::
        Use is_free_account_auth_key() instead.
    """
    warnings.warn(
        "auth_key_is_free_account is deprecated, use is_free_account_auth_key",
        DeprecationWarning,
        stacklevel=2,
    )
    return auth_key.endswith(":fx")


def validate_glossary_term(term: str) -> None:
    """Checks if the given glossary term contains any disallowed characters.

    :param term: Glossary term to check for validity.
    :raises ValueError: If the term is not valid or a disallowed character is
    found."""
    if len(term) == 0:
        raise ValueError(f'Term "{term}" is not a valid string')
    if any(
        (
            0 <= ord(char) <= 31  # C0 control characters
            or 128 <= ord(char) <= 159  # C1 control characters
            or char in "\u2028\u2029"  # Unicode newlines
        )
        for char in term
    ):
        raise ValueError(f'Term "{term}" contains invalid character')


def convert_tsv_to_dict(
    tsv: str, term_separator: str = "\t", skip_checks: bool = False
) -> dict:
    """Converts the given tab-separated values (TSV) string to an entries
    dictionary for use in a glossary. Each line should contain a source and
    target term separated by a tab. Empty lines are ignored.

    :param tsv: string containing TSV to parse.
    :param term_separator: optional term separator to use.
    :param skip_checks: set to True to override entry validation.
    :return: dictionary containing parsed entries.
    """
    entries_dict = {}
    for line, index in zip(tsv.splitlines(), itertools.count(1)):
        if not line:
            continue
        if term_separator not in line:
            raise ValueError(
                f"Entry {index} does not contain separator: {line}"
            )
        source, target = line.split(term_separator, 1)
        source, target = source.strip(), target.strip()
        if source in entries_dict:
            raise ValueError(
                f'Entry {index} duplicates source term "{source}"'
            )
        if term_separator in target:
            raise ValueError(
                f"Entry {index} contains more than one term separator: {line}"
            )
        if not skip_checks:
            validate_glossary_term(source)
            validate_glossary_term(target)
        entries_dict[source] = target
    return entries_dict


def convert_dict_to_tsv(
    entry_dict: Dict[str, str], skip_checks: bool = False
) -> str:
    """Converts the given glossary entries dictionary to a tab-separated values
    (TSV) string.

    :param entry_dict: dictionary containing glossary entries.
    :param skip_checks: set to True to override entry validation.
    :return: string containing entries in TSV format.
    """
    if not skip_checks:
        for source, target in entry_dict.items():
            validate_glossary_term(source.strip())
            validate_glossary_term(target.strip())

    return "\n".join(
        f"{s.strip()}\t{t.strip()}" for s, t in entry_dict.items()
    )


def convert_csv_to_dict(
    csv_data: Union[TextIO, BinaryIO, str, bytes, Any],
    skip_checks: bool = False,
) -> Dict[str, str]:
    """Converts the given comma-separated values (CSV) string to an entries
    dictionary for use in a glossary. Each line should contain a source and
    target term separated by a comma or a source term, target term, source
    language code, and target language code all separated by commas.
    Empty lines are ignored.

    :param tsv: string containing CSV to parse.
    :param skip_checks: set to True to override entry validation.
    :return: dictionary containing parsed entries.
    """
    entries_dict = {}
    csv_string = (
        csv_data if isinstance(csv_data, (str, bytes)) else csv_data.read()
    )

    if not isinstance(csv_string, (bytes, str)):
        raise ValueError("Entries of the glossary are invalid")

    if isinstance(csv_string, bytes):
        csv_string = csv_string.decode("utf-8")

    if isinstance(csv_string, str):
        csv_string = io.StringIO(csv_string)

    reader = csv.reader(csv_string)

    for line, index in zip(reader, itertools.count(1)):
        if not line:
            continue
        source, target = line[0].strip(), line[1].strip()
        if source in entries_dict:
            raise ValueError(
                f'Entry {index} duplicates source term "{source}"'
            )
        if not skip_checks:
            validate_glossary_term(source)
            validate_glossary_term(target)
        entries_dict[source] = target
    return entries_dict


def parse_timestamp(creation_time: str) -> datetime.datetime:
    # Truncate fractional seconds to 6 digits (microseconds) since Python's
    # %f only handles up to 6 digits, but the API may return 7 (nanoseconds).
    creation_time = re.sub(r"(\.\d{6})\d+", r"\1", creation_time)
    # Some timestamps (e.g. the usage billing period) have no fraction.
    fmt = (
        "%Y-%m-%dT%H:%M:%S.%f%z"
        if "." in creation_time
        else "%Y-%m-%dT%H:%M:%S%z"
    )
    return datetime.datetime.strptime(creation_time, fmt)
