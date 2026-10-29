# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
import time

import deepl

from .client import make_admin_client
from .helpers import get_unique_name


def _past_week():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    return today - datetime.timedelta(days=7), today


def test_get_usage_analytics():
    start, end = _past_week()

    report = make_admin_client().get_usage_analytics(
        start, end, group_by=deepl.AdminUsageGroupBy.KEY_AND_DAY
    )

    assert isinstance(report.total_usage, deepl.AdminUsageBreakdown)
    assert report.start_date is not None
    assert report.start_date.tzinfo is not None
    assert report.end_date is not None
    assert report.group_by == "keyAndDay"


def test_get_custom_tag_usage_analytics():
    start, end = _past_week()

    report = make_admin_client().get_custom_tag_usage_analytics(
        start, end, aggregate_by=deepl.CustomTagUsageAggregateBy.DAY
    )

    assert report.start_date is not None
    assert report.end_date is not None
    assert report.aggregate_by == "day"
    assert isinstance(report.usage, list)


def _assert_key_listed(client, key_id, attempts=5):
    # A newly created key can be briefly invisible to the list call.
    for attempt in range(attempts):
        if key_id in [k.key_id for k in client.list_developer_keys()]:
            return
        if attempt < attempts - 1:
            time.sleep(1)
    raise AssertionError(
        f"New developer key not listed after {attempts} attempts"
    )


def test_developer_key_lifecycle():
    client = make_admin_client()
    key = client.create_developer_key(label=get_unique_name("admin-key"))
    deactivated = False
    try:
        assert not key.is_deactivated
        _assert_key_listed(client, key.key_id)

        new_label = get_unique_name("admin-key-renamed")
        assert client.rename_developer_key(key, new_label).label == new_label

        limits = client.set_developer_key_usage_limits(
            key, characters=5000, speech_to_text_milliseconds=None
        ).usage_limits
        assert limits.characters == 5000
        assert limits.speech_to_text_milliseconds is None

        assert client.deactivate_developer_key(key).is_deactivated
        deactivated = True
    finally:
        if not deactivated:
            try:
                client.deactivate_developer_key(key)
            except deepl.DeepLException as e:
                if e.http_status_code != 404:
                    raise
