# Copyright 2023 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import json
import logging
from typing import Any, Callable, List, Tuple
from collections.abc import Iterable

from deepl.translator import TextResult


def batch_translate(
    input_handler_pairs: List[Tuple[str, Callable[[deepl.TextResult], None]]],
    target_lang: str,
    translator: deepl.DeepLClient,
    **kwargs,
) -> None:
    """
    Takes a list of translation inputs and result handlers, translates all
    inputs and calls each handler with the translation results.
    """
    inputs = [input_str for input_str, _ in input_handler_pairs]
    handlers = [handler for _, handler in input_handler_pairs]
    results = translator.translate_text(
        inputs, target_lang=target_lang, **kwargs
    )
    assert isinstance(results, list)
    for result, handler in zip(results, handlers):
        handler(result)


def parse_json_for_translation(
    obj: Any,
    translation_candidates: List[
        Tuple[str, Callable[[deepl.TextResult], None]]
    ],
):
    """
    Steps into the given JSON object and adds all strings to
    translation candidates list
    """

    keys: Iterable = []
    if type(obj) is dict:
        keys = obj.keys()
    elif type(obj) is list:
        keys = range(len(obj))
    else:
        return

    for key in keys:
        if type(obj[key]) is str:
            current_obj = obj
            current_key = key
            assign = lambda val: current_obj.__setitem__(current_key, val.text)
            translation_candidates.append((obj[key], assign))
        else:
            parse_json_for_translation(obj[key], translation_candidates)


def translate_json(
    json_input: str,
    target_lang: str,
    translator: deepl.DeepLClient,
    **kwargs,
) -> str:
    """
    Translates given JSON input using the DeepL API.

    Most of the arguments of the translate_text function are supported,
    source_lang, target_lang, glossary_id, formality, etc.

    :param json_input: JSON input to be translated.
    :param target_lang: language code to translate template into, for example
        "DE", "EN-US", "FR".
    :param translator: deepl.DeepLClient to use for translation.
    :return: Translated JSON.
    """

    logger = logging.getLogger("deepl")
    obj = json.loads(json_input)
    # Wrap the JSON object in an array, in case the input is a string
    obj = [obj]

    # Find all text in the JSON that is to be translated
    translation_candidates: List[
        Tuple[str, Callable[[deepl.TextResult], None]]
    ] = []
    parse_json_for_translation(obj, translation_candidates)
    logger.info(
        f"Found {len(translation_candidates)} strings to be translated"
    )

    # Translate all texts
    batch_translate(translation_candidates, target_lang, translator, **kwargs)
    logger.info("Translation complete")

    # Unwrap the dummy array and convert to JSON
    return json.dumps(obj[0])
