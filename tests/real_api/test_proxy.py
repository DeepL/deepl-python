# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import ipaddress

import deepl
import proxy
import pytest

from .client import make_translator


def test_sends_requests_through_proxy(monkeypatch, tmp_path):
    monkeypatch.setattr(deepl.http_client, "max_network_retries", 0)

    # proxy.py writes below the home directory unless told otherwise, which CI
    # runners do not have.
    with proxy.Proxy(
        input_args=[
            "--data-dir",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
        port=0,
        hostname=ipaddress.ip_address("127.0.0.1"),
        num_workers=1,
        num_acceptors=1,
    ) as local_proxy:
        translator = make_translator(
            proxy=f"http://127.0.0.1:{local_proxy.flags.port}"
        )

        assert isinstance(translator.get_usage(), deepl.Usage)

    with pytest.raises(
        deepl.ConnectionException, match="Unable to connect to proxy"
    ):
        translator.get_usage()
