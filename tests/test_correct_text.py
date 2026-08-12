# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .conftest import example_text, needs_real_server
from deepl.api_data import WriteResult


@needs_real_server
def test_single_text(deepl_client):
    result = deepl_client.correct_text(example_text["EN"], target_lang="EN-GB")
    _check_sanity_of_improvements(example_text["EN"], result)


@needs_real_server
def test_multiple_texts(deepl_client):
    input_texts = [example_text["EN"], example_text["EN"]]
    results = deepl_client.correct_text(input_texts, target_lang="EN-US")
    assert len(results) == len(input_texts)
    for input_text, result in zip(input_texts, results):
        _check_sanity_of_improvements(input_text, result)


def _check_sanity_of_improvements(
    input_text: str,
    result: WriteResult,
    expected_lang_uppercase="EN",
    epsilon=0.2,
):
    assert result.detected_source_language.upper() == expected_lang_uppercase
    n_improved = len(result.text)
    n_original = len(input_text)
    assert 1 / (1.0 + epsilon) <= n_improved / n_original <= (1.0 + epsilon)
