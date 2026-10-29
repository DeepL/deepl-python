# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime

import deepl
import pytest
from deepl.api_data import (
    MultilingualGlossaryInfo,
    StyleRuleInfo,
    TranslationMemoryInfo,
)

from .client import make_deepl_client, url
from .matchers import bodyless_request, json_request

PROFILE_ID = "5f1c2b7e-3a4d-4c8b-9e6f-0d2a7b3c9e14"

# The example of the StyleProfile schema in the OpenAPI spec.
STYLE_PROFILE_JSON = {
    "style_profile_id": PROFILE_ID,
    "name": "Legal, German",
    "description": "Contract wording for the German market.",
    "industry": "Legal",
    "glossary_ids": ["4d0a2e1c-6b93-4f7a-8d15-2c6e9a3b7f81"],
    "style_rule_ids": ["bd0a38f3-1831-440b-a8dd-2c702e2325ab"],
    "translation_memory_ids": ["a74d88fb-ed2a-4943-a664-a4512398b994"],
    "glossary_priority_order_enabled": True,
    "creation_time": "2026-04-01T16:34:25.223Z",
    "updated_time": "2026-08-06T09:12:44.108Z",
}

MINIMAL_PROFILE_JSON = {
    "style_profile_id": PROFILE_ID,
    "name": "minimal",
    "glossary_ids": [],
    "style_rule_ids": [],
    "translation_memory_ids": [],
    "glossary_priority_order_enabled": False,
    "creation_time": "2026-10-26T16:27:10.2982869Z",
    "updated_time": "2026-10-26T16:27:10.2982869Z",
    "example_document_ids": ["x"],
    "spoken_terms_ids": ["y"],
}

PROFILE = deepl.StyleProfile.from_json(STYLE_PROFILE_JSON)


def utc(*args):
    return datetime.datetime(*args, tzinfo=datetime.timezone.utc)


@pytest.mark.parametrize(
    "kwargs, query",
    [
        ({}, {}),
        ({"page": 2, "page_size": 100}, {"page": "2", "page_size": "100"}),
    ],
)
def test_sends_page_and_page_size_only_when_set(mocked, kwargs, query):
    mocked.get(
        url("v3/style_profiles"),
        json={"style_profiles": [STYLE_PROFILE_JSON], "total_count": 1},
        match=bodyless_request(query),
    )

    profiles = make_deepl_client().list_style_profiles(**kwargs)

    assert [p.style_profile_id for p in profiles] == [PROFILE_ID]


def test_returns_empty_list_when_style_profiles_are_missing(mocked):
    mocked.get(url("v3/style_profiles"), json={"total_count": 0})

    assert make_deepl_client().list_style_profiles() == []


def test_creates_with_only_a_name(mocked):
    mocked.post(
        url("v3/style_profiles"),
        json=MINIMAL_PROFILE_JSON,
        status=201,
        match=json_request({"name": "minimal"}),
    )

    created = make_deepl_client().create_style_profile("minimal")

    assert created.name == "minimal"


def test_creates_with_every_option(mocked):
    mocked.post(
        url("v3/style_profiles"),
        json=STYLE_PROFILE_JSON,
        status=201,
        match=json_request(
            {
                "name": "Legal, German",
                "description": "Contract wording.",
                "industry": "Legal",
                "glossary_ids": ["g2", "g1"],
                "style_rule_ids": ["s1"],
                "translation_memory_ids": ["t2", "t1"],
                "glossary_priority_order_enabled": True,
            }
        ),
    )

    make_deepl_client().create_style_profile(
        "Legal, German",
        description="Contract wording.",
        industry="Legal",
        glossary_ids=["g2", "g1"],
        style_rule_ids=["s1"],
        translation_memory_ids=["t2", "t1"],
        glossary_priority_order_enabled=True,
    )


@pytest.mark.parametrize("style_profile", [PROFILE_ID, PROFILE])
def test_gets_by_id_or_object(mocked, style_profile):
    mocked.get(
        url(f"v3/style_profiles/{PROFILE_ID}"),
        json=STYLE_PROFILE_JSON,
        match=bodyless_request(),
    )

    fetched = make_deepl_client().get_style_profile(style_profile)

    assert fetched.style_profile_id == PROFILE_ID


def test_escapes_the_id_in_the_path(mocked):
    mocked.get(
        url("v3/style_profiles/a%2Fb%3Fc%20d"),
        json=STYLE_PROFILE_JSON,
        match=bodyless_request(),
    )

    make_deepl_client().get_style_profile("a/b?c d")


@pytest.mark.parametrize(
    "kwargs, body",
    [
        ({}, {}),
        (
            {"name": "new", "description": "", "style_rule_ids": []},
            {"name": "new", "description": "", "style_rule_ids": []},
        ),
        (
            {"glossary_priority_order_enabled": False, "industry": "Legal"},
            {"glossary_priority_order_enabled": False, "industry": "Legal"},
        ),
    ],
)
@pytest.mark.parametrize("style_profile", [PROFILE_ID, PROFILE])
def test_updates_only_the_set_fields(mocked, style_profile, kwargs, body):
    mocked.patch(
        url(f"v3/style_profiles/{PROFILE_ID}"),
        json=STYLE_PROFILE_JSON,
        match=json_request(body),
    )

    make_deepl_client().update_style_profile(style_profile, **kwargs)


