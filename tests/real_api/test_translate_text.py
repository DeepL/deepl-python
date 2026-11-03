# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl

from ..fixtures import example_text
from .client import make_deepl_client


def test_parses_translation():
    result = make_deepl_client().translate_text(
        example_text["EN"], target_lang="DE"
    )

    assert isinstance(result, deepl.TextResult)
    assert result.detected_source_lang
    assert isinstance(result.billed_characters, int)
