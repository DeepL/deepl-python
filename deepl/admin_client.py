# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.exceptions import DeepLException
from deepl.api_data import (
    AdminUsageGroupBy,
    AppInfo,
    AdminUsageReport,
    CustomTagUsageAggregateBy,
    CustomTagUsageReport,
    DeveloperKey,
    DeveloperKeyUsageLimitsUpdate,
)
from deepl._base_client import BaseClient
import datetime
import re
import urllib.parse
from typing import Dict, List, Optional, Union


_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class DeepLAdminClient(BaseClient):
    """Client for the DeepL Admin API, used to manage developer keys and
    retrieve usage analytics for your organization.

    :param admin_key: Admin API key as found in your DeepL account. Developer
        keys cannot access the Admin API.
    :param server_url: (Optional) Base URL of DeepL API, can be overridden e.g.
        for testing purposes.
    :param proxy: (Optional) Proxy server URL string or dictionary containing
        URL strings for the 'http' and 'https' keys. This is passed to the
        underlying requests session, see the requests proxy documentation for
        more information.
    :param send_platform_info: (Optional) boolean that indicates if the client
        library can send basic platform info (python version, OS) to the
        DeepL API. True = send info, False = only send client
        library version
    :param verify_ssl: (Optional) Controls how requests verifies SSL
        certificates. This is passed to the underlying requests session, see
        the requests verify documentation for more information.
    :param max_retries: (Optional) Maximum number of times a failed request
        is retried, for failures that may be transient (e.g. HTTP 429). If
        None, the deprecated deepl.http_client.max_network_retries is used
        (default 5).
    :param timeout_s: (Optional) Minimum timeout in seconds for each attempt
        of a request. If None, the deprecated
        deepl.http_client.min_connection_timeout is used (default 10.0).
    :param headers: (Optional) Additional HTTP headers sent with every
        request to the DeepL API. A User-Agent header replaces the one the
        library generates. An Authorization header is ignored.
    :param app_info: (Optional) AppInfo identifying your application in the
        User-Agent header, same as set_app_info().

    All functions may raise DeepLException or a subclass if a connection error
    occurs.
    """

    def __init__(
        self,
        admin_key: str,
        *,
        server_url: Optional[str] = None,
        proxy: Union[Dict, str, None] = None,
        send_platform_info: bool = True,
        verify_ssl: Union[bool, str, None] = None,
        max_retries: Optional[int] = None,
        timeout_s: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        app_info: Optional[AppInfo] = None,
    ):
        if not admin_key or not admin_key.strip():
            raise ValueError("admin_key must not be empty")

        super().__init__(
            admin_key,
            server_url=(
                self._DEEPL_SERVER_URL if server_url is None else server_url
            ),
            proxy=proxy,
            send_platform_info=send_platform_info,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            timeout_s=timeout_s,
            headers=headers,
            app_info=app_info,
        )

    def get_usage_analytics(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        *,
        group_by: Union[AdminUsageGroupBy, str, None] = None,
    ) -> AdminUsageReport:
        """Retrieves usage statistics for the organization within the given
        date range.

        :param start_date: Start date of the report, as a date or a
            "YYYY-MM-DD" string, e.g. "2025-09-29". Dates are UTC calendar
            days, and both the start and the end day are included. Of a
            datetime, the UTC date is used: 2026-10-20T00:00+02:00 is sent as
            2026-10-19. A naive datetime is treated as UTC.
        :param end_date: End date of the report, in the same format as
            start_date. The API requires it to be after start_date and at
            most 366 days after it.
        :param group_by: (Optional) Group the usage by key or by key and day,
            see AdminUsageGroupBy.
        :return: AdminUsageReport containing the usage statistics.
        :raises ValueError: If a date is not a date or a "YYYY-MM-DD" string.
        :raises DeepLException: If the API rejects the date range.
        """
        params = _date_range_params(start_date, end_date)
        if group_by is not None:
            params["group_by"] = str(group_by)

        status, content, json = self._api_call(
            f"v2/admin/analytics?{urllib.parse.urlencode(params)}",
            method="GET",
        )
        self._raise_for_status(status, content, json)
        _require_object(json, "Usage analytics")
        return AdminUsageReport.from_json(json)

    def get_custom_tag_usage_analytics(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        *,
        aggregate_by: Union[CustomTagUsageAggregateBy, str, None] = None,
        page: Optional[int] = None,
    ) -> CustomTagUsageReport:
        """Retrieves usage statistics per custom tag within the given date
        range. Results are paginated; pass the `next_page` value of a report
        as `page` to retrieve the following page.

        :param start_date: Start date of the report, as a date or a
            "YYYY-MM-DD" string, e.g. "2025-09-29". Dates are UTC calendar
            days, and both the start and the end day are included. Of a
            datetime, the UTC date is used: 2026-10-20T00:00+02:00 is sent as
            2026-10-19. A naive datetime is treated as UTC.
        :param end_date: End date of the report, in the same format as
            start_date. The API requires it to be after start_date and at
            most 366 days after it.
        :param aggregate_by: (Optional) Aggregate the usage over the whole
            period or by day, see CustomTagUsageAggregateBy.
        :param page: (Optional) Page number to retrieve.
        :return: CustomTagUsageReport containing the usage statistics.
        :raises ValueError: If a date is not a date or a "YYYY-MM-DD" string.
        :raises DeepLException: If the API rejects the date range.
        """
        params = _date_range_params(start_date, end_date)
        if aggregate_by is not None:
            params["aggregate_by"] = str(aggregate_by)
        if page is not None:
            params["page"] = str(page)

        status, content, json = self._api_call(
            f"v2/admin/analytics/custom-tags?{urllib.parse.urlencode(params)}",
            method="GET",
        )
        self._raise_for_status(status, content, json)
        _require_object(json, "Custom tag usage analytics")
        return CustomTagUsageReport.from_json(json)

    def create_developer_key(
        self,
        *,
        label: Optional[str] = None,
        extra_body_parameters: Optional[dict] = None,
    ) -> DeveloperKey:
        """Creates a developer key in the organization. The request is only
        retried if it cannot have been processed (HTTP 429 or a DNS
        resolution failure): a retry after a server error, timeout or lost
        connection could create a second key.

        :param label: (Optional) Label for the new key. The API uses
            "DeepL API Key" if no label is given.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace keys of the same name that the client sets.
        :return: DeveloperKey describing the created key.
        """
        request_data = {}
        if label is not None:
            request_data["label"] = label
        _add_extra_body_parameters(request_data, extra_body_parameters)

        status, content, json = self._api_call(
            "v2/admin/developer-keys",
            json=request_data,
            retry_only_unprocessed=True,
        )
        self._raise_for_status(status, content, json)
        return _parse_key(json)

    def list_developer_keys(self) -> List[DeveloperKey]:
        """Retrieves all developer keys in the organization, including
        deactivated ones.

        :return: List of DeveloperKey objects.
        """
        status, content, json = self._api_call(
            "v2/admin/developer-keys", method="GET"
        )
        self._raise_for_status(status, content, json)
        if not isinstance(json, list):
            raise DeepLException("Developer keys response is not a list")
        return [
            DeveloperKey.from_json(key)
            for key in json
            if isinstance(key, dict) and _has_key_id(key)
        ]

    def deactivate_developer_key(
        self,
        key: Union[str, DeveloperKey],
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> DeveloperKey:
        """Deactivates a developer key. Deactivation is permanent.

        :param key: Key ID or DeveloperKey to deactivate.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace keys of the same name that the client sets.
        :return: DeveloperKey describing the deactivated key.
        """
        return self._put_developer_key(
            "v2/admin/developer-keys/deactivate",
            {"key_id": _key_id(key)},
            extra_body_parameters,
        )

    def rename_developer_key(
        self,
        key: Union[str, DeveloperKey],
        label: str,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> DeveloperKey:
        """Changes the label of a developer key.

        :param key: Key ID or DeveloperKey to rename.
        :param label: New label for the key.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace keys of the same name that the client sets.
        :return: DeveloperKey describing the renamed key.
        """
        key_id = _key_id(key)
        return self._put_developer_key(
            "v2/admin/developer-keys/label",
            {"key_id": key_id, "label": label},
            extra_body_parameters,
        )

    def set_developer_key_usage_limits(
        self,
        key: Union[str, DeveloperKey],
        limits: DeveloperKeyUsageLimitsUpdate,
        *,
        extra_body_parameters: Optional[dict] = None,
    ) -> DeveloperKey:
        """Changes the monthly usage limits of a developer key. Only the
        limits set in `limits` are changed; the others keep their current
        value.

        :param key: Key ID or DeveloperKey to modify.
        :param limits: DeveloperKeyUsageLimitsUpdate with the limits to
            change. None removes a limit (unlimited usage) and 0 blocks that
            usage.
        :param extra_body_parameters: (Optional) Additional key/value pairs to
            include in the JSON request body sent to the API. They are added
            last and replace keys of the same name that the client sets.
        :return: DeveloperKey describing the modified key.
        """
        key_id = _key_id(key)
        return self._put_developer_key(
            "v2/admin/developer-keys/limits",
            {"key_id": key_id, **limits._to_request_dict()},
            extra_body_parameters,
        )

    def _put_developer_key(
        self,
        url: str,
        request_data: dict,
        extra_body_parameters: Optional[dict],
    ) -> DeveloperKey:
        _add_extra_body_parameters(request_data, extra_body_parameters)
        status, content, json = self._api_call(
            url, method="PUT", json=request_data
        )
        self._raise_for_status(status, content, json)
        return _parse_key(json)


def _add_extra_body_parameters(
    request_data: dict, extra_body_parameters: Optional[dict]
) -> None:
    # Entries replace keys of the same name set by the client.
    if extra_body_parameters:
        request_data.update(extra_body_parameters)


def _date_range_params(
    start_date: Union[datetime.date, str], end_date: Union[datetime.date, str]
) -> Dict[str, str]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}


def _parse_date(value: Union[datetime.date, str]) -> datetime.date:
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None and value.utcoffset() is not None:
            value = value.astimezone(datetime.timezone.utc)
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and _DATE_PATTERN.fullmatch(value):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(
        f"Invalid date {value!r}, expected a date or a YYYY-MM-DD string"
    )


def _has_key_id(json: dict) -> bool:
    key_id = json.get("key_id")
    return isinstance(key_id, str) and bool(key_id)


def _parse_key(json) -> DeveloperKey:
    if not isinstance(json, dict) or not _has_key_id(json):
        raise DeepLException("Developer key response is missing key_id")
    return DeveloperKey.from_json(json)


def _require_object(json, what: str):
    if not isinstance(json, dict):
        raise DeepLException(f"{what} response is not a JSON object")


def _key_id(key: Union[str, DeveloperKey]) -> str:
    key_id = key.key_id if isinstance(key, DeveloperKey) else key
    if not key_id:
        raise ValueError("key_id must not be empty")
    return key_id
