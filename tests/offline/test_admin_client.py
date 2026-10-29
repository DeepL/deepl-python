# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
import socket

import pytest
import requests  # type: ignore
import urllib3

import deepl

from .client import make_admin_client, url
from .matchers import bodyless_request, json_request

UTC = datetime.timezone.utc
KEY_ID = (
    "ca7d5694-96eb-4263-a9a4-7f7e4211529e:20c2abcf-4c3c-4cd6-8ae8-8bd2a7d4da38"
)
DEVELOPER_KEY_JSON = {
    "key_id": KEY_ID,
    "label": "developer key prod",
    "creation_time": "2025-07-08T08:15:29.362Z",
    "deactivated_time": None,
    "is_deactivated": False,
    "usage_limits": {
        "characters": 5000,
        "speech_to_text_milliseconds": None,
        "speech_to_speech_milliseconds": 3600000,
    },
}


@pytest.mark.parametrize("admin_key", ["", "  "])
def test_rejects_empty_admin_key(admin_key):
    with pytest.raises(ValueError, match="must not be empty"):
        deepl.DeepLAdminClient(admin_key)


def test_server_url():
    assert make_admin_client().server_url == "https://api.deepl.com"
    client = make_admin_client(server_url="http://localhost:3000")
    assert client.server_url == "http://localhost:3000"


def test_get_usage_analytics(mocked):
    mocked.get(
        url("v2/admin/analytics"),
        match=bodyless_request(
            {
                "start_date": "2025-09-29",
                "end_date": "2025-10-01",
                "group_by": "key_and_day",
            }
        ),
        json={
            "usage_report": {
                "total_usage": {
                    "total_characters": 9619,
                    "text_translation_characters": 4892,
                    "document_translation_characters": 0,
                    "text_improvement_characters": 4727,
                    "speech_to_text_minutes": 107.46,
                    "speech_to_speech_minutes": 3.5,
                },
                "group_by": "keyAndDay",
                "start_date": "2025-09-29T00:00:00",
                "end_date": "2025-10-01T00:00:00",
                "key_and_day_usages": [
                    {
                        "api_key": "dc88****3a2c",
                        "api_key_label": "Staging API Key",
                        "usage_date": "2025-09-29T00:00:00Z",
                        "usage": {
                            "total_characters": 315,
                            "text_translation_characters": 159,
                            "document_translation_characters": 0,
                            "text_improvement_characters": 156,
                            "speech_to_text_minutes": 11.94,
                        },
                    }
                ],
            }
        },
    )

    report = make_admin_client().get_usage_analytics(
        datetime.date(2025, 9, 29),
        "2025-10-01",
        group_by=deepl.AdminUsageGroupBy.KEY_AND_DAY,
    )

    assert report.total_usage.speech_to_text_minutes == 107.46
    assert report.total_usage.speech_to_speech_minutes == 3.5
    assert report.group_by == "keyAndDay"
    assert report.start_date == datetime.datetime(2025, 9, 29, tzinfo=UTC)
    assert report.key_usages == []
    usage = report.key_and_day_usages[0]
    assert usage.api_key_label == "Staging API Key"
    assert usage.usage_date == datetime.datetime(2025, 9, 29, tzinfo=UTC)
    assert usage.usage.text_improvement_characters == 156
    assert usage.usage.speech_to_speech_minutes == 0


def test_get_custom_tag_usage_analytics(mocked):
    mocked.get(
        url("v2/admin/analytics/custom-tags"),
        match=bodyless_request(
            {
                "start_date": "2026-05-03",
                "end_date": "2026-05-15",
                "aggregate_by": "day",
                "page": "2",
            }
        ),
        json={
            "custom_tag_usage_report": {
                "aggregate_by": "day",
                "start_date": "2026-05-03T00:00:00",
                "end_date": "2026-05-15T00:00:00",
                "next_page": 3,
                "usage": [
                    {
                        "custom_tag": "example-custom-tag",
                        "usage_date": "2026-05-04T00:00:00Z",
                        "breakdown": {
                            "total_characters": 380,
                            "text_translation_characters": 380,
                            "text_improvement_characters": 0,
                            "speech_to_text_minutes": 12.5,
                            "speech_to_speech_minutes": 4.2,
                        },
                    }
                ],
            }
        },
    )

    report = make_admin_client().get_custom_tag_usage_analytics(
        datetime.datetime(2026, 5, 3, 23, 30, tzinfo=UTC),
        datetime.date(2026, 5, 15),
        aggregate_by=deepl.CustomTagUsageAggregateBy.DAY,
        page=2,
    )

    assert report.aggregate_by == "day"
    assert report.next_page == 3
    assert report.usage[0].breakdown.speech_to_speech_minutes == 4.2
    assert report.usage[0].usage_date == datetime.datetime(
        2026, 5, 4, tzinfo=UTC
    )
    assert report.end_date == datetime.datetime(2026, 5, 15, tzinfo=UTC)


