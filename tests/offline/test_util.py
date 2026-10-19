# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime

import deepl
from deepl.util import parse_timestamp
import pytest


def test_convert_tsv_to_dict():
    result = deepl.convert_tsv_to_dict("Apple\tApfel\n\nBanana \t Banane  ")
    assert result == {"Apple": "Apfel", "Banana": "Banane"}

    with pytest.raises(ValueError, match="does not contain separator"):
        deepl.convert_tsv_to_dict("no separator")

    with pytest.raises(ValueError, match="more than one term separator"):
        deepl.convert_tsv_to_dict("too\tmany\tseparators")

    with pytest.raises(ValueError, match="duplicates source term"):
        deepl.convert_tsv_to_dict("source\ttarget1\nsource\ttarget2")


def test_convert_dict_to_tsv():
    result = deepl.convert_dict_to_tsv(
        {"Apple": "Apfel", "Banana ": " Banane  "}
    )
    assert result == "Apple\tApfel\nBanana\tBanane"

    with pytest.raises(ValueError, match="invalid character"):
        deepl.convert_dict_to_tsv({"source\t1": "target"})

    with pytest.raises(ValueError, match="not a valid string"):
        deepl.convert_dict_to_tsv({"": "target"})
    with pytest.raises(ValueError, match="not a valid string"):
        deepl.convert_dict_to_tsv({"\t": "target"})


def test_parse_timestamp_microseconds():
    """Standard 6-digit fractional seconds should parse correctly."""
    result = parse_timestamp("2025-01-15T10:30:00.123456+0000")
    assert result == datetime.datetime(
        2025, 1, 15, 10, 30, 0, 123456, tzinfo=datetime.timezone.utc
    )


def test_parse_timestamp_nanoseconds():
    """7-digit fractional seconds (nanoseconds) should be truncated to 6."""
    result = parse_timestamp("2025-01-15T10:30:00.1234567+0000")
    assert result == datetime.datetime(
        2025, 1, 15, 10, 30, 0, 123456, tzinfo=datetime.timezone.utc
    )


def test_parse_timestamp_extra_nanoseconds():
    """9-digit fractional seconds should be truncated to 6."""
    result = parse_timestamp("2025-01-15T10:30:00.123456789+0000")
    assert result == datetime.datetime(
        2025, 1, 15, 10, 30, 0, 123456, tzinfo=datetime.timezone.utc
    )
