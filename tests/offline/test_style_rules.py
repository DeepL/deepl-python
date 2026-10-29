# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime

import pytest
from deepl.api_data import ConfiguredRules, CustomInstruction, StyleRuleInfo

from .client import make_deepl_client, url
from .matchers import bodyless_request, json_request

STYLE_RULE_JSON = {
    "style_id": "style-1",
    "name": "style",
    "creation_time": "2021-08-03T14:16:18.329Z",
    "updated_time": "2021-08-04T14:16:18.329Z",
    "language": "en",
    "version": 3,
}
INSTRUCTION_JSON = {
    "id": "instruction-1",
    "label": "Label",
    "prompt": "Prompt",
}
CONFIGURED_RULES = {"dates_and_times": {"calendar_era": "use_bc_and_ad"}}


def style_rule_info():
    return StyleRuleInfo.from_json(STYLE_RULE_JSON)


@pytest.mark.parametrize(
    "kwargs, query",
    [
        ({}, {}),
        ({"page": 2}, {"page": "2"}),
        ({"page_size": 10}, {"page_size": "10"}),
        ({"detailed": True}, {"detailed": "true"}),
        ({"detailed": False}, {"detailed": "false"}),
        (
            {"page": 1, "page_size": 5, "detailed": True},
            {"page": "1", "page_size": "5", "detailed": "true"},
        ),
    ],
)
def test_sends_query_when_listing_style_rules(mocked, kwargs, query):
    mocked.get(
        url("v3/style_rules"),
        json={"style_rules": [STYLE_RULE_JSON]},
        match=bodyless_request(query),
    )

    make_deepl_client().get_all_style_rules(**kwargs)


def test_parses_style_rule_list_with_details(mocked):
    mocked.get(
        url("v3/style_rules"),
        json={
            "style_rules": [
                {
                    **STYLE_RULE_JSON,
                    "configured_rules": {
                        "numbers": {"number_format": "x"},
                        "vocabulary": {"a": "b"},
                    },
                    "custom_instructions": [
                        {**INSTRUCTION_JSON, "source_language": "de"}
                    ],
                },
                {**STYLE_RULE_JSON, "style_id": "style-2"},
            ]
        },
    )

    style_rules = make_deepl_client().get_all_style_rules(detailed=True)

    first, second = style_rules
    assert isinstance(first.configured_rules, ConfiguredRules)
    assert first.configured_rules.formatting == {}
    assert isinstance(first.custom_instructions[0], CustomInstruction)
    assert second.configured_rules is None
    assert second.custom_instructions == []


