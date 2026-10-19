# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .client import make_deepl_client
from .helpers import get_unique_name


def test_sends_style_rule_requests_from_create_to_delete():
    client = make_deepl_client()
    name = get_unique_name("style-rule")
    renamed = get_unique_name("style-rule-renamed")

    created = client.create_style_rule(name, "en")
    style_id = created.style_id
    try:
        assert style_id
        assert created.name == name
        assert created.language == "en"

        assert client.get_style_rule(style_id).style_id == style_id

        assert _is_listed(client, style_id)

        assert client.update_style_rule_name(created, renamed).name == renamed

        updated = client.update_style_rule_configured_rules(
            created, {"dates_and_times": {"calendar_era": "use_bc_and_ad"}}
        )
        assert updated.style_id == style_id

        instruction = client.create_style_rule_custom_instruction(
            created, "Formal", "Always use formal language"
        )
        assert instruction.id
        assert instruction.label == "Formal"

        fetched = client.get_style_rule_custom_instruction(
            created, instruction.id
        )
        assert fetched.id == instruction.id

        changed = client.update_style_rule_custom_instruction(
            created, instruction.id, "Casual", "Use casual language"
        )
        assert changed.label == "Casual"

        client.delete_style_rule_custom_instruction(created, instruction.id)
    finally:
        client.delete_style_rule(style_id)


def _is_listed(client, style_id):
    for page in range(20):
        rules = client.get_all_style_rules(page=page, page_size=25)
        if style_id in [rule.style_id for rule in rules]:
            return True
        if not rules:
            return False
    return False
