# Copyright 2026 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

# Re-export all builder/parser functions (private, underscore-prefixed).
# DeepLClient and DeepLClientAsync import from here.

from ._translate import (  # noqa
    _build_list_translation_memories_request,
    _build_translate_text_request,
    _parse_list_translation_memories_response,
    _parse_translate_text_response,
)
from ._document import (  # noqa
    _build_document_upload_request,
    _parse_document_upload_response,
    _build_document_status_request,
    _parse_document_status_response,
    _build_document_download_request,
)
from ._glossary import (  # noqa
    _build_create_glossary_request,
    _parse_create_glossary_response,
    _build_get_glossary_request,
    _parse_get_glossary_response,
    _build_list_glossaries_request,
    _parse_list_glossaries_response,
    _build_get_glossary_entries_request,
    _parse_get_glossary_entries_response,
    _build_delete_glossary_request,
    _build_create_multilingual_glossary_request,
    _parse_multilingual_glossary_response,
    _build_update_multilingual_glossary_name_request,
    _build_update_multilingual_glossary_dict_request,
    _build_replace_multilingual_glossary_dict_request,
    _parse_multilingual_glossary_dict_response,
    _build_get_multilingual_glossary_request,
    _build_list_multilingual_glossaries_request,
    _parse_list_multilingual_glossaries_response,
    _build_get_multilingual_glossary_entries_request,
    _parse_multilingual_glossary_entries_response,
    _build_delete_multilingual_glossary_request,
    _build_delete_multilingual_glossary_dict_request,
)
from ._usage import (  # noqa
    _build_get_usage_request,
    _parse_get_usage_response,
)
from ._languages import (  # noqa
    _build_get_source_languages_request,
    _build_get_target_languages_request,
    _parse_get_source_languages_response,
    _parse_get_target_languages_response,
    _build_get_glossary_languages_request,
    _parse_get_glossary_languages_response,
)
from ._write import (  # noqa
    _build_rephrase_text_request,
    _parse_rephrase_text_response,
)
from ._style_rules import (  # noqa
    _build_get_style_rules_request,
    _parse_get_style_rules_response,
    _build_create_style_rule_request,
    _parse_style_rule_response,
    _build_get_style_rule_request,
    _build_update_style_rule_name_request,
    _build_delete_style_rule_request,
    _build_update_style_rule_configured_rules_request,
    _build_create_style_rule_custom_instruction_request,
    _parse_custom_instruction_response,
    _build_get_style_rule_custom_instruction_request,
    _build_update_style_rule_custom_instruction_request,
    _build_delete_style_rule_custom_instruction_request,
)
