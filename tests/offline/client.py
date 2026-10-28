# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import warnings

import deepl

SERVER_URL = "https://api.deepl.com"
AUTH_KEY = "k"
AUTH_HEADER = f"DeepL-Auth-Key {AUTH_KEY}"


def url(path: str) -> str:
    return f"{SERVER_URL}/{path}"


def make_translator(**kwargs) -> deepl.Translator:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", "Translator is deprecated", DeprecationWarning
        )
        return deepl.Translator(AUTH_KEY, **kwargs)


def make_deepl_client(**kwargs) -> deepl.DeepLClient:
    return deepl.DeepLClient(AUTH_KEY, **kwargs)


def make_admin_client(**kwargs) -> deepl.DeepLAdminClient:
    return deepl.DeepLAdminClient(AUTH_KEY, **kwargs)