def test_parses_style_rule(mocked):
    mocked.get(url("v3/style_rules/style-1"), json=STYLE_RULE_JSON)

    style_rule = make_deepl_client().get_style_rule("style-1")

    assert style_rule.creation_time == datetime.datetime(
        2021, 8, 3, 14, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert style_rule.updated_time == datetime.datetime(
        2021, 8, 4, 14, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert str(style_rule) == 'StyleRule "style" (style-1)'


@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_get_when_getting_style_rule(mocked, style_rule):
    mocked.get(
        url("v3/style_rules/style-1"),
        json=STYLE_RULE_JSON,
        match=bodyless_request(),
    )

    make_deepl_client().get_style_rule(style_rule)


def test_sends_name_and_language_when_creating_style_rule(mocked):
    mocked.post(
        url("v3/style_rules"),
        json=STYLE_RULE_JSON,
        match=json_request({"name": "style", "language": "en"}),
    )

    make_deepl_client().create_style_rule("style", "en")


def test_sends_rules_and_instructions_when_creating_style_rule(mocked):
    instructions = [{"label": "L", "prompt": "P", "source_language": "de"}]
    mocked.post(
        url("v3/style_rules"),
        json=STYLE_RULE_JSON,
        match=json_request(
            {
                "name": "style",
                "language": "en",
                "configured_rules": CONFIGURED_RULES,
                "custom_instructions": instructions,
            }
        ),
    )

    make_deepl_client().create_style_rule(
        "style",
        "en",
        configured_rules=CONFIGURED_RULES,
        custom_instructions=instructions,
    )


@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_new_name_when_renaming_style_rule(mocked, style_rule):
    mocked.patch(
        url("v3/style_rules/style-1"),
        json=STYLE_RULE_JSON,
        match=json_request({"name": "new"}),
    )

    make_deepl_client().update_style_rule_name(style_rule, "new")


@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_rules_as_body_when_updating_configured_rules(
    mocked, style_rule
):
    mocked.put(
        url("v3/style_rules/style-1/configured_rules"),
        json=STYLE_RULE_JSON,
        match=json_request(CONFIGURED_RULES),
    )

    make_deepl_client().update_style_rule_configured_rules(
        style_rule, CONFIGURED_RULES
    )


@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_delete_when_deleting_style_rule(mocked, style_rule):
    mocked.delete(
        url("v3/style_rules/style-1"), status=204, match=bodyless_request()
    )

    assert make_deepl_client().delete_style_rule(style_rule) is None


@pytest.mark.parametrize(
    "kwargs, body",
    [
        ({}, {"label": "L", "prompt": "P"}),
        (
            {"source_language": "de"},
            {"label": "L", "prompt": "P", "source_language": "de"},
        ),
    ],
)
@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_label_and_prompt_when_creating_instruction(
    mocked, style_rule, kwargs, body
):
    mocked.post(
        url("v3/style_rules/style-1/custom_instructions"),
        json=INSTRUCTION_JSON,
        match=json_request(body),
    )

    make_deepl_client().create_style_rule_custom_instruction(
        style_rule, "L", "P", **kwargs
    )


def test_sends_get_when_getting_instruction(mocked):
    mocked.get(
        url("v3/style_rules/style-1/custom_instructions/instruction-1"),
        json={**INSTRUCTION_JSON, "source_language": "de"},
        match=bodyless_request(),
    )

    instruction = make_deepl_client().get_style_rule_custom_instruction(
        style_rule_info(), "instruction-1"
    )

    assert isinstance(instruction, CustomInstruction)


@pytest.mark.parametrize(
    "kwargs, body",
    [
        ({}, {"label": "L", "prompt": "P"}),
        (
            {"source_language": "de"},
            {"label": "L", "prompt": "P", "source_language": "de"},
        ),
    ],
)
def test_sends_put_when_updating_instruction(mocked, kwargs, body):
    mocked.put(
        url("v3/style_rules/style-1/custom_instructions/instruction-1"),
        json=INSTRUCTION_JSON,
        match=json_request(body),
    )

    make_deepl_client().update_style_rule_custom_instruction(
        style_rule_info(), "instruction-1", "L", "P", **kwargs
    )


@pytest.mark.parametrize("style_rule", ["style-1", style_rule_info()])
def test_sends_delete_when_deleting_instruction(mocked, style_rule):
    mocked.delete(
        url("v3/style_rules/style-1/custom_instructions/instruction-1"),
        status=204,
        match=bodyless_request(),
    )

    make_deepl_client().delete_style_rule_custom_instruction(
        style_rule, "instruction-1"
    )


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda c: c.create_style_rule("", "en"), "name must not be empty"),
        (
            lambda c: c.create_style_rule("n", ""),
            "language must not be empty",
        ),
        (lambda c: c.get_style_rule(""), "style_rule must not be empty"),
        (
            lambda c: c.update_style_rule_name("", "n"),
            "style_rule must not be empty",
        ),
        (
            lambda c: c.update_style_rule_name("s", ""),
            "name must not be empty",
        ),
        (lambda c: c.delete_style_rule(""), "style_rule must not be empty"),
        (
            lambda c: c.update_style_rule_configured_rules("", {}),
            "style_rule must not be empty",
        ),
        (
            lambda c: c.create_style_rule_custom_instruction("", "L", "P"),
            "style_rule must not be empty",
        ),
        (
            lambda c: c.create_style_rule_custom_instruction("s", "", "P"),
            "label must not be empty",
        ),
        (
            lambda c: c.create_style_rule_custom_instruction("s", "L", ""),
            "prompt must not be empty",
        ),
        (
            lambda c: c.get_style_rule_custom_instruction("", "i"),
            "style_rule must not be empty",
        ),
        (
            lambda c: c.get_style_rule_custom_instruction("s", ""),
            "instruction_id must not be empty",
        ),
        (
            lambda c: c.update_style_rule_custom_instruction(
                "", "i", "L", "P"
            ),
            "style_rule must not be empty",
        ),
        (
            lambda c: c.update_style_rule_custom_instruction(
                "s", "", "L", "P"
            ),
            "instruction_id must not be empty",
        ),
        (
            lambda c: c.update_style_rule_custom_instruction(
                "s", "i", "", "P"
            ),
            "label must not be empty",
        ),
        (
            lambda c: c.update_style_rule_custom_instruction(
                "s", "i", "L", ""
            ),
            "prompt must not be empty",
        ),
        (
            lambda c: c.delete_style_rule_custom_instruction("", "i"),
            "style_rule must not be empty",
        ),
        (
            lambda c: c.delete_style_rule_custom_instruction("s", ""),
            "instruction_id must not be empty",
        ),
    ],
)
def test_raises_for_empty_arguments(call, match):
    with pytest.raises(ValueError, match=match):
        call(make_deepl_client())


ESCAPED = "v3/style_rules/a%2Fb%3Fc%20d"


@pytest.mark.parametrize(
    "method, path, call",
    [
        ("GET", ESCAPED, lambda c: c.get_style_rule("a/b?c d")),
        ("PATCH", ESCAPED, lambda c: c.update_style_rule_name("a/b?c d", "n")),
        ("DELETE", ESCAPED, lambda c: c.delete_style_rule("a/b?c d")),
        (
            "PUT",
            f"{ESCAPED}/configured_rules",
            lambda c: c.update_style_rule_configured_rules("a/b?c d", {}),
        ),
        (
            "POST",
            f"{ESCAPED}/custom_instructions",
            lambda c: c.create_style_rule_custom_instruction(
                "a/b?c d", "L", "P"
            ),
        ),
        (
            "GET",
            f"{ESCAPED}/custom_instructions/i%2Fj",
            lambda c: c.get_style_rule_custom_instruction("a/b?c d", "i/j"),
        ),
        (
            "PUT",
            f"{ESCAPED}/custom_instructions/i%2Fj",
            lambda c: c.update_style_rule_custom_instruction(
                "a/b?c d", "i/j", "L", "P"
            ),
        ),
        (
            "DELETE",
            f"{ESCAPED}/custom_instructions/i%2Fj",
            lambda c: c.delete_style_rule_custom_instruction("a/b?c d", "i/j"),
        ),
    ],
)
def test_escapes_ids_in_the_path(mocked, method, path, call):
    body = INSTRUCTION_JSON if "custom_instructions" in path else None
    mocked.add(method, url(path), json=body or STYLE_RULE_JSON)

    call(make_deepl_client())
