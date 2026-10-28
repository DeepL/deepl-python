# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import pytest
import responses


@pytest.fixture(autouse=True)
def mocked():
    """Intercepts every request sent through the requests library, so nothing
    reaches the network. A test fails at teardown if it declared a request
    that the SDK did not send."""
    with responses.RequestsMock(assert_all_requests_are_fired=True) as mocked:
        yield mocked


@pytest.fixture
def no_retries(monkeypatch):
    """Makes the SDK fail on the first 429, 5xx or connection error instead
    of retrying with backoff."""
    # Patch the module dict: assigning the deprecated global would warn.
    monkeypatch.setitem(vars(deepl.http_client), "max_network_retries", 0)