@pytest.mark.parametrize("style_profile", [PROFILE_ID, PROFILE])
def test_deletes_by_id_or_object(mocked, style_profile):
    mocked.delete(
        url(f"v3/style_profiles/{PROFILE_ID}"),
        status=204,
        match=bodyless_request(),
    )

    assert make_deepl_client().delete_style_profile(style_profile) is None


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.get_style_profile(""),
        lambda c: c.update_style_profile("", name="x"),
        lambda c: c.delete_style_profile(""),
    ],
)
def test_rejects_an_empty_id_without_a_request(call):
    # The autouse `mocked` fixture fails any request that is sent.
    with pytest.raises(ValueError):
        call(make_deepl_client())


def test_parses_every_field_of_the_spec_example():
    assert PROFILE.style_profile_id == PROFILE_ID
    assert PROFILE.name == "Legal, German"
    assert PROFILE.description == "Contract wording for the German market."
    assert PROFILE.industry == "Legal"
    assert PROFILE.glossary_ids == ["4d0a2e1c-6b93-4f7a-8d15-2c6e9a3b7f81"]
    assert PROFILE.style_rule_ids == ["bd0a38f3-1831-440b-a8dd-2c702e2325ab"]
    assert PROFILE.translation_memory_ids == [
        "a74d88fb-ed2a-4943-a664-a4512398b994"
    ]
    assert PROFILE.glossary_priority_order_enabled is True
    assert PROFILE.creation_time == utc(2026, 4, 1, 16, 34, 25, 223000)
    assert PROFILE.updated_time == utc(2026, 8, 6, 9, 12, 44, 108000)


def test_parses_a_profile_without_optional_fields():
    profile = deepl.StyleProfile.from_json(MINIMAL_PROFILE_JSON)

    assert profile.description is None
    assert profile.industry is None
    assert profile.creation_time == utc(2026, 10, 26, 16, 27, 10, 298286)
    assert not hasattr(profile, "example_document_ids")
    assert not hasattr(profile, "spoken_terms_ids")


@pytest.mark.parametrize("creation_time", ["not a timestamp", 123])
def test_tolerates_malformed_values(mocked, creation_time):
    malformed = dict(
        STYLE_PROFILE_JSON,
        creation_time=creation_time,
        glossary_ids=["g1", 7, None, "g2"],
        translation_memory_ids=None,
    )
    del malformed["glossary_priority_order_enabled"]
    mocked.get(url(f"v3/style_profiles/{PROFILE_ID}"), json=malformed)

    profile = make_deepl_client().get_style_profile(PROFILE_ID)

    assert profile.creation_time is None
    assert profile.glossary_ids == ["g1", "g2"]
    assert profile.translation_memory_ids == []
    assert profile.glossary_priority_order_enabled is False
    assert profile.name == "Legal, German"
    assert profile.updated_time == utc(2026, 8, 6, 9, 12, 44, 108000)


def test_maps_404_to_not_found(mocked):
    mocked.get(
        url(f"v3/style_profiles/{PROFILE_ID}"),
        json={"message": "Style profile not found"},
        status=404,
    )

    with pytest.raises(deepl.DeepLException) as error:
        make_deepl_client().get_style_profile(PROFILE_ID)

    assert error.value.http_status_code == 404
    assert "Style profile not found" in str(error.value)


GLOSSARY = deepl.GlossaryInfo("g1", "v2", True, "EN", "DE", utc(2026, 1, 1), 1)
MULTILINGUAL_GLOSSARY = MultilingualGlossaryInfo(
    "g2", "v3", utc(2026, 1, 1), []
)
STYLE_RULE = StyleRuleInfo(
    "s1", "rules", utc(2026, 1, 1), utc(2026, 1, 1), "de", 1
)
TRANSLATION_MEMORY = TranslationMemoryInfo("t1", "tm", "en", ["de"], 0)

RESOURCE_REFS = {
    "glossary_ids": [MULTILINGUAL_GLOSSARY, "g3", GLOSSARY],
    "style_rule_ids": [STYLE_RULE, "s2"],
    "translation_memory_ids": ["t2", TRANSLATION_MEMORY],
}
RESOURCE_IDS = {
    "glossary_ids": ["g2", "g3", "g1"],
    "style_rule_ids": ["s1", "s2"],
    "translation_memory_ids": ["t2", "t1"],
}


def test_creates_with_resource_objects_as_ids(mocked):
    mocked.post(
        url("v3/style_profiles"),
        json=STYLE_PROFILE_JSON,
        status=201,
        match=json_request(dict(RESOURCE_IDS, name="n")),
    )

    make_deepl_client().create_style_profile("n", **RESOURCE_REFS)


def test_updates_with_resource_objects_as_ids(mocked):
    mocked.patch(
        url(f"v3/style_profiles/{PROFILE_ID}"),
        json=STYLE_PROFILE_JSON,
        match=json_request(RESOURCE_IDS),
    )

    make_deepl_client().update_style_profile(PROFILE_ID, **RESOURCE_REFS)


def test_create_merges_extra_body_parameters_last(mocked):
    mocked.post(
        url("v3/style_profiles"),
        json=STYLE_PROFILE_JSON,
        status=201,
        match=json_request(
            {"name": "replaced", "industry": "Legal", "extra": {"a": [1]}}
        ),
    )

    make_deepl_client().create_style_profile(
        "n",
        industry="Legal",
        extra_body_parameters={"name": "replaced", "extra": {"a": [1]}},
    )


def test_update_merges_extra_body_parameters_last(mocked):
    mocked.patch(
        url(f"v3/style_profiles/{PROFILE_ID}"),
        json=STYLE_PROFILE_JSON,
        match=json_request({"glossary_ids": ["x"], "extra": True}),
    )

    make_deepl_client().update_style_profile(
        PROFILE_ID,
        glossary_ids=[GLOSSARY],
        extra_body_parameters={"glossary_ids": ["x"], "extra": True},
    )
