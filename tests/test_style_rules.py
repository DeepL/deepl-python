# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import pytest

from .conftest import example_text, needs_mock_server

DEFAULT_STYLE_ID = "dca2e053-8ae5-45e6-a0d2-881156e7f4e4"


@needs_mock_server
def test_get_all_style_rules(deepl_client):
    style_rules = deepl_client.get_all_style_rules(detailed=True)

    assert isinstance(style_rules, list)
    assert len(style_rules) == 1
    assert style_rules[0].style_id == DEFAULT_STYLE_ID
    assert style_rules[0].name == "Default Style Rule"
    assert style_rules[0].creation_time is not None
    assert style_rules[0].updated_time is not None
    assert style_rules[0].language == "en"
    assert style_rules[0].version == 1
    assert style_rules[0].configured_rules is not None
    assert style_rules[0].custom_instructions is not None


def test_style_rule_crud(deepl_client):
    # Create a style rule
    style_rule = deepl_client.create_style_rule(
        name="Test Style Rule",
        language="en",
    )
    assert style_rule.style_id is not None
    assert style_rule.name == "Test Style Rule"
    assert style_rule.language == "en"

    style_id = style_rule.style_id

    # Get the style rule by ID
    retrieved = deepl_client.get_style_rule(style_id)
    assert retrieved.style_id == style_id
    assert retrieved.name == "Test Style Rule"

    # Update the name
    updated = deepl_client.update_style_rule_name(style_id, "Updated Name")
    assert updated.name == "Updated Name"

    # Update configured rules
    configured = deepl_client.update_style_rule_configured_rules(
        style_id,
        {"dates_and_times": {"calendar_era": "use_bc_and_ad"}},
    )
    assert configured.style_id == style_id

    # Create a custom instruction
    instruction = deepl_client.create_style_rule_custom_instruction(
        style_id,
        label="Test Instruction",
        prompt="Always use formal language",
    )
    assert instruction.label == "Test Instruction"
    assert instruction.prompt == "Always use formal language"
    assert instruction.id is not None

    instruction_id = instruction.id

    # Get the custom instruction
    retrieved_instruction = deepl_client.get_style_rule_custom_instruction(
        style_id, instruction_id
    )
    assert retrieved_instruction.label == "Test Instruction"

    # Update the custom instruction
    updated_instruction = deepl_client.update_style_rule_custom_instruction(
        style_id,
        instruction_id,
        label="Updated Instruction",
        prompt="Use very formal language",
    )
    assert updated_instruction.label == "Updated Instruction"

    # Delete the custom instruction
    deepl_client.delete_style_rule_custom_instruction(style_id, instruction_id)

    # Delete the style rule
    deepl_client.delete_style_rule(style_id)


def test_style_rule_accepts_style_rule_info(deepl_client):
    """Methods accepting Union[str, StyleRuleInfo] should work with objects."""
    style_rule = deepl_client.create_style_rule(
        name="Object Test", language="en"
    )

    # get_style_rule with StyleRuleInfo object
    retrieved = deepl_client.get_style_rule(style_rule)
    assert retrieved.style_id == style_rule.style_id

    # update_style_rule_name with StyleRuleInfo object
    updated = deepl_client.update_style_rule_name(style_rule, "New Name")
    assert updated.name == "New Name"

    # update_style_rule_configured_rules with StyleRuleInfo object
    configured = deepl_client.update_style_rule_configured_rules(
        style_rule, {"dates_and_times": {"calendar_era": "use_bc_and_ad"}}
    )
    assert configured.style_id == style_rule.style_id

    # create/get/update/delete custom instruction with StyleRuleInfo object
    instruction = deepl_client.create_style_rule_custom_instruction(
        style_rule, label="Test", prompt="Be formal"
    )
    assert instruction.id is not None

    deepl_client.get_style_rule_custom_instruction(style_rule, instruction.id)
    deepl_client.update_style_rule_custom_instruction(
        style_rule, instruction.id, label="Updated", prompt="Be casual"
    )
    deepl_client.delete_style_rule_custom_instruction(
        style_rule, instruction.id
    )

    # delete_style_rule with StyleRuleInfo object
    deepl_client.delete_style_rule(style_rule)


def test_style_rule_validation(deepl_client):
    # create_style_rule
    with pytest.raises(ValueError, match="name must not be empty"):
        deepl_client.create_style_rule(name="", language="en")
    with pytest.raises(ValueError, match="language must not be empty"):
        deepl_client.create_style_rule(name="Test", language="")

    # get_style_rule
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.get_style_rule("")

    # update_style_rule_name
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.update_style_rule_name("", "New Name")
    with pytest.raises(ValueError, match="name must not be empty"):
        deepl_client.update_style_rule_name("some-id", "")

    # delete_style_rule
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.delete_style_rule("")

    # update_style_rule_configured_rules
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.update_style_rule_configured_rules("", {})

    # create_style_rule_custom_instruction
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.create_style_rule_custom_instruction(
            "", label="L", prompt="P"
        )
    with pytest.raises(ValueError, match="label must not be empty"):
        deepl_client.create_style_rule_custom_instruction(
            "some-id", label="", prompt="P"
        )
    with pytest.raises(ValueError, match="prompt must not be empty"):
        deepl_client.create_style_rule_custom_instruction(
            "some-id", label="L", prompt=""
        )

    # get_style_rule_custom_instruction
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.get_style_rule_custom_instruction("", "instr-id")
    with pytest.raises(ValueError, match="instruction_id must not be empty"):
        deepl_client.get_style_rule_custom_instruction("some-id", "")

    # update_style_rule_custom_instruction
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.update_style_rule_custom_instruction(
            "", "instr-id", label="L", prompt="P"
        )
    with pytest.raises(ValueError, match="instruction_id must not be empty"):
        deepl_client.update_style_rule_custom_instruction(
            "some-id", "", label="L", prompt="P"
        )
    with pytest.raises(ValueError, match="label must not be empty"):
        deepl_client.update_style_rule_custom_instruction(
            "some-id", "instr-id", label="", prompt="P"
        )
    with pytest.raises(ValueError, match="prompt must not be empty"):
        deepl_client.update_style_rule_custom_instruction(
            "some-id", "instr-id", label="L", prompt=""
        )

    # delete_style_rule_custom_instruction
    with pytest.raises(ValueError, match="style_rule must not be empty"):
        deepl_client.delete_style_rule_custom_instruction("", "instr-id")
    with pytest.raises(ValueError, match="instruction_id must not be empty"):
        deepl_client.delete_style_rule_custom_instruction("some-id", "")


@needs_mock_server
def test_translate_text_with_style_rule(deepl_client):
    # Note: this test may use the mock server that will not translate the text,
    # therefore we do not check the translated result.
    _ = deepl_client.translate_text(
        example_text["DE"], target_lang="EN-US", style_rule=DEFAULT_STYLE_ID
    )


@needs_mock_server
def test_translate_document_with_style_rule(
    deepl_client,
    example_document_path,
    output_document_path,
):
    # Note: this test may use the mock server that will not translate the text,
    # therefore we do not check the translated result.
    example_document_path.write_text(example_text["DE"])
    deepl_client.translate_document_from_filepath(
        example_document_path,
        output_path=output_document_path,
        source_lang="DE",
        target_lang="EN-US",
        style_rule=DEFAULT_STYLE_ID,
    )
