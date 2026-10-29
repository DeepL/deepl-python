# Copyright 2023 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from deepl.translator import TextResult
from html_parsing import TagReplacerHTMLParser
import deepl
import logging
from typing import Dict, Iterator, List, Optional, Tuple


def tokenize_mustache(
    template: str, delimiters: List[Tuple[str, str]]
) -> Iterator[Tuple[str, str]]:
    """
    Tokenizes Mustache template with given delimiters, yielding tuples of
    ("literal", text) or ("tag", tag-content).

    :param template: Mustache template text.
    :param delimiters: List of left and right delimiters identifying Mustache
        tags.
    """
    literal = ""
    while template:
        # Find the next Mustache tag
        for ldel, rdel in delimiters:
            if not template.startswith(ldel):
                continue
            rpos = template.find(rdel, len(ldel))
            if rpos == -1:
                continue
            rpos += len(rdel)

            yield "literal", literal
            literal = ""
            yield "tag", template[0:rpos]
            template = template[rpos:]
            break
        else:
            # Template does not begin with tag, append to literal
            literal += template[0]
            template = template[1:]

    if literal:
        yield "literal", literal


def convert_mustache_to_xml(
    template: str, placeholder_tag: str, delimiters: List[Tuple[str, str]]
) -> Tuple[str, Dict[str, str]]:
    """
    Converts Mustache template to XML by replacing Mustache tags with
    placeholder XML tags.

    :param template: Mustache template text.
    :param placeholder_tag: XML tag name for placeholder tags.
    :param delimiters: List of left and right delimiters identifying Mustache
        tags.
    :return XML and dictionary of replaced tags.
    """
    xml = ""
    id_counter = 0
    extracted_tokens = {}

    tokens = tokenize_mustache(template, delimiters)
    for tag_type, tag_content in tokens:
        if tag_type == "tag":
            tag_id = str(id_counter)
            id_counter += 1
            xml += f'<{placeholder_tag} id="{tag_id}" />'
            extracted_tokens[f"{placeholder_tag}#{tag_id}"] = tag_content
        else:
            xml += tag_content

    return xml, extracted_tokens


def translate_mustache(
    template: str,
    target_lang: str,
    translator: deepl.DeepLClient,
    delimiters: Optional[List[Tuple[str, str]]] = None,
    placeholder_tag: str = "m",
    **kwargs,
) -> str:
    """
    Translates given Mustache template text using the DeepL API, by
    converting the template to XML.

    Most of the arguments of the translate_text function are supported,
    source_lang, target_lang, glossary_id, formality, etc.
    The tag_handling argument is *not* supported, because the Mustache tags
    are replaced by XML before translation.

    :param template: Mustache template to be translated.
    :param target_lang: language code to translate template into, for example
        "DE", "EN-US", "FR".
    :param translator: deepl.DeepLClient to use for translation.
    :param delimiters: Optional. Tuples of left- and right-delimiters
        identifying Mustache tags. Delimiter tuples must be specified in
        order-of-precedence, for example {{{ must be before {{.
    :param placeholder_tag: Optional. Dummy XML-tag to replace Mustache tags,
        defaults to "m".
    :return: Translated Mustache template.
    """
    if not delimiters:
        delimiters = [("{{{", "}}}"), ("{{", "}}")]

    logger = logging.getLogger("deepl")
    # Replace Mustache tags with placeholder XML tags
    placeholder_xml, replaced_tags = convert_mustache_to_xml(
        template, placeholder_tag, delimiters
    )
    logger.info("XML with placeholder tags: %s", placeholder_xml)
    logger.debug("Placeholder tokens: %s", replaced_tags)

    # Translate XML with placeholder tags
    result = translator.translate_text(
        placeholder_xml, target_lang=target_lang, tag_handling="xml", **kwargs
    )
    assert isinstance(result, TextResult)
    logger.info("Translated XML: %s", result.text)

    # Reinsert the extracted Mustache tags in the translated XML
    xml_parser = TagReplacerHTMLParser(replaced_tags)
    xml_parser.feed(result.text)
    xml_parser.close()
    translated_template = xml_parser.parsed()

    return translated_template