def test_uses_utc_date_of_datetime(mocked):
    mocked.get(
        url("v2/admin/analytics"),
        match=bodyless_request(
            {"start_date": "2026-05-02", "end_date": "2026-05-04"}
        ),
        json={"usage_report": {}},
    )
    cest = datetime.timezone(datetime.timedelta(hours=2))
    start = datetime.datetime(2026, 5, 3, 1, 0, tzinfo=cest)
    end = datetime.datetime(2026, 5, 4, 23, 59)

    make_admin_client().get_usage_analytics(start, end)

    assert start == datetime.datetime(2026, 5, 3, 1, 0, tzinfo=cest)
    assert start.tzinfo is cest
    assert end == datetime.datetime(2026, 5, 4, 23, 59)


def test_utc_date_of_datetime_can_be_the_next_day(mocked):
    mocked.get(
        url("v2/admin/analytics"),
        match=bodyless_request(
            {"start_date": "2026-05-04", "end_date": "2026-05-05"}
        ),
        json={"usage_report": {}},
    )
    west = datetime.timezone(datetime.timedelta(hours=-5))

    make_admin_client().get_usage_analytics(
        datetime.datetime(2026, 5, 3, 20, 0, tzinfo=west),
        datetime.date(2026, 5, 5),
    )


@pytest.mark.parametrize(
    "date",
    ["2026-5-3", "20260503", "2026-02-30", "2026-05-03T00:00:00", 20260503],
)
def test_rejects_invalid_date(date):
    client = make_admin_client()
    with pytest.raises(ValueError, match="Invalid date"):
        client.get_usage_analytics(date, "2026-05-04")
    with pytest.raises(ValueError, match="Invalid date"):
        client.get_custom_tag_usage_analytics("2026-05-03", date)


def test_date_range_rejected_by_api_raises_exception(mocked):
    mocked.get(
        url("v2/admin/analytics"),
        status=400,
        json={"message": "start_date must be before end_date"},
    )

    with pytest.raises(deepl.DeepLException, match="must be before"):
        make_admin_client().get_usage_analytics("2026-05-04", "2026-05-03")


def test_response_with_malformed_values_is_parsed_tolerantly(mocked):
    mocked.get(
        url("v2/admin/analytics"),
        json={
            "usage_report": {
                "group_by": 5,
                "start_date": "not a timestamp",
                "total_usage": {
                    "total_characters": "x",
                    "speech_to_text_minutes": 1.5,
                },
                "key_usages": [
                    "oops",
                    {"api_key_label": "kept", "usage": []},
                    {},
                ],
                "key_and_day_usages": None,
            }
        },
    )
    mocked.get(
        url("v2/admin/analytics/custom-tags"),
        json={
            "custom_tag_usage_report": {
                "next_page": None,
                "usage": [1, {"custom_tag": "tag", "usage_date": 7}],
            }
        },
    )
    mocked.get(
        url("v2/admin/developer-keys"),
        json=[
            "oops",
            {"label": "no id"},
            dict(DEVELOPER_KEY_JSON, usage_limits={"characters": "many"}),
            dict(
                DEVELOPER_KEY_JSON,
                key_id="other",
                creation_time="not a timestamp",
                is_deactivated="false",
                usage_limits="none",
            ),
            dict(
                DEVELOPER_KEY_JSON,
                key_id="null-flag",
                is_deactivated=None,
                usage_limits={"characters": True},
            ),
        ],
    )
    client = make_admin_client()

    report = client.get_usage_analytics("2026-05-03", "2026-05-04")
    tags = client.get_custom_tag_usage_analytics("2026-05-03", "2026-05-04")
    keys = client.list_developer_keys()

    assert report.group_by is None
    assert report.start_date is None
    assert report.total_usage.total_characters == 0
    assert report.total_usage.speech_to_text_minutes == 1.5
    assert [k.api_key_label for k in report.key_usages] == ["kept", None]
    assert report.key_and_day_usages == []
    assert tags.next_page is None
    assert [(u.custom_tag, u.usage_date) for u in tags.usage] == [
        ("tag", None)
    ]
    assert [k.key_id for k in keys] == [KEY_ID, "other", "null-flag"]
    assert keys[0].label == "developer key prod"
    assert keys[0].usage_limits.characters is None
    assert keys[1].creation_time is None
    assert keys[1].is_deactivated is False
    assert keys[1].usage_limits is None
    assert keys[2].is_deactivated is False
    assert keys[2].usage_limits.characters is None


