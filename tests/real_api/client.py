# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import os
from typing import Optional

import deepl


def _auth_key() -> str:
    auth_key = os.environ.get("DEEPL_AUTH_KEY")
    if not auth_key:
        raise RuntimeError(
            "The real-API tests need the DEEPL_AUTH_KEY environment variable "
            "(and DEEPL_SERVER_URL for a non-default server)."
        )
    return auth_key


def server_url() -> Optional[str]:
    return os.environ.get("DEEPL_SERVER_URL") or None


def make_translator(**kwargs) -> deepl.Translator:
    return deepl.Translator(_auth_key(), server_url=server_url(), **kwargs)


def make_deepl_client(**kwargs) -> deepl.DeepLClient:
    return deepl.DeepLClient(_auth_key(), server_url=server_url(), **kwargs)
