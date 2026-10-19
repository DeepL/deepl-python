# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.api_data import WriteResult

from ..fixtures import example_text
from .client import make_deepl_client


def test_parses_corrected_text():
    result = make_deepl_client().correct_text(
        example_text["EN"], target_lang="EN-GB"
    )

    assert isinstance(result, WriteResult)
    assert result.detected_source_language
    assert result.target_language