def test_absent_optional_key_fields_are_none(mocked):
    key_json = {
        k: v
        for k, v in DEVELOPER_KEY_JSON.items()
        if k not in ("label", "usage_limits")
    }
    mocked.get(url("v2/admin/developer-keys"), json=[key_json])

    key = make_admin_client().list_developer_keys()[0]

    assert key.label is None
    assert key.usage_limits is None
    assert str(key) == f"DeveloperKey ({KEY_ID})"
    assert "None" not in str(key)


def test_create_developer_key(mocked):
    mocked.post(
        url("v2/admin/developer-keys"),
        match=json_request({"label": "developer key prod"}),
        json=DEVELOPER_KEY_JSON,
    )

    key = make_admin_client().create_developer_key(label="developer key prod")

    assert key.key_id == KEY_ID
    assert key.creation_time == datetime.datetime(
        2025, 7, 8, 8, 15, 29, 362000, tzinfo=UTC
    )
    assert key.deactivated_time is None
    assert not key.is_deactivated
    assert key.usage_limits.characters == 5000
    assert key.usage_limits.speech_to_text_milliseconds is None
    assert key.usage_limits.speech_to_speech_milliseconds == 3600000


@pytest.mark.parametrize(
    "body", [[], "oops", {"label": "x"}, {"key_id": ""}, {"key_id": 5}]
)
def test_key_response_without_key_id_raises_exception(mocked, body):
    mocked.post(url("v2/admin/developer-keys"), json=body)
    mocked.put(url("v2/admin/developer-keys/label"), json=body)

    client = make_admin_client()
    with pytest.raises(deepl.DeepLException, match="key_id"):
        client.create_developer_key()
    with pytest.raises(deepl.DeepLException, match="key_id"):
        client.rename_developer_key(KEY_ID, "renamed")


def test_non_list_developer_keys_response_raises_exception(mocked):
    mocked.get(url("v2/admin/developer-keys"), json={"keys": []})

    with pytest.raises(deepl.DeepLException, match="not a list"):
        make_admin_client().list_developer_keys()


@pytest.mark.parametrize("body", [[], "oops", None])
def test_non_object_analytics_response_raises_exception(mocked, body):
    mocked.get(url("v2/admin/analytics"), json=body)
    mocked.get(url("v2/admin/analytics/custom-tags"), json=body)

    client = make_admin_client()
    with pytest.raises(deepl.DeepLException, match="not a JSON object"):
        client.get_usage_analytics("2026-05-03", "2026-05-04")
    with pytest.raises(deepl.DeepLException, match="not a JSON object"):
        client.get_custom_tag_usage_analytics("2026-05-03", "2026-05-04")


def test_create_developer_key_without_label(mocked):
    mocked.post(
        url("v2/admin/developer-keys"),
        match=json_request({}),
        json=DEVELOPER_KEY_JSON,
    )

    make_admin_client().create_developer_key()


@pytest.mark.parametrize(
    "failure",
    [
        {"status": 500},
        {"status": 503},
        {"body": requests.exceptions.ConnectionError("reset")},
        {"body": requests.exceptions.ReadTimeout("slow")},
    ],
)
def test_create_developer_key_is_not_retried_after_possible_processing(
    mocked, failure
):
    mocked.post(url("v2/admin/developer-keys"), **failure)

    with pytest.raises(deepl.DeepLException):
        make_admin_client().create_developer_key()

    assert len(mocked.calls) == 1


def _dns_failure():
    gaierror = socket.gaierror(8, "not known")
    if hasattr(urllib3.exceptions, "NameResolutionError"):
        reason = urllib3.exceptions.NameResolutionError(
            "api.deepl.com", None, gaierror
        )
    else:
        reason = urllib3.exceptions.NewConnectionError(None, "not known")
    reason.__context__ = gaierror
    return requests.exceptions.ConnectionError(
        urllib3.exceptions.MaxRetryError(None, "/", reason)
    )


@pytest.mark.parametrize(
    "failure", [{"status": 429}, {"body": _dns_failure()}]
)
def test_create_developer_key_is_retried_when_not_processed(mocked, failure):
    mocked.post(url("v2/admin/developer-keys"), **failure)
    mocked.post(url("v2/admin/developer-keys"), json=DEVELOPER_KEY_JSON)

    make_admin_client().create_developer_key()

    assert len(mocked.calls) == 2


def test_other_admin_requests_are_retried(mocked):
    mocked.get(url("v2/admin/developer-keys"), status=503)
    mocked.get(url("v2/admin/developer-keys"), json=[])

    make_admin_client().list_developer_keys()

    assert len(mocked.calls) == 2


