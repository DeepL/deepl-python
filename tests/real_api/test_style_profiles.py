# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import time

import deepl
import pytest

from .client import make_deepl_client
from .helpers import get_unique_name


def get_style_profile_when_visible(client, style_profile_id):
    """A style profile that was just created can be briefly invisible."""
    for _ in range(9):
        try:
            return client.get_style_profile(style_profile_id)
        except deepl.DeepLException as e:
            if e.http_status_code != 404:
                raise
            time.sleep(1)
    return client.get_style_profile(style_profile_id)


def delete_ignoring_not_found(delete, resource_id):
    try:
        delete(resource_id)
    except deepl.DeepLException as e:
        if e.http_status_code != 404:
            raise


def is_listed(client, style_profile_id):
    for page in range(20):
        profiles = client.list_style_profiles(page=page, page_size=100)
        if style_profile_id in [p.style_profile_id for p in profiles]:
            return True
        if not profiles:
            return False
    return False


def test_sends_style_profile_requests_from_create_to_delete():
    client = make_deepl_client()
    rule_id = client.create_style_rule(
        get_unique_name("styleProfileRule"), "de"
    ).style_id
    profile_id = None
    try:
        name = get_unique_name("styleProfile")
        created = client.create_style_profile(
            name, description="SDK test profile", style_rule_ids=[rule_id]
        )
        profile_id = created.style_profile_id
        assert created.name == name
        assert created.description == "SDK test profile"
        assert created.style_rule_ids == [rule_id]
        assert created.glossary_ids == []
        assert created.translation_memory_ids == []

        fetched = get_style_profile_when_visible(client, profile_id)
        assert fetched.name == name
        assert fetched.description == "SDK test profile"
        assert fetched.style_rule_ids == [rule_id]

        assert is_listed(client, profile_id)

        renamed = get_unique_name("styleProfile-renamed")
        updated = client.update_style_profile(
            created,
            name=renamed,
            industry="Legal",
            description="",
            style_rule_ids=[],
        )
        assert updated.name == renamed
        assert updated.industry == "Legal"
        assert updated.description is None
        assert updated.style_rule_ids == []

        client.delete_style_profile(profile_id)
        with pytest.raises(deepl.DeepLException) as error:
            client.get_style_profile(profile_id)
        assert error.value.http_status_code == 404
    finally:
        if profile_id:
            delete_ignoring_not_found(client.delete_style_profile, profile_id)
        delete_ignoring_not_found(client.delete_style_rule, rule_id)
