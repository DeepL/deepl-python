# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl

from .client import make_deepl_client


def test_parses_usage():
    usage = make_deepl_client().get_usage()

    assert isinstance(usage, deepl.Usage)
    assert "Usage this billing period" in str(usage)
