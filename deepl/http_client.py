# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

# Backward-compatibility shim.
# The public `HttpClient` class has been replaced by `RequestsClient`.
# `_BackoffTimer` has been replaced by `BackoffTimer` in `_backoff_timer.py`.
# Module-level globals (`max_network_retries`, `min_connection_timeout`) are
# preserved for old code but are deprecated.  Set them to emit a
# DeprecationWarning; they are honoured by DeepLClient as long as they are
# set BEFORE the client is constructed.  Use RetryConfig instead.

import sys
import types
import warnings

from .requests_client import RequestsClient as HttpClient  # noqa: F401
from ._backoff_timer import BackoffTimer as _BackoffTimer  # noqa: F401
from ._client_base import _generate_user_agent  # noqa: F401
from .exceptions import ConnectionException, DeepLException  # noqa: F401

# Deprecated.  Set before constructing a DeepLClient to override the
# User-Agent header.  Use DeepLClient.set_user_agent() instead.
user_agent = None

# Deprecated.  Default None means "not set by caller; use RetryConfig".
# Assign an int/float to override and receive a DeprecationWarning.
# Must be set before constructing a DeepLClient; values set afterwards
# are ignored.
max_network_retries = None
min_connection_timeout = None

_DEPRECATED_GLOBALS = frozenset(
    ("max_network_retries", "min_connection_timeout", "user_agent")
)

_DEPRECATION_MESSAGES = {
    "max_network_retries": (
        "deepl.http_client.max_network_retries is deprecated and will be "
        "removed in a future version. Use RetryConfig instead."
    ),
    "min_connection_timeout": (
        "deepl.http_client.min_connection_timeout is deprecated and will be "
        "removed in a future version. Use RetryConfig instead."
    ),
    "user_agent": (
        "deepl.http_client.user_agent is deprecated and will be removed in a "
        "future version. Use DeepLClient.set_user_agent() instead."
    ),
}


class _Module(types.ModuleType):
    """Module subclass that intercepts assignment to deprecated globals."""

    def __setattr__(self, name: str, value: object) -> None:
        if name in _DEPRECATED_GLOBALS:
            warnings.warn(
                _DEPRECATION_MESSAGES[name],
                DeprecationWarning,
                stacklevel=2,
            )
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _Module
