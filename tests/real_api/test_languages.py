# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl

from .client import make_deepl_client


def test_parses_source_languages():
    languages = make_deepl_client().get_source_languages()

    assert languages
    assert all(isinstance(lang, deepl.Language) for lang in languages)
    assert all(lang.code and lang.name for lang in languages)


def test_parses_language_resources():
    resources = make_deepl_client().get_language_resources()

    assert resources
    for resource in resources:
        assert resource.resource
        assert all(
            name == feature.name for name, feature in resource.features.items()
        )
