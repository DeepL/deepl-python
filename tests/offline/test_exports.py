# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import inspect

import deepl
from deepl import api_data


def test_exports_every_public_api_data_class():
    public = {
        name
        for name, cls in inspect.getmembers(api_data, inspect.isclass)
        if cls.__module__ == api_data.__name__ and not name.startswith("_")
    }
    assert sorted(public - set(deepl.__all__)) == []
    for name in public:
        assert getattr(deepl, name) is getattr(api_data, name)