def test_list_developer_keys(mocked):
    deactivated = dict(
        DEVELOPER_KEY_JSON,
        is_deactivated=True,
        deactivated_time="2025-07-09T08:15:29.362Z",
    )
    mocked.get(
        url("v2/admin/developer-keys"),
        match=bodyless_request(),
        json=[DEVELOPER_KEY_JSON, deactivated],
    )

    keys = make_admin_client().list_developer_keys()

    assert [k.is_deactivated for k in keys] == [False, True]
    assert keys[1].deactivated_time is not None


def test_deactivate_developer_key(mocked):
    mocked.put(
        url("v2/admin/developer-keys/deactivate"),
        match=json_request({"key_id": KEY_ID}),
        json=DEVELOPER_KEY_JSON,
    )

    make_admin_client().deactivate_developer_key(
        deepl.DeveloperKey.from_json(DEVELOPER_KEY_JSON)
    )


def test_rename_developer_key(mocked):
    mocked.put(
        url("v2/admin/developer-keys/label"),
        match=json_request({"key_id": KEY_ID, "label": "renamed"}),
        json=DEVELOPER_KEY_JSON,
    )

    make_admin_client().rename_developer_key(KEY_ID, "renamed")


@pytest.mark.parametrize(
    "limits",
    [
        {"characters": 0},
        {"speech_to_text_milliseconds": None},
        {"speech_to_speech_milliseconds": 60000},
        {
            "characters": None,
            "speech_to_text_milliseconds": 0,
            "speech_to_speech_milliseconds": 1,
        },
    ],
)
def test_set_developer_key_usage_limits_sends_only_given_limits(
    mocked, limits
):
    mocked.put(
        url("v2/admin/developer-keys/limits"),
        match=json_request({"key_id": KEY_ID, **limits}),
        json=DEVELOPER_KEY_JSON,
    )

    make_admin_client().set_developer_key_usage_limits(
        KEY_ID, deepl.DeveloperKeyUsageLimitsUpdate(**limits)
    )


@pytest.mark.parametrize(
    "call, message",
    [
        (lambda c: c.deactivate_developer_key(""), "key_id"),
        (lambda c: c.rename_developer_key("", "renamed"), "key_id"),
        (
            lambda c: c.set_developer_key_usage_limits(
                "", deepl.DeveloperKeyUsageLimitsUpdate(characters=1)
            ),
            "key_id",
        ),
    ],
)
def test_rejects_empty_arguments(call, message):
    with pytest.raises(ValueError, match=message):
        call(make_admin_client())


def test_forbidden_raises_authorization_exception(mocked):
    mocked.get(url("v2/admin/developer-keys"), status=403)

    with pytest.raises(deepl.AuthorizationException):
        make_admin_client().list_developer_keys()


def test_admin_client_applies_retry_and_timeout_options(mocked, no_retries):
    mocked.get(url("v2/admin/developer-keys"), status=503)
    mocked.get(url("v2/admin/developer-keys"), json=[])

    make_admin_client(max_retries=1, timeout_s=42.0).list_developer_keys()

    assert len(mocked.calls) == 2
    assert mocked.calls[1].request.req_kwargs["timeout"] == 42.0


@pytest.mark.parametrize(
    "method, path, call, body",
    [
        (
            "POST",
            "v2/admin/developer-keys",
            lambda c, extra: c.create_developer_key(
                label="a", extra_body_parameters=extra
            ),
            {"label": "replaced", "flag": True},
        ),
        (
            "PUT",
            "v2/admin/developer-keys/deactivate",
            lambda c, extra: c.deactivate_developer_key(
                KEY_ID, extra_body_parameters=extra
            ),
            {"key_id": KEY_ID, "label": "replaced", "flag": True},
        ),
        (
            "PUT",
            "v2/admin/developer-keys/label",
            lambda c, extra: c.rename_developer_key(
                KEY_ID, "a", extra_body_parameters=extra
            ),
            {"key_id": KEY_ID, "label": "replaced", "flag": True},
        ),
        (
            "PUT",
            "v2/admin/developer-keys/limits",
            lambda c, extra: c.set_developer_key_usage_limits(
                KEY_ID,
                deepl.DeveloperKeyUsageLimitsUpdate(characters=1),
                extra_body_parameters=extra,
            ),
            {
                "key_id": KEY_ID,
                "characters": 1,
                "label": "replaced",
                "flag": True,
            },
        ),
    ],
)
def test_developer_key_methods_send_extra_body_parameters(
    mocked, method, path, call, body
):
    mocked.add(
        method, url(path), match=json_request(body), json=DEVELOPER_KEY_JSON
    )

    call(make_admin_client(), {"label": "replaced", "flag": True})
