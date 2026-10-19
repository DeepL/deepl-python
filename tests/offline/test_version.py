# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl


def test_version():
    assert "1.32.0" == deepl.__version__
