# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

# Backward-compatibility shim.
# `Translator` was the original public class name; `DeepLClient` is preferred.
from .deepl_client import DeepLClient as Translator  # noqa: F401

# Re-export api_data types that were historically importable from this module.
from .api_data import (  # noqa: F401
    DocumentHandle,
    DocumentStatus,
    Formality,
    GlossaryInfo,
    Language,
    ModelType,
    SplitSentences,
    TextResult,
    TranslationMemoryInfo,
    Usage,
)
