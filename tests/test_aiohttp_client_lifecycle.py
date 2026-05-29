# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

"""Unit tests for resource-lifecycle behaviour in AioHttpClient.
- streaming/buffered responses must `release()` (not sync `close()`) so
  the aiohttp connection pool can reclaim sockets.
- sessions abandoned on event-loop change must not be silently leaked
  via `loop.create_task()`; they're queued and drained in `close()`.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("aiohttp")

from deepl.aiohttp_client import (  # noqa: E402
    AioHttpClient,
    _AioHttpStreamingResponse,
)

pytestmark = pytest.mark.asyncio


async def test_streaming_response_close_awaits_release():
    resp = MagicMock()
    resp.status = 200
    resp.headers = {}
    resp.release = AsyncMock()
    resp.close = MagicMock()

    streaming = _AioHttpStreamingResponse(resp)
    await streaming.close()

    resp.release.assert_awaited_once()
    resp.close.assert_not_called()


async def test_stale_session_queued_not_fire_and_forget(monkeypatch):
    import deepl.aiohttp_client as mod

    new_session = MagicMock()
    new_session.closed = False
    new_session.close = AsyncMock()
    monkeypatch.setattr(mod.aiohttp, "ClientSession", lambda **kw: new_session)
    monkeypatch.setattr(mod.aiohttp, "TCPConnector", lambda **kw: MagicMock())

    client = AioHttpClient()
    old_session = MagicMock()
    old_session.closed = False
    old_session.close = AsyncMock()
    client._session = old_session
    # Distinct sentinel — any value other than the current running loop
    # makes `_get_session` treat the prior session as stale.
    client._session_loop = MagicMock()

    client._get_session()

    assert old_session in client._pending_close_sessions
    old_session.close.assert_not_called()
    assert client._session is new_session


async def test_close_drains_pending_sessions():
    client = AioHttpClient()
    s1, s2 = MagicMock(), MagicMock()
    for s in (s1, s2):
        s.closed = False
        s.close = AsyncMock()
    client._pending_close_sessions = [s1, s2]

    await client.close()

    s1.close.assert_awaited_once()
    s2.close.assert_awaited_once()
    assert client._pending_close_sessions == []


async def test_close_swallows_errors_from_dead_loop_sessions():
    client = AioHttpClient()
    bad = MagicMock()
    bad.closed = False
    bad.close = AsyncMock(side_effect=RuntimeError("loop is closed"))
    client._pending_close_sessions = [bad]

    await client.close()  # must not raise

    assert client._pending_close_sessions == []
