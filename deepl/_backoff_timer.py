# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import random
import time
from typing import Callable

from .retry_config import RetryConfig


class BackoffTimer:
    """Exponential-backoff timer. Pure logic — no sleeping.

    Based on the gRPC Connection Backoff Protocol:
    https://github.com/grpc/grpc/blob/master/doc/connection-backoff.md

    Usage in a retry loop::

        timer = BackoffTimer(config)
        while True:
            try:
                result = attempt()
                return result
            except RetryableError:
                if timer.get_num_retries() >= config.max_retries:
                    raise
                sleep_fn(timer.get_time_until_deadline())
                timer.advance()

    :param config: RetryConfig controlling backoff parameters.
    :param time_fn: Clock function (default time.time). Override in tests to
        control perceived time without actual sleeping.

    .. note::
        The first backoff deadline is set at construction time, not after the
        first failure. If the initial attempt itself is slow (e.g. it times out
        after many seconds), the first retry sleep may be shorter than
        ``backoff_initial``. This is consistent with the gRPC backoff protocol.
    """

    def __init__(
        self,
        config: RetryConfig,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._time_fn = time_fn
        self._num_retries = 0
        self._backoff = config.backoff_initial
        self._deadline = time_fn() + self._backoff

    def get_num_retries(self) -> int:
        """Return the number of retries that have been recorded so far."""
        return self._num_retries

    def get_time_until_deadline(self) -> float:
        """Return seconds until the current backoff deadline (≥ 0)."""
        return max(self._deadline - self._time_fn(), 0.0)

    def get_timeout(self, min_timeout: float) -> float:
        """Return the connection timeout to use for the current attempt.

        Returns ``max(time_until_deadline, min_timeout)`` so that later
        retries — which have longer backoff periods — also receive
        proportionally longer connection timeouts.
        """
        return max(self.get_time_until_deadline(), min_timeout)

    def advance(self) -> None:
        """Record a completed retry and compute the next backoff deadline.

        Call this *after* sleeping
        (i.e. after sleep_fn(get_time_until_deadline())).
        """
        self._backoff = min(
            self._backoff * self._config.backoff_multiplier,
            self._config.backoff_max,
        )
        self._deadline = self._time_fn() + self._backoff * (
            1 + self._config.backoff_jitter * random.uniform(-1, 1)
        )
        self._num_retries += 1
