# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryConfig:
    """Immutable configuration for HTTP retry and backoff behaviour.

    Passed to DeepLClient / DeepLClientAsync. The same config applies to
    all requests; construct a second client if you need different settings
    for a subset of calls.

    :param max_retries: Maximum number of retry attempts (default 5).
    :param min_connection_timeout: Minimum timeout in seconds per attempt
        (default 10.0). Passed to the underlying HTTP client.
    :param backoff_initial: Initial backoff duration in seconds (default 1.0).
    :param backoff_max: Maximum backoff duration in seconds (default 120.0).
    :param backoff_multiplier: Multiplier applied to backoff after each retry
        (default 1.6).
    :param backoff_jitter: Jitter as a proportion of backoff (default 0.23).
        The actual sleep duration is backoff * (1 ± jitter).
    """

    max_retries: int = 5
    min_connection_timeout: float = 10.0
    backoff_initial: float = 1.0
    backoff_max: float = 120.0
    backoff_multiplier: float = 1.6
    backoff_jitter: float = 0.23
