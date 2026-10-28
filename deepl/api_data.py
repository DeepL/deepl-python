# Copyright 2023 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from deepl.util import get_float_safe, get_int_safe, parse_timestamp


class TextResult:
    """Holds the result of a text translation request."""

    def __init__(
        self,
        text: str,
        detected_source_lang: str,
        billed_characters: int,
        model_type_used: Optional[str] = None,
    ):
        self.text = text
        self.detected_source_lang = detected_source_lang
        self.billed_characters = billed_characters
        self.model_type_used = model_type_used

    def __str__(self):
        return self.text


class WriteResult:
    """Holds the result of a text improvement request."""

    def __init__(
        self, text: str, detected_source_language: str, target_language: str
    ):
        self.text = text
        self.detected_source_language = detected_source_language
        self.target_language = target_language

    def __str__(self):
        return self.text


class DocumentHandle:
    """Handle to an in-progress document translation.

    :param document_id: ID of associated document request.
    :param document_key: Key of associated document request.
    """

    def __init__(self, document_id: str, document_key: str):
        self._document_id = document_id
        self._document_key = document_key

    def __str__(self):
        return f"Document ID: {self.document_id}, key: {self.document_key}"

    @property
    def document_id(self) -> str:
        return self._document_id

    @property
    def document_key(self) -> str:
        return self._document_key


class DocumentStatus:
    """Status of a document translation request.

    :param status: One of the Status enum values below.
    :param seconds_remaining: Estimated time until document translation
        completes in seconds, or None if unknown.
    :param billed_characters: Number of characters billed for this document, or
        None if unknown or before translation is complete.
    :param error_message: A short description of the error, or None if no error
        has occurred.
    """

    class Status(Enum):
        QUEUED = "queued"
        TRANSLATING = "translating"
        DONE = "done"
        DOWNLOADED = "downloaded"
        ERROR = "error"

    def __init__(
        self,
        status: Status,
        seconds_remaining=None,
        billed_characters=None,
        error_message=None,
    ):
        self._status = self.Status(status)
        self._seconds_remaining = seconds_remaining
        self._billed_characters = billed_characters
        self._error_message = error_message

    def __str__(self) -> str:
        return self.status.value

    @property
    def ok(self) -> bool:
        return self._status != self.Status.ERROR

    @property
    def done(self) -> bool:
        return self._status == self.Status.DONE

    @property
    def status(self) -> Status:
        return self._status

    @property
    def seconds_remaining(self) -> Optional[int]:
        return self._seconds_remaining

    @property
    def billed_characters(self) -> Optional[int]:
        return self._billed_characters

    @property
    def error_message(self) -> Optional[int]:
        return self._error_message


class Usage:
    """Holds the result of a usage request.

    The character, document and team_document properties provide details about
    each corresponding usage type. These properties allow each usage type to be
    checked individually.
    For API Pro accounts, api_key_character, speech_to_text_minutes,
    speech_to_speech_minutes, products, start_time and end_time provide
    further details; for other accounts they are invalid or None.
    The any_limit_reached property checks if for any usage type the amount used
    has reached the allowed amount.
    """

    class Detail:
        def __init__(self, json: Optional[dict], prefix: str):
            self._count = get_int_safe(json, f"{prefix}_count")
            self._limit = get_int_safe(json, f"{prefix}_limit")

        @property
        def count(self) -> Optional[int]:
            """Returns the amount used for this usage type, may be None."""
            return self._count

        @property
        def limit(self) -> Optional[int]:
            """Returns the maximum amount for this usage type, may be None."""
            return self._limit

        @property
        def valid(self) -> bool:
            """True iff both the count and limit are set for this usage
            type."""
            return self._count is not None and self._limit is not None

        @property
        def limit_reached(self) -> bool:
            """True if this limit is valid and the amount used is greater than
            or equal to the amount allowed, otherwise False."""
            return self.valid and self.count >= self.limit  # type: ignore[operator] # noqa: E501

        @property
        def limit_exceeded(self) -> bool:
            """Deprecated, use limit_reached instead."""
            import warnings

            warnings.warn(
                "limit_exceeded is deprecated, use limit_reached",
                DeprecationWarning,
                stacklevel=2,
            )
            return self.limit_reached

        def __str__(self) -> str:
            return f"{self.count} of {self.limit}" if self.valid else "Unknown"

    class Product:
        """Usage of one product (e.g. "translate", "write") in the current
        billing period.

        :param product_type: Product type, for example "translate", "write",
            "speechToText" or "speechToSpeech".
        :param billing_unit: Unit the product is billed in, for example
            "characters" or "minutes".
        :param api_key_unit_count: Units used by this API key.
        :param account_unit_count: Units used by the whole account.
        """

        def __init__(
            self,
            product_type: Optional[str],
            billing_unit: Optional[str],
            api_key_unit_count: Optional[int],
            account_unit_count: Optional[int],
        ):
            self._product_type = product_type
            self._billing_unit = billing_unit
            self._api_key_unit_count = api_key_unit_count
            self._account_unit_count = account_unit_count

        @staticmethod
        def from_json(json: dict) -> "Usage.Product":
            return Usage.Product(
                json.get("product_type"),
                json.get("billing_unit"),
                get_int_safe(json, "api_key_unit_count"),
                get_int_safe(json, "account_unit_count"),
            )

        @property
        def product_type(self) -> Optional[str]:
            """Returns the product type, for example "translate"."""
            return self._product_type

        @property
        def billing_unit(self) -> Optional[str]:
            """Returns the billing unit, for example "characters"."""
            return self._billing_unit

        @property
        def api_key_unit_count(self) -> Optional[int]:
            """Returns the units used for this product by this API key."""
            return self._api_key_unit_count

        @property
        def account_unit_count(self) -> Optional[int]:
            """Returns the units used for this product by the account."""
            return self._account_unit_count

        def __str__(self) -> str:
            return (
                f"{self.product_type}: {self.api_key_unit_count} (API key), "
                f"{self.account_unit_count} (account) {self.billing_unit}"
            )

    def __init__(self, json: Optional[dict]):
        self._character = self.Detail(json, "character")
        self._document = self.Detail(json, "document")
        self._team_document = self.Detail(json, "team_document")
        self._api_key_character = self.Detail(json, "api_key_character")
        self._speech_to_text_minutes = self.Detail(
            json, "speech_to_text_minutes"
        )
        self._speech_to_speech_minutes = self.Detail(
            json, "speech_to_speech_minutes"
        )
        products = json.get("products") if json else None
        self._products: Optional[List[Usage.Product]] = (
            [Usage.Product.from_json(p) for p in products]
            if isinstance(products, list)
            else None
        )
        self._start_time = parse_optional_timestamp(
            json.get("start_time") if json else None
        )
        self._end_time = parse_optional_timestamp(
            json.get("end_time") if json else None
        )

    @property
    def any_limit_reached(self) -> bool:
        """True if for the character, document or team document usage, the
        amount used is greater than or equal to the amount allowed, otherwise
        False. The API Pro usage types (api_key_character and the speech
        minutes) are not considered; check their limit_reached directly."""
        return (
            self.character.limit_reached
            or self.document.limit_reached
            or self.team_document.limit_reached
        )

    @property
    def any_limit_exceeded(self) -> bool:
        """Deprecated, use any_limit_reached instead."""
        import warnings

        warnings.warn(
            "any_limit_exceeded is deprecated, use any_limit_reached",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.any_limit_reached

    @property
    def character(self) -> Detail:
        """Returns usage details for characters, primarily associated with the
        translate_text (/translate) function."""
        return self._character

    @property
    def document(self) -> Detail:
        """Returns usage details for documents."""
        return self._document

    @property
    def team_document(self) -> Detail:
        """Returns usage details for documents shared among your team."""
        return self._team_document

    @property
    def api_key_character(self) -> Detail:
        """Returns character usage details for this API key, as opposed to
        character, which covers the whole account. Only valid for API Pro
        accounts."""
        return self._api_key_character

    @property
    def speech_to_text_minutes(self) -> Detail:
        """Returns speech-to-text usage details in minutes. Only valid for API
        Pro accounts."""
        return self._speech_to_text_minutes

    @property
    def speech_to_speech_minutes(self) -> Detail:
        """Returns speech-to-speech usage details in minutes. Only valid for
        API Pro accounts."""
        return self._speech_to_speech_minutes

    @property
    def products(self) -> Optional[List["Usage.Product"]]:
        """Returns the per-product usage details, or None if the response does
        not contain them (only present for API Pro accounts)."""
        return self._products

    @property
    def start_time(self) -> Optional[datetime.datetime]:
        """Returns the start of the current billing period, or None (only
        present for API Pro accounts)."""
        return self._start_time

    @property
    def end_time(self) -> Optional[datetime.datetime]:
        """Returns the end of the current billing period, or None (only
        present for API Pro accounts)."""
        return self._end_time

    def __str__(self) -> str:
        details: List[Tuple[str, Usage.Detail]] = [
            ("Characters", self.character),
            ("Documents", self.document),
            ("Team documents", self.team_document),
        ]
        return "Usage this billing period:\n" + "\n".join(
            [f"{label}: {detail}" for label, detail in details if detail.valid]
        )


class Language:
    """Information about a language supported by DeepL translator.

    :param code: Language code according to ISO 639-1, for example "EN".
        Some target languages also include the regional variant according to
        ISO 3166-1, for example "EN-US".
    :param name: Name of the language in English.
    :param supports_formality: (Optional) Specifies whether the formality
        option is available for this language; target languages only.
    """

    def __init__(
        self, code: str, name: str, supports_formality: Optional[bool] = None
    ):
        self.code = code
        self.name = name
        self.supports_formality = supports_formality

    def __str__(self):
        return self.code

    @staticmethod
    def remove_regional_variant(language: Union[str, "Language"]) -> str:
        """Removes the regional variant from a language, e.g. EN-US gives EN"""
        dash_index = str(language).find("-")
        if dash_index != -1:
            return str(language).upper()[0:dash_index]
        else:
            return str(language).upper()

    ACEHNESE = "ace"
    AFRIKAANS = "af"
    ARAGONESE = "an"
    ARABIC = "ar"
    ASSAMESE = "as"
    AYMARA = "ay"
    AZERBAIJANI = "az"
    BASHKIR = "ba"
    BELARUSIAN = "be"
    BULGARIAN = "bg"
    BHOJPURI = "bho"
    BENGALI = "bn"
    BRETON = "br"
    BOSNIAN = "bs"
    CATALAN = "ca"
    CEBUANO = "ceb"
    KURDISH_SORANI = "ckb"
    CZECH = "cs"
    WELSH = "cy"
    DANISH = "da"
    GERMAN = "de"
    GERMAN_SWISS = "de-CH"  # Only usable as a target language
    GERMAN_GERMANY = "de-DE"  # Only usable as a target language
    GREEK = "el"
    ENGLISH = "en"  # Source or target; as target, translates to en-US
    ENGLISH_BRITISH = "en-GB"  # Only usable as a target language
    ENGLISH_AMERICAN = "en-US"  # Only usable as a target language
    ESPERANTO = "eo"
    SPANISH = "es"
    SPANISH_LATIN_AMERICAN = "es-419"  # Only usable as a target language
    SPANISH_EUROPEAN = "es-ES"  # Only usable as a target language
    ESTONIAN = "et"
    BASQUE = "eu"
    PERSIAN = "fa"
    FINNISH = "fi"
    FRENCH = "fr"
    FRENCH_CANADIAN = "fr-CA"  # Only usable as a target language
    FRENCH_EUROPEAN = "fr-FR"  # Only usable as a target language
    IRISH = "ga"
    GALICIAN = "gl"
    GUARANI = "gn"
    KONKANI = "gom"
    GUJARATI = "gu"
    HAUSA = "ha"
    HEBREW = "he"
    HINDI = "hi"
    CROATIAN = "hr"
    HAITIAN_CREOLE = "ht"
    HUNGARIAN = "hu"
    ARMENIAN = "hy"
    INDONESIAN = "id"
    IGBO = "ig"
    ICELANDIC = "is"
    ITALIAN = "it"
    JAPANESE = "ja"
    JAVANESE = "jv"
    GEORGIAN = "ka"
    KAZAKH = "kk"
    KURDISH_KURMANJI = "kmr"
    KOREAN = "ko"
    KYRGYZ = "ky"
    LATIN = "la"
    LUXEMBOURGISH = "lb"
    LOMBARD = "lmo"
    LINGALA = "ln"
    LITHUANIAN = "lt"
    LATVIAN = "lv"
    MAITHILI = "mai"
    MALAGASY = "mg"
    MAORI = "mi"
    MACEDONIAN = "mk"
    MALAYALAM = "ml"
    MONGOLIAN = "mn"
    MARATHI = "mr"
    MALAY = "ms"
    MALTESE = "mt"
    BURMESE = "my"
    NORWEGIAN = "nb"
    NEPALI = "ne"
    DUTCH = "nl"
    OCCITAN = "oc"
    OROMO = "om"
    PUNJABI = "pa"
    PANGASINAN = "pag"
    KAPAMPANGAN = "pam"
    POLISH = "pl"
    DARI = "prs"
    PASHTO = "ps"
    PORTUGUESE = "pt"  # Source or target; as target, translates to pt-PT
    PORTUGUESE_BRAZILIAN = "pt-BR"  # Only usable as a target language
    PORTUGUESE_EUROPEAN = "pt-PT"  # Only usable as a target language
    QUECHUA = "qu"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SANSKRIT = "sa"
    SICILIAN = "scn"
    SLOVAK = "sk"
    SLOVENIAN = "sl"
    ALBANIAN = "sq"
    SERBIAN = "sr"
    SESOTHO = "st"
    SUNDANESE = "su"
    SWEDISH = "sv"
    SWAHILI = "sw"
    TAMIL = "ta"
    TELUGU = "te"
    TAJIK = "tg"
    THAI = "th"
    TURKMEN = "tk"
    TAGALOG = "tl"
    TSWANA = "tn"
    TURKISH = "tr"
    TSONGA = "ts"
    TATAR = "tt"
    UKRAINIAN = "uk"
    URDU = "ur"
    UZBEK = "uz"
    VIETNAMESE = "vi"
    WOLOF = "wo"
    XHOSA = "xh"
    YIDDISH = "yi"
    CANTONESE = "yue"
    CHINESE = "zh"
    CHINESE_SIMPLIFIED = "zh-Hans"  # Only usable as a target language
    CHINESE_TRADITIONAL = "zh-Hant"  # Only usable as a target language
    ZULU = "zu"


class GlossaryLanguagePair:
    """Information about a pair of languages supported for DeepL glossaries.

    :param source_lang: The code of the source language.
    :param target_lang: The code of the target language.
    """

    def __init__(self, source_lang: str, target_lang: str):
        self._source_lang = source_lang
        self._target_lang = target_lang

    @property
    def source_lang(self) -> str:
        """Returns the code of the source language."""
        return self._source_lang

    @property
    def target_lang(self) -> str:
        """Returns the code of the target language."""
        return self._target_lang


class ResourceFeature:
    """A feature supported by a DeepL API resource, as returned by
    DeepLClient.get_language_resources().

    :param name: The feature name, for example "glossary" or "formality".
    :param needs_source_support: True if the source language must support
        the feature for it to be available, None if not specified.
    :param needs_target_support: True if the target language must support
        the feature for it to be available, None if not specified.
    """

    def __init__(
        self,
        name: str,
        needs_source_support: Optional[bool] = None,
        needs_target_support: Optional[bool] = None,
    ):
        self._name = name
        self._needs_source_support = needs_source_support
        self._needs_target_support = needs_target_support

    @staticmethod
    def from_json(json) -> "ResourceFeature":
        """Create ResourceFeature from the given API JSON object."""
        return ResourceFeature(
            name=json["name"],
            needs_source_support=json.get("needs_source_support"),
            needs_target_support=json.get("needs_target_support"),
        )

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """Returns the feature name."""
        return self._name

    @property
    def needs_source_support(self) -> Optional[bool]:
        """Returns True if the source language must support this feature,
        or None if the API did not specify it."""
        return self._needs_source_support

    @property
    def needs_target_support(self) -> Optional[bool]:
        """Returns True if the target language must support this feature,
        or None if the API did not specify it."""
        return self._needs_target_support


class LanguageResourceInfo:
    """A DeepL API resource and the features it supports, as returned by
    DeepLClient.get_language_resources().

    :param resource: The resource name, for example "translate_text".
    :param features: Dictionary mapping feature names to ResourceFeature
        objects.
    """

    def __init__(self, resource: str, features: Dict[str, ResourceFeature]):
        self._resource = resource
        self._features = features

    @staticmethod
    def from_json(json) -> "LanguageResourceInfo":
        """Create LanguageResourceInfo from the given API JSON object."""
        features = [
            ResourceFeature.from_json(feature)
            for feature in json.get("features") or []
        ]
        return LanguageResourceInfo(
            resource=json["name"],
            features={feature.name: feature for feature in features},
        )

    def __str__(self) -> str:
        return self.resource

    def supports(self, feature: str) -> bool:
        """Returns True if this resource exposes the given feature."""
        return feature in self._features

    @property
    def resource(self) -> str:
        """Returns the resource name."""
        return self._resource

    @property
    def features(self) -> Dict[str, ResourceFeature]:
        """Returns a dictionary mapping feature names to ResourceFeature
        objects."""
        return self._features


class MultilingualGlossaryDictionaryEntries:
    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        entries: Dict[str, str],
    ):
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._entries = entries

    def __str__(self) -> str:
        return (
            "MultilingualGlossaryDictionaryEntries: Source Language "
            f"{self._source_lang}, Target Language {self._target_lang} "
            f"Contents: {self._entries}"
        )

    @staticmethod
    def from_json(json) -> "MultilingualGlossaryDictionaryEntries":
        """Create MultilingualGlossaryDictionaryEntries from the given
        API JSON object.
        """
        return MultilingualGlossaryDictionaryEntries(
            str(json["source_lang"]),
            str(json["target_lang"]),
            json["entries"],
        )

    def to_json(self):
        """Create API JSON object from
        MultilingualGlossaryDictionaryEntries
        """
        return {
            "source_lang": self._source_lang,
            "target_lang": self._target_lang,
            "entries": self._entries,
        }

    @property
    def source_lang(self) -> str:
        return self._source_lang

    @property
    def target_lang(self) -> str:
        return self._target_lang

    @property
    def entries(self) -> Dict[str, str]:
        return self._entries


class MultilingualGlossaryDictionaryEntriesResponse:
    def __init__(
        self, dictionaries: List[MultilingualGlossaryDictionaryEntries]
    ):
        self._dictionaries = dictionaries

    def __str__(self) -> str:
        return (
            "MultilingualGlossaryDictionaryEntriesResponse: "
            f"Contents {self._dictionaries}"
        )

    @staticmethod
    def from_json(json) -> "MultilingualGlossaryDictionaryEntriesResponse":
        """Create MultilingualGlossaryDictionaryEntriesResponse from the given
        API JSON object.
        """
        glossary_dicts = list(json["dictionaries"])
        serialized_dicts = list(
            map(
                lambda glossary_dict: MultilingualGlossaryDictionaryEntries.from_json(  # noqa: E501
                    glossary_dict
                ),
                glossary_dicts,
            )
        )
        return MultilingualGlossaryDictionaryEntriesResponse(serialized_dicts)

    @property
    def dictionaries(self) -> List[MultilingualGlossaryDictionaryEntries]:
        return self._dictionaries


class MultilingualGlossaryDictionaryInfo:
    def __init__(self, source_lang: str, target_lang: str, entry_count: int):
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._entry_count = entry_count

    @staticmethod
    def from_json(json) -> "MultilingualGlossaryDictionaryInfo":
        """Create MultilingualGlossaryDictionaryInfo from the given API JSON
        object."""
        return MultilingualGlossaryDictionaryInfo(
            str(json["source_lang"]).upper(),
            str(json["target_lang"]).upper(),
            int(json["entry_count"]),
        )

    @property
    def source_lang(self) -> str:
        return self._source_lang

    @property
    def target_lang(self) -> str:
        return self._target_lang

    @property
    def entry_count(self) -> int:
        return self._entry_count


class MultilingualGlossaryInfo:
    """Information about a multilingual glossary, excluding the entry list.
    Used by the /v3/glossaries API endpoints

    :param glossary_id: Unique ID assigned to the glossary.
    :param name: User-defined name assigned to the glossary.
    :param creation_time: Timestamp when the glossary was created.
    :param dictionaries: Dictionaries contained in this glossary. Each
        dictionary contains its language pair and the number of entries.
    """

    def __init__(
        self,
        glossary_id: str,
        name: str,
        creation_time: datetime.datetime,
        dictionaries: List[MultilingualGlossaryDictionaryInfo],
    ):
        self._glossary_id = glossary_id
        self._name = name
        self._creation_time = creation_time
        self._dictionaries = dictionaries

    def __str__(self) -> str:
        return f'MultilingualGlossary "{self.name}" ({self.glossary_id})'

    @staticmethod
    def from_json(json) -> "MultilingualGlossaryInfo":
        """Create MultilingualGlossaryInfo from the given API JSON object."""
        return MultilingualGlossaryInfo(
            json["glossary_id"],
            json["name"],
            parse_timestamp(json["creation_time"]),
            list(
                map(
                    lambda entry: MultilingualGlossaryDictionaryInfo.from_json(
                        entry
                    ),
                    json["dictionaries"],
                )
            ),
        )

    def to_json(self) -> dict:
        """Create API JSON object from MultilingualGlossaryInfo."""
        return {
            "glossary_id": self._glossary_id,
            "name": self._name,
            "creation_time": self._creation_time,
            "dictionaries": self._dictionaries,
        }

    @property
    def glossary_id(self) -> str:
        return self._glossary_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def dictionaries(self) -> List[MultilingualGlossaryDictionaryInfo]:
        return self._dictionaries

    @property
    def creation_time(self) -> datetime.datetime:
        return self._creation_time


class SpokenTermsList:
    """Information about the term list of one language in a spoken-terms
    collection, excluding the entries.

    :param lang: Language of the terms.
    :param entry_count: Number of terms in the list.
    """

    def __init__(self, lang: str, entry_count: int):
        self._lang = lang
        self._entry_count = entry_count

    def __str__(self) -> str:
        return f"SpokenTermsList: {self._lang}, {self._entry_count} entries"

    @staticmethod
    def from_json(json) -> "SpokenTermsList":
        """Create SpokenTermsList from the given API JSON object."""
        return SpokenTermsList(str(json["lang"]), int(json["entry_count"]))

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def entry_count(self) -> int:
        return self._entry_count


class SpokenTermsEntries:
    """The terms of one language in a spoken-terms collection.

    :param lang: Language of the terms.
    :param entries: The terms, one per list item.
    """

    def __init__(self, lang: str, entries: List[str]):
        self._lang = lang
        self._entries = entries

    def __str__(self) -> str:
        return f"SpokenTermsEntries: {self._lang}, {self._entries}"

    @staticmethod
    def from_json(json) -> "SpokenTermsEntries":
        """Create SpokenTermsEntries from the given API JSON object."""
        # The API sends the terms newline-separated, one term per line.
        entries = [
            line for line in str(json.get("entries") or "").split("\n") if line
        ]
        return SpokenTermsEntries(str(json["lang"]), entries)

    def to_json(self) -> dict:
        """Create API JSON object from SpokenTermsEntries."""
        return {"lang": self._lang, "entries": "\n".join(self._entries)}

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def entries(self) -> List[str]:
        return self._entries


class SpokenTerms:
    """Information about a spoken-terms collection, excluding the entries.
    Used by the /v3/spoken-terms API endpoints.

    :param spoken_terms_id: Unique ID assigned to the collection.
    :param name: User-defined name assigned to the collection.
    :param creation_time: Timestamp when the collection was created.
    :param term_lists: Term lists in this collection, one per language,
        each with its language and the number of terms.
    """

    def __init__(
        self,
        spoken_terms_id: str,
        name: str,
        creation_time: datetime.datetime,
        term_lists: List[SpokenTermsList],
    ):
        self._spoken_terms_id = spoken_terms_id
        self._name = name
        self._creation_time = creation_time
        self._term_lists = term_lists

    def __str__(self) -> str:
        return f'SpokenTerms "{self._name}" ({self._spoken_terms_id})'

    @staticmethod
    def from_json(json) -> "SpokenTerms":
        """Create SpokenTerms from the given API JSON object."""
        return SpokenTerms(
            json["spoken_terms_id"],
            json["name"],
            parse_timestamp(json["creation_time"]),
            [
                SpokenTermsList.from_json(term_list)
                for term_list in json.get("term_lists") or []
            ],
        )

    @property
    def spoken_terms_id(self) -> str:
        return self._spoken_terms_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def creation_time(self) -> datetime.datetime:
        return self._creation_time

    @property
    def term_lists(self) -> List[SpokenTermsList]:
        return self._term_lists


class GlossaryInfo:
    """Information about a glossary, excluding the entry list. GlossaryInfo
    is compatible with the /v2 glossary endpoints and can only support
    mono-lingual glossaries (e.g. a glossary with only one source and
    target language defined).

    :param glossary_id: Unique ID assigned to the glossary.
    :param name: User-defined name assigned to the glossary.
    :param ready: True iff the glossary may be used for translations.
    :param source_lang: Source language code of the glossary.
    :param target_lang: Target language code of the glossary.
    :param creation_time: Timestamp when the glossary was created.
    :param entry_count: The number of entries contained in the glossary.
    """

    def __init__(
        self,
        glossary_id: str,
        name: str,
        ready: bool,
        source_lang: str,
        target_lang: str,
        creation_time: datetime.datetime,
        entry_count: int,
    ):
        self._glossary_id = glossary_id
        self._name = name
        self._ready = ready
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._creation_time = creation_time
        self._entry_count = entry_count

    def __str__(self) -> str:
        return f'Glossary "{self.name}" ({self.glossary_id})'

    @staticmethod
    def from_json(json) -> "GlossaryInfo":
        """Create GlossaryInfo from the given API JSON object."""
        return GlossaryInfo(
            json["glossary_id"],
            json["name"],
            bool(json["ready"]),
            str(json["source_lang"]).upper(),
            str(json["target_lang"]).upper(),
            parse_timestamp(json["creation_time"]),
            int(json["entry_count"]),
        )

    @property
    def glossary_id(self) -> str:
        return self._glossary_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def source_lang(self) -> str:
        return self._source_lang

    @property
    def target_lang(self) -> str:
        return self._target_lang

    @property
    def creation_time(self) -> datetime.datetime:
        return self._creation_time

    @property
    def entry_count(self) -> int:
        return self._entry_count


class Formality(Enum):
    """Options for formality parameter."""

    LESS = "less"
    """Translate using informal language."""

    DEFAULT = "default"
    """Translate using the default formality."""

    MORE = "more"
    """Translate using formal language."""

    PREFER_MORE = "prefer_more"
    """Translate using formal language if the target language supports
    formality, otherwise use default formality."""

    PREFER_LESS = "prefer_less"
    """Translate using informal language if the target language supports
    formality, otherwise use default formality."""

    def __str__(self):
        return self.value


class SplitSentences(Enum):
    """Options for split_sentences parameter.

    Sets whether the translation engine should first split the input into
    sentences. This is enabled by default. Possible values are:
    - OFF: no splitting at all, whole input is treated as one sentence. Use
        this option if the input text is already split into sentences, to
        prevent the engine from splitting the sentence unintentionally.
    - ALL: (default) splits on punctuation and on newlines.
    - NO_NEWLINES: splits on punctuation only, ignoring newlines.
    """

    OFF = "0"
    ALL = "1"
    NO_NEWLINES = "nonewlines"
    DEFAULT = ALL

    def __str__(self):
        return self.value


class ModelType(Enum):
    """Options for model_type parameter.

    Sets whether the translation engine should use a newer model type that
    offers higher quality translations at the cost of translation time.
    """

    QUALITY_OPTIMIZED = "quality_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    PREFER_QUALITY_OPTIMIZED = "prefer_quality_optimized"

    def __str__(self):
        return self.value


class WritingStyle(Enum):
    """Options for the `style` parameter of the Write API.
    Sets the style the improved text should be in. Note that currently, only
    a style OR a tone is supported.

    When using a style starting with `prefer_`, the style will only be used
    if the chosen or detected language supports it.
    """

    ACADEMIC = "academic"
    BUSINESS = "business"
    CASUAL = "casual"
    DEFAULT = "default"
    PREFER_ACADEMIC = "prefer_academic"
    PREFER_BUSINESS = "prefer_business"
    PREFER_CASUAL = "prefer_casual"
    PREFER_SIMPLE = "prefer_simple"
    SIMPLE = "simple"

    def __str__(self):
        return self.value


class WritingTone(Enum):
    """Options for the `tone` parameter of the Write API.
    Sets the tone the improved text should be in. Note that currently, only
    a style OR a tone is supported.

    When using a tone starting with `prefer_`, the tone will only be used
    if the chosen or detected language supports it.
    """

    CONFIDENT = "confident"
    DEFAULT = "default"
    DIPLOMATIC = "diplomatic"
    ENTHUSIASTIC = "enthusiastic"
    FRIENDLY = "friendly"
    PREFER_CONFIDENT = "prefer_confident"
    PREFER_DIPLOMATIC = "prefer_diplomatic"
    PREFER_ENTHUSIASTIC = "prefer_enthusiastic"
    PREFER_FRIENDLY = "prefer_friendly"

    def __str__(self):
        return self.value


class ConfiguredRules:
    """Configuration rules for a style rule list.

    :param dates_and_times: Date and time formatting rules.
    :param formatting: Text formatting rules.
    :param numbers: Number formatting rules.
    :param punctuation: Punctuation rules.
    :param spelling_and_grammar: Spelling and grammar rules.
    :param style_and_tone: Style and tone rules.
    :param vocabulary: Vocabulary rules.
    """

    def __init__(
        self,
        dates_and_times: Optional[Dict[str, str]] = None,
        formatting: Optional[Dict[str, str]] = None,
        numbers: Optional[Dict[str, str]] = None,
        punctuation: Optional[Dict[str, str]] = None,
        spelling_and_grammar: Optional[Dict[str, str]] = None,
        style_and_tone: Optional[Dict[str, str]] = None,
        vocabulary: Optional[Dict[str, str]] = None,
    ):
        self._dates_and_times = dates_and_times or {}
        self._formatting = formatting or {}
        self._numbers = numbers or {}
        self._punctuation = punctuation or {}
        self._spelling_and_grammar = spelling_and_grammar or {}
        self._style_and_tone = style_and_tone or {}
        self._vocabulary = vocabulary or {}

    @staticmethod
    def from_json(json) -> "ConfiguredRules":
        """Create ConfiguredRules from the given API JSON object."""
        if not json:
            return ConfiguredRules()

        return ConfiguredRules(
            dates_and_times=json.get("dates_and_times"),
            formatting=json.get("formatting"),
            numbers=json.get("numbers"),
            punctuation=json.get("punctuation"),
            spelling_and_grammar=json.get("spelling_and_grammar"),
            style_and_tone=json.get("style_and_tone"),
            vocabulary=json.get("vocabulary"),
        )

    @property
    def dates_and_times(self) -> Dict[str, str]:
        """Returns date and time formatting rules."""
        return self._dates_and_times

    @property
    def formatting(self) -> Dict[str, str]:
        """Returns text formatting rules."""
        return self._formatting

    @property
    def numbers(self) -> Dict[str, str]:
        """Returns number formatting rules."""
        return self._numbers

    @property
    def punctuation(self) -> Dict[str, str]:
        """Returns punctuation rules."""
        return self._punctuation

    @property
    def spelling_and_grammar(self) -> Dict[str, str]:
        """Returns spelling and grammar rules."""
        return self._spelling_and_grammar

    @property
    def style_and_tone(self) -> Dict[str, str]:
        """Returns style and tone rules."""
        return self._style_and_tone

    @property
    def vocabulary(self) -> Dict[str, str]:
        """Returns vocabulary rules."""
        return self._vocabulary


class CustomInstruction:
    """Custom instruction for a style rule.

    :param label: Label for the custom instruction.
    :param prompt: Prompt text for the custom instruction.
    :param source_language: Optional source language code for the custom
        instruction.
    """

    def __init__(
        self,
        label: str,
        prompt: str,
        source_language: Optional[str] = None,
        id: Optional[str] = None,
    ):
        self._label = label
        self._prompt = prompt
        self._source_language = source_language
        self._id = id

    @staticmethod
    def from_json(json) -> "CustomInstruction":
        """Create CustomInstruction from the given API JSON object."""
        return CustomInstruction(
            label=json["label"],
            prompt=json["prompt"],
            source_language=json.get("source_language"),
            id=json.get("id"),
        )

    @property
    def id(self) -> Optional[str]:
        """Returns the unique ID of the custom instruction."""
        return self._id

    @property
    def label(self) -> str:
        """Returns the label of the custom instruction."""
        return self._label

    @property
    def prompt(self) -> str:
        """Returns the prompt text of the custom instruction."""
        return self._prompt

    @property
    def source_language(self) -> Optional[str]:
        """Returns the source language code, if specified."""
        return self._source_language


class StyleRuleInfo:
    """Information about a style rule list.

    :param style_id: Unique ID assigned to the style rule list.
    :param name: User-defined name assigned to the style rule list.
    :param creation_time: Timestamp when the style rule list was created.
    :param updated_time: Timestamp when the style rule list was last updated.
    :param language: Language code for the style rule list.
    :param version: Version number of the style rule list.
    :param configured_rules: The predefined rules that have been enabled.
    :param custom_instructions: Optional list of custom instructions.
    """

    def __init__(
        self,
        style_id: str,
        name: str,
        creation_time: datetime.datetime,
        updated_time: datetime.datetime,
        language: str,
        version: int,
        configured_rules: Optional[ConfiguredRules] = None,
        custom_instructions: Optional[List[CustomInstruction]] = None,
    ):
        self._style_id = style_id
        self._name = name
        self._creation_time = creation_time
        self._updated_time = updated_time
        self._language = language
        self._version = version
        self._configured_rules = configured_rules
        self._custom_instructions = custom_instructions

    def __str__(self) -> str:
        return f'StyleRule "{self.name}" ({self.style_id})'

    @staticmethod
    def from_json(json) -> "StyleRuleInfo":
        """Create StyleRuleInfo from the given API JSON object."""
        configured_rules_data = json.get("configured_rules")
        configured_rules = None
        if configured_rules_data:
            configured_rules = ConfiguredRules.from_json(configured_rules_data)

        custom_instructions_data = json.get("custom_instructions")
        custom_instructions = None
        if custom_instructions_data:
            custom_instructions = [
                CustomInstruction.from_json(instruction)
                for instruction in custom_instructions_data
            ]

        return StyleRuleInfo(
            style_id=json["style_id"],
            name=json["name"],
            creation_time=parse_timestamp(json["creation_time"]),
            updated_time=parse_timestamp(json["updated_time"]),
            language=json["language"],
            version=json["version"],
            configured_rules=configured_rules,
            custom_instructions=custom_instructions,
        )

    @property
    def style_id(self) -> str:
        """Returns the unique ID of the style rule set."""
        return self._style_id

    @property
    def name(self) -> str:
        """Returns the name of the style rule set."""
        return self._name

    @property
    def creation_time(self) -> datetime.datetime:
        """Returns the creation timestamp."""
        return self._creation_time

    @property
    def updated_time(self) -> datetime.datetime:
        """Returns the last update timestamp."""
        return self._updated_time

    @property
    def language(self) -> str:
        """Returns the language code."""
        return self._language

    @property
    def version(self) -> int:
        """Returns the version number."""
        return self._version

    @property
    def configured_rules(self) -> Optional[ConfiguredRules]:
        """Returns the detailed configuration rules."""
        return self._configured_rules

    @property
    def custom_instructions(self) -> List[CustomInstruction]:
        """Returns the list of custom instructions."""
        return self._custom_instructions or []


def parse_optional_timestamp(
    value: Any,
) -> Optional[datetime.datetime]:
    """Parses an optional API timestamp, returning None if it is absent, not
    a string or in an unrecognised format."""
    if not value or not isinstance(value, str):
        return None
    try:
        return parse_timestamp(value)
    except ValueError:
        # Fall back for timestamps without fractional seconds or without a
        # timezone offset.
        try:
            return datetime.datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None


def _parse_utc_timestamp(value: Any) -> Optional[datetime.datetime]:
    """Parses an Admin API timestamp, taking one without a timezone offset
    (e.g. the report start and end dates) as UTC."""
    timestamp = (
        parse_optional_timestamp(value) if isinstance(value, str) else None
    )
    if timestamp is not None and timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=datetime.timezone.utc)
    return timestamp


def _string_list(value) -> List[str]:
    """Returns the strings of an API list; a missing or non-list value is an
    empty list and non-string entries are skipped."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


class StyleProfile:
    """Information about a style profile. Used by the /v3/style_profiles API
    endpoints.

    :param style_profile_id: Unique ID assigned to the style profile.
    :param name: User-defined name assigned to the style profile.
    :param description: Description of the style profile, or None if it has
        none.
    :param industry: Industry the style profile is written for, or None if it
        has none.
    :param glossary_ids: IDs of the linked glossaries, highest priority first.
    :param style_rule_ids: IDs of the linked style rule lists.
    :param translation_memory_ids: IDs of the linked translation memories.
    :param glossary_priority_order_enabled: Whether the order of glossary_ids
        decides which glossary wins when glossaries overlap.
    :param creation_time: Timestamp when the style profile was created, or
        None if the response has none or it cannot be parsed.
    :param updated_time: Timestamp of the last update, or None if the
        response has none or it cannot be parsed.
    """

    def __init__(
        self,
        style_profile_id: str,
        name: str,
        description: Optional[str],
        industry: Optional[str],
        glossary_ids: List[str],
        style_rule_ids: List[str],
        translation_memory_ids: List[str],
        glossary_priority_order_enabled: bool,
        creation_time: Optional[datetime.datetime],
        updated_time: Optional[datetime.datetime],
    ):
        self._style_profile_id = style_profile_id
        self._name = name
        self._description = description
        self._industry = industry
        self._glossary_ids = glossary_ids
        self._style_rule_ids = style_rule_ids
        self._translation_memory_ids = translation_memory_ids
        self._glossary_priority_order_enabled = glossary_priority_order_enabled
        self._creation_time = creation_time
        self._updated_time = updated_time

    def __str__(self) -> str:
        return f'StyleProfile "{self._name}" ({self._style_profile_id})'

    @staticmethod
    def from_json(json) -> "StyleProfile":
        """Create StyleProfile from the given API JSON object."""
        return StyleProfile(
            json["style_profile_id"],
            json["name"],
            _str_or_none(json.get("description")),
            _str_or_none(json.get("industry")),
            _string_list(json.get("glossary_ids")),
            _string_list(json.get("style_rule_ids")),
            _string_list(json.get("translation_memory_ids")),
            json.get("glossary_priority_order_enabled") is True,
            parse_optional_timestamp(json.get("creation_time")),
            parse_optional_timestamp(json.get("updated_time")),
        )

    @property
    def style_profile_id(self) -> str:
        return self._style_profile_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def industry(self) -> Optional[str]:
        return self._industry

    @property
    def glossary_ids(self) -> List[str]:
        return self._glossary_ids

    @property
    def style_rule_ids(self) -> List[str]:
        return self._style_rule_ids

    @property
    def translation_memory_ids(self) -> List[str]:
        return self._translation_memory_ids

    @property
    def glossary_priority_order_enabled(self) -> bool:
        return self._glossary_priority_order_enabled

    @property
    def creation_time(self) -> Optional[datetime.datetime]:
        return self._creation_time

    @property
    def updated_time(self) -> Optional[datetime.datetime]:
        return self._updated_time


class TranslationMemoryInfo:
    """Information about a translation memory.

    :param translation_memory_id: Unique ID assigned to the translation memory.
    :param name: User-defined name assigned to the translation memory.
    :param source_language: Source language code for the translation memory.
    :param target_languages: List of target language codes available.
    :param segment_count: Number of segments stored in the translation memory.
    :param creation_time: Timestamp when the translation memory was created.
    :param updated_time: Timestamp when the translation memory was last
        updated.
    """

    def __init__(
        self,
        translation_memory_id: str,
        name: str,
        source_language: str,
        target_languages: List[str],
        segment_count: int,
        creation_time: Optional[datetime.datetime] = None,
        updated_time: Optional[datetime.datetime] = None,
    ):
        self._translation_memory_id = translation_memory_id
        self._name = name
        self._source_language = source_language
        self._target_languages = target_languages
        self._segment_count = segment_count
        self._creation_time = creation_time
        self._updated_time = updated_time

    def __str__(self) -> str:
        return (
            f'TranslationMemory "{self.name}" '
            f"({self.translation_memory_id})"
        )

    @staticmethod
    def from_json(json) -> "TranslationMemoryInfo":
        """Create TranslationMemoryInfo from the given API JSON object."""
        return TranslationMemoryInfo(
            translation_memory_id=json["translation_memory_id"],
            name=json["name"],
            source_language=json["source_language"],
            target_languages=json.get("target_languages", []),
            segment_count=json.get("segment_count", 0),
            creation_time=parse_optional_timestamp(json.get("creation_time")),
            updated_time=parse_optional_timestamp(json.get("updated_time")),
        )

    @property
    def translation_memory_id(self) -> str:
        """Returns the unique ID of the translation memory."""
        return self._translation_memory_id

    @property
    def name(self) -> str:
        """Returns the name of the translation memory."""
        return self._name

    @property
    def source_language(self) -> str:
        """Returns the source language code."""
        return self._source_language

    @property
    def target_languages(self) -> List[str]:
        """Returns the list of target language codes."""
        return self._target_languages

    @property
    def segment_count(self) -> int:
        """Returns the number of segments stored."""
        return self._segment_count

    @property
    def creation_time(self) -> Optional[datetime.datetime]:
        """Returns the creation timestamp, if provided by the API."""
        return self._creation_time

    @property
    def updated_time(self) -> Optional[datetime.datetime]:
        """Returns the last update timestamp, if provided by the API."""
        return self._updated_time


class TranslationMemoryTargetSegment:
    """A target-language translation attached to a source segment.

    :param target_segment_id: Unique ID assigned to the target segment.
    :param target_language: Target language code of the translation.
    :param target_text: The translated text.
    :param creation_time: Timestamp when the target segment was created.
    :param updated_time: Timestamp when the target segment was last updated.
    :param last_used_time: Timestamp when the target segment was last used.
    """

    def __init__(
        self,
        target_segment_id: str,
        target_language: str,
        target_text: str,
        creation_time: Optional[datetime.datetime] = None,
        updated_time: Optional[datetime.datetime] = None,
        last_used_time: Optional[datetime.datetime] = None,
    ):
        self._target_segment_id = target_segment_id
        self._target_language = target_language
        self._target_text = target_text
        self._creation_time = creation_time
        self._updated_time = updated_time
        self._last_used_time = last_used_time

    def __str__(self) -> str:
        return f"{self.target_language}: {self.target_text}"

    @staticmethod
    def from_json(json) -> "TranslationMemoryTargetSegment":
        """Create TranslationMemoryTargetSegment from the given API JSON
        object."""
        return TranslationMemoryTargetSegment(
            target_segment_id=json["target_segment_id"],
            target_language=json["target_language"],
            target_text=json["target_text"],
            creation_time=parse_optional_timestamp(json.get("creation_time")),
            updated_time=parse_optional_timestamp(json.get("updated_time")),
            last_used_time=parse_optional_timestamp(
                json.get("last_used_time")
            ),
        )

    @property
    def target_segment_id(self) -> str:
        """Returns the unique ID of the target segment."""
        return self._target_segment_id

    @property
    def target_language(self) -> str:
        """Returns the target language code."""
        return self._target_language

    @property
    def target_text(self) -> str:
        """Returns the translated text."""
        return self._target_text

    @property
    def creation_time(self) -> Optional[datetime.datetime]:
        """Returns the creation timestamp, if provided by the API."""
        return self._creation_time

    @property
    def updated_time(self) -> Optional[datetime.datetime]:
        """Returns the last update timestamp, if provided by the API."""
        return self._updated_time

    @property
    def last_used_time(self) -> Optional[datetime.datetime]:
        """Returns the last used timestamp, if provided by the API."""
        return self._last_used_time


class TranslationMemorySegment:
    """A source segment of a translation memory and its translations.

    :param source_segment_id: Unique ID assigned to the source segment.
    :param source_text: The source text.
    :param targets: Translations of the source text, one per target language.
    :param creation_time: Timestamp when the source segment was created.
    :param updated_time: Timestamp when the source segment was last updated.
    :param last_used_time: Timestamp when the source segment was last used.
    """

    def __init__(
        self,
        source_segment_id: str,
        source_text: str,
        targets: List[TranslationMemoryTargetSegment],
        creation_time: Optional[datetime.datetime] = None,
        updated_time: Optional[datetime.datetime] = None,
        last_used_time: Optional[datetime.datetime] = None,
    ):
        self._source_segment_id = source_segment_id
        self._source_text = source_text
        self._targets = targets
        self._creation_time = creation_time
        self._updated_time = updated_time
        self._last_used_time = last_used_time

    def __str__(self) -> str:
        return f"TranslationMemorySegment ({self.source_segment_id})"

    @staticmethod
    def from_json(json) -> "TranslationMemorySegment":
        """Create TranslationMemorySegment from the given API JSON object."""
        return TranslationMemorySegment(
            source_segment_id=json["source_segment_id"],
            source_text=json["source_text"],
            targets=[
                TranslationMemoryTargetSegment.from_json(target)
                for target in json.get("targets", [])
            ],
            creation_time=parse_optional_timestamp(json.get("creation_time")),
            updated_time=parse_optional_timestamp(json.get("updated_time")),
            last_used_time=parse_optional_timestamp(
                json.get("last_used_time")
            ),
        )

    @property
    def source_segment_id(self) -> str:
        """Returns the unique ID of the source segment."""
        return self._source_segment_id

    @property
    def source_text(self) -> str:
        """Returns the source text."""
        return self._source_text

    @property
    def targets(self) -> List[TranslationMemoryTargetSegment]:
        """Returns the translations of the source text."""
        return self._targets

    @property
    def creation_time(self) -> Optional[datetime.datetime]:
        """Returns the creation timestamp, if provided by the API."""
        return self._creation_time

    @property
    def updated_time(self) -> Optional[datetime.datetime]:
        """Returns the last update timestamp, if provided by the API."""
        return self._updated_time

    @property
    def last_used_time(self) -> Optional[datetime.datetime]:
        """Returns the last used timestamp, if provided by the API."""
        return self._last_used_time


class TranslationMemorySegments:
    """One page of translation memory segments.

    :param segments: The segments in this page.
    :param segment_count: Total number of segments stored in the translation
        memory. This is translation-memory-level metadata and is not reduced
        by a text filter.
    :param next_page_cursor: Opaque cursor to pass as page_cursor to fetch the
        next page, or None if this is the last page.
    """

    def __init__(
        self,
        segments: List[TranslationMemorySegment],
        segment_count: int,
        next_page_cursor: Optional[str] = None,
    ):
        self._segments = segments
        self._segment_count = segment_count
        self._next_page_cursor = next_page_cursor

    def __iter__(self):
        return iter(self._segments)

    def __len__(self) -> int:
        return len(self._segments)

    @staticmethod
    def from_json(json) -> "TranslationMemorySegments":
        """Create TranslationMemorySegments from the given API JSON object."""
        return TranslationMemorySegments(
            segments=[
                TranslationMemorySegment.from_json(segment)
                for segment in json.get("segments", [])
            ],
            segment_count=json.get("segment_count", 0),
            next_page_cursor=json.get("next_page_cursor"),
        )

    @property
    def segments(self) -> List[TranslationMemorySegment]:
        """Returns the segments in this page."""
        return self._segments

    @property
    def segment_count(self) -> int:
        """Returns the total number of segments in the translation memory."""
        return self._segment_count

    @property
    def next_page_cursor(self) -> Optional[str]:
        """Returns the cursor for the next page, or None on the last page."""
        return self._next_page_cursor


class TranslationMemoryImport:
    """A newly created translation memory import job.

    The TMX file must be uploaded to upload_url before expires_at; processing
    starts automatically once the upload is detected.

    :param job_id: Unique ID assigned to the import job.
    :param upload_url: URL to upload the TMX file to.
    :param expires_at: Timestamp after which the upload URL is no longer
        valid.
    """

    def __init__(
        self,
        job_id: str,
        upload_url: str,
        expires_at: Optional[datetime.datetime] = None,
    ):
        self._job_id = job_id
        self._upload_url = upload_url
        self._expires_at = expires_at

    def __str__(self) -> str:
        return f"TranslationMemoryImport ({self.job_id})"

    @staticmethod
    def from_json(json) -> "TranslationMemoryImport":
        """Create TranslationMemoryImport from the given API JSON object."""
        return TranslationMemoryImport(
            job_id=json["job_id"],
            upload_url=json["upload_url"],
            expires_at=parse_optional_timestamp(json.get("expires_at")),
        )

    @property
    def job_id(self) -> str:
        """Returns the unique ID of the import job."""
        return self._job_id

    @property
    def upload_url(self) -> str:
        """Returns the URL to upload the TMX file to."""
        return self._upload_url

    @property
    def expires_at(self) -> Optional[datetime.datetime]:
        """Returns the expiry timestamp of the upload URL."""
        return self._expires_at


class TranslationMemoryExport:
    """A translation memory export job.

    :param job_id: Unique ID assigned to the export job.
    :param translation_memory_id: ID of the translation memory being exported.
    :param reused_existing: True if the API reused a previously completed
        export instead of starting a new one.
    """

    def __init__(
        self,
        job_id: str,
        translation_memory_id: Optional[str] = None,
        reused_existing: bool = False,
    ):
        self._job_id = job_id
        self._translation_memory_id = translation_memory_id
        self._reused_existing = reused_existing

    def __str__(self) -> str:
        return f"TranslationMemoryExport ({self.job_id})"

    @staticmethod
    def from_json(json, reused_existing: bool = False):
        """Create TranslationMemoryExport from the given API JSON object."""
        parameters = json.get("parameters") or {}
        return TranslationMemoryExport(
            job_id=json["job_id"],
            translation_memory_id=parameters.get("translation_memory_id"),
            reused_existing=reused_existing,
        )

    @property
    def job_id(self) -> str:
        """Returns the unique ID of the export job."""
        return self._job_id

    @property
    def translation_memory_id(self) -> Optional[str]:
        """Returns the ID of the translation memory being exported."""
        return self._translation_memory_id

    @property
    def reused_existing(self) -> bool:
        """Returns True if a previously completed export was reused."""
        return self._reused_existing


class TranslationMemoryJobResult:
    """The outcome of a translation memory import or export job.

    :param status: Job status, one of "awaiting_input", "processing",
        "completed", "downloaded", "failed" or "expired".
    :param required_action: Human-readable action the caller must take, set
        while the job is waiting on the caller.
    :param download_url: Download URL of the exported TMX file, set once an
        export completes.
    :param expires_at: Timestamp after which the download URL is no longer
        valid.
    :param error_message: Error description, set when the job failed.
    :param translation_memory_id: ID of the translation memory created by a
        completed import.
    :param skipped_segment_count: Number of segments an import skipped.
    """

    STATUS_AWAITING_INPUT = "awaiting_input"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_DOWNLOADED = "downloaded"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"

    def __init__(
        self,
        status: str,
        required_action: Optional[str] = None,
        download_url: Optional[str] = None,
        expires_at: Optional[datetime.datetime] = None,
        error_message: Optional[str] = None,
        translation_memory_id: Optional[str] = None,
        skipped_segment_count: Optional[int] = None,
    ):
        self._status = status
        self._required_action = required_action
        self._download_url = download_url
        self._expires_at = expires_at
        self._error_message = error_message
        self._translation_memory_id = translation_memory_id
        self._skipped_segment_count = skipped_segment_count

    def __str__(self) -> str:
        return f"TranslationMemoryJobResult ({self.status})"

    @staticmethod
    def from_json(json) -> "TranslationMemoryJobResult":
        """Create TranslationMemoryJobResult from the given API JSON
        object."""
        status_metadata = json.get("status_metadata") or {}
        error = json.get("error") or {}
        return TranslationMemoryJobResult(
            status=json.get("status", ""),
            required_action=status_metadata.get("required_action"),
            download_url=json.get("download_url"),
            expires_at=parse_optional_timestamp(json.get("expires_at")),
            error_message=error.get("message"),
            translation_memory_id=json.get("translation_memory_id"),
            skipped_segment_count=json.get("skipped_segment_count"),
        )

    @property
    def status(self) -> str:
        """Returns the job status."""
        return self._status

    @property
    def done(self) -> bool:
        """True if the job has finished, successfully or not."""
        return self._status in (
            self.STATUS_COMPLETED,
            self.STATUS_DOWNLOADED,
            self.STATUS_FAILED,
            self.STATUS_EXPIRED,
        )

    @property
    def ok(self) -> bool:
        """False if the job failed or expired."""
        return self._status not in (self.STATUS_FAILED, self.STATUS_EXPIRED)

    @property
    def required_action(self) -> Optional[str]:
        """Returns the action the caller must take, if any."""
        return self._required_action

    @property
    def download_url(self) -> Optional[str]:
        """Returns the download URL of a completed export."""
        return self._download_url

    @property
    def expires_at(self) -> Optional[datetime.datetime]:
        """Returns the expiry timestamp of the download URL."""
        return self._expires_at

    @property
    def error_message(self) -> Optional[str]:
        """Returns the error description if the job failed."""
        return self._error_message

    @property
    def translation_memory_id(self) -> Optional[str]:
        """Returns the ID of the translation memory a completed import
        created."""
        return self._translation_memory_id

    @property
    def skipped_segment_count(self) -> Optional[int]:
        """Returns the number of segments an import skipped."""
        return self._skipped_segment_count


class TranslationMemoryJob:
    """Status of a translation memory import or export job.

    :param job_id: Unique ID assigned to the job.
    :param operation: Either "import" or "export".
    :param results: Results of the job; the API returns exactly one.
    :param product: Product the job belongs to, always "translation_memory".
    :param creation_time: Timestamp when the job was created.
    :param updated_time: Timestamp when the job was last updated.
    :param translation_memory_id: ID of the translation memory an export job
        reads from.
    :param display_name: Display name an import job assigns to the new
        translation memory.
    :param source_content_type: MIME type declared for an import job's file.
    :param source_content_length: Size in bytes declared for an import job's
        file.
    """

    OPERATION_IMPORT = "import"
    OPERATION_EXPORT = "export"

    def __init__(
        self,
        job_id: str,
        operation: str,
        results: List[TranslationMemoryJobResult],
        product: str = "translation_memory",
        creation_time: Optional[datetime.datetime] = None,
        updated_time: Optional[datetime.datetime] = None,
        translation_memory_id: Optional[str] = None,
        display_name: Optional[str] = None,
        source_content_type: Optional[str] = None,
        source_content_length: Optional[int] = None,
    ):
        self._job_id = job_id
        self._operation = operation
        self._results = results
        self._product = product
        self._creation_time = creation_time
        self._updated_time = updated_time
        self._translation_memory_id = translation_memory_id
        self._display_name = display_name
        self._source_content_type = source_content_type
        self._source_content_length = source_content_length

    def __str__(self) -> str:
        return (
            f"TranslationMemoryJob {self.operation} ({self.job_id}): "
            f"{self.status}"
        )

    @staticmethod
    def from_json(json) -> "TranslationMemoryJob":
        """Create TranslationMemoryJob from the given API JSON object."""
        parameters = json.get("parameters") or {}
        source_file = json.get("source_file") or {}
        return TranslationMemoryJob(
            job_id=json["job_id"],
            operation=json.get("operation", ""),
            results=[
                TranslationMemoryJobResult.from_json(result)
                for result in json.get("results", [])
            ],
            product=json.get("product", "translation_memory"),
            creation_time=parse_optional_timestamp(json.get("creation_time")),
            updated_time=parse_optional_timestamp(json.get("updated_time")),
            translation_memory_id=parameters.get("translation_memory_id"),
            display_name=parameters.get("display_name"),
            source_content_type=source_file.get("content_type"),
            source_content_length=source_file.get("content_length"),
        )

    @property
    def job_id(self) -> str:
        """Returns the unique ID of the job."""
        return self._job_id

    @property
    def operation(self) -> str:
        """Returns the job operation, "import" or "export"."""
        return self._operation

    @property
    def product(self) -> str:
        """Returns the product the job belongs to."""
        return self._product

    @property
    def results(self) -> List[TranslationMemoryJobResult]:
        """Returns the results of the job."""
        return self._results

    @property
    def result(self) -> Optional[TranslationMemoryJobResult]:
        """Returns the single result of the job, or None if absent."""
        return self._results[0] if self._results else None

    @property
    def status(self) -> Optional[str]:
        """Returns the status of the job result."""
        return self.result.status if self.result else None

    @property
    def done(self) -> bool:
        """True if the job has finished, successfully or not."""
        return self.result.done if self.result else False

    @property
    def ok(self) -> bool:
        """False if the job failed or expired."""
        return self.result.ok if self.result else True

    @property
    def creation_time(self) -> Optional[datetime.datetime]:
        """Returns the creation timestamp."""
        return self._creation_time

    @property
    def updated_time(self) -> Optional[datetime.datetime]:
        """Returns the last update timestamp."""
        return self._updated_time

    @property
    def translation_memory_id(self) -> Optional[str]:
        """Returns the translation memory an export job reads from."""
        return self._translation_memory_id

    @property
    def display_name(self) -> Optional[str]:
        """Returns the display name an import job assigns."""
        return self._display_name

    @property
    def source_content_type(self) -> Optional[str]:
        """Returns the MIME type declared for an import job's file."""
        return self._source_content_type

    @property
    def source_content_length(self) -> Optional[int]:
        """Returns the size in bytes declared for an import job's file."""
        return self._source_content_length


class LanguageResource(Enum):
    """Resources that can be passed to
    `DeepLClient.get_languages_for_resource()`."""

    TRANSLATE_TEXT = "translate_text"
    TRANSLATE_DOCUMENT = "translate_document"
    GLOSSARY = "glossary"
    VOICE = "voice"
    WRITE = "write"
    STYLE_RULES = "style_rules"
    TRANSLATION_MEMORY = "translation_memory"

    def __str__(self):
        return self.value


class LanguageInclude(Enum):
    """Options for the `include` parameter of
    `DeepLClient.get_languages_for_resource()`. By default only stable
    languages and features are returned."""

    BETA = "beta"
    """Also return languages and features in beta."""

    EXTERNAL = "external"
    """Also return features that rely on third-party service providers."""

    def __str__(self):
        return self.value


class LanguageFeature:
    """Support level of a single feature of a language for a resource.

    :param status: Availability status of the feature, for example "stable"
        or "beta".
    """

    def __init__(self, status: str):
        self._status = status

    @staticmethod
    def from_json(json) -> "LanguageFeature":
        """Create LanguageFeature from the given API JSON object."""
        return LanguageFeature(status=json["status"])

    @property
    def status(self) -> str:
        """Returns the availability status of the feature."""
        return self._status


class LanguageSupport:
    """Information about a language supported by a DeepL API resource, as
    returned by `DeepLClient.get_languages_for_resource()`.

    :param code: Language code (BCP 47), for example "de" or "en-US".
    :param name: Name of the language in English.
    :param status: Availability status of the language, for example
        "stable" or "beta".
    :param usable_as_source: True if the language can be used as a source
        language for the resource.
    :param usable_as_target: True if the language can be used as a target
        language for the resource.
    :param features: Map of feature name to LanguageFeature; empty if no
        optional features are supported.
    """

    def __init__(
        self,
        code: str,
        name: str,
        status: str,
        usable_as_source: bool,
        usable_as_target: bool,
        features: Dict[str, LanguageFeature],
    ):
        self._code = code
        self._name = name
        self._status = status
        self._usable_as_source = usable_as_source
        self._usable_as_target = usable_as_target
        self._features = features

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    @staticmethod
    def from_json(json) -> "LanguageSupport":
        """Create LanguageSupport from the given API JSON object."""
        features = json.get("features") or {}
        return LanguageSupport(
            code=json["lang"],
            name=json["name"],
            status=json["status"],
            usable_as_source=bool(json["usable_as_source"]),
            usable_as_target=bool(json["usable_as_target"]),
            features={
                name: LanguageFeature.from_json(feature)
                for name, feature in features.items()
            },
        )

    def supports(self, feature: str) -> bool:
        """Returns True if the language supports the given feature, for
        example "formality", for the requested resource."""
        return feature in self._features

    @property
    def code(self) -> str:
        """Returns the language code (BCP 47)."""
        return self._code

    @property
    def name(self) -> str:
        """Returns the name of the language in English."""
        return self._name

    @property
    def status(self) -> str:
        """Returns the availability status of the language."""
        return self._status

    @property
    def usable_as_source(self) -> bool:
        """Returns True if usable as a source language."""
        return self._usable_as_source

    @property
    def usable_as_target(self) -> bool:
        """Returns True if usable as a target language."""
        return self._usable_as_target

    @property
    def features(self) -> Dict[str, LanguageFeature]:
        """Returns the map of feature name to LanguageFeature."""
        return self._features


class AdminUsageGroupBy(Enum):
    """Options for grouping the admin usage analytics report."""

    KEY = "key"
    """Group usage by API key."""

    KEY_AND_DAY = "key_and_day"
    """Group usage by API key and usage date."""

    def __str__(self):
        return self.value


class CustomTagUsageAggregateBy(Enum):
    """Options for aggregating the custom tag usage analytics report."""

    PERIOD = "period"
    """Aggregate usage over the entire date range."""

    DAY = "day"
    """Aggregate usage by individual day."""

    def __str__(self):
        return self.value


def _str_or_none(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _limit_or_none(json: dict, key: str) -> Optional[int]:
    return None if isinstance(json.get(key), bool) else get_int_safe(json, key)


class DeveloperKeyUsageLimits:
    """Usage limits of a developer key. A value of None means unlimited.

    :param characters: Maximum number of characters per usage period.
    :param speech_to_text_milliseconds: Maximum number of speech-to-text
        milliseconds per usage period.
    :param speech_to_speech_milliseconds: Maximum number of speech-to-speech
        milliseconds per usage period.
    """

    def __init__(
        self,
        characters: Optional[int] = None,
        speech_to_text_milliseconds: Optional[int] = None,
        speech_to_speech_milliseconds: Optional[int] = None,
    ):
        self._characters = characters
        self._speech_to_text_milliseconds = speech_to_text_milliseconds
        self._speech_to_speech_milliseconds = speech_to_speech_milliseconds

    @staticmethod
    def from_json(json: Any) -> "DeveloperKeyUsageLimits":
        """Create DeveloperKeyUsageLimits from the given API JSON object."""
        json = _as_dict(json)
        return DeveloperKeyUsageLimits(
            characters=_limit_or_none(json, "characters"),
            speech_to_text_milliseconds=_limit_or_none(
                json, "speech_to_text_milliseconds"
            ),
            speech_to_speech_milliseconds=_limit_or_none(
                json, "speech_to_speech_milliseconds"
            ),
        )

    @property
    def characters(self) -> Optional[int]:
        """Returns the character limit, or None if unlimited."""
        return self._characters

    @property
    def speech_to_text_milliseconds(self) -> Optional[int]:
        """Returns the speech-to-text limit in milliseconds, or None if
        unlimited."""
        return self._speech_to_text_milliseconds

    @property
    def speech_to_speech_milliseconds(self) -> Optional[int]:
        """Returns the speech-to-speech limit in milliseconds, or None if
        unlimited."""
        return self._speech_to_speech_milliseconds


class DeveloperKey:
    """Information about a developer API key, as returned by the Admin API.

    :param key_id: Unique ID of the key.
    :param label: Label assigned to the key.
    :param creation_time: Timestamp when the key was created.
    :param deactivated_time: Timestamp when the key was deactivated, if it was.
    :param is_deactivated: True if the key is deactivated.
    :param usage_limits: Usage limits configured for the key.
    """

    def __init__(
        self,
        key_id: str,
        label: str,
        creation_time: Optional[datetime.datetime],
        deactivated_time: Optional[datetime.datetime],
        is_deactivated: bool,
        usage_limits: DeveloperKeyUsageLimits,
    ):
        self._key_id = key_id
        self._label = label
        self._creation_time = creation_time
        self._deactivated_time = deactivated_time
        self._is_deactivated = is_deactivated
        self._usage_limits = usage_limits

    def __str__(self) -> str:
        return f'DeveloperKey "{self.label}" ({self.key_id})'

    @staticmethod
    def from_json(json: Any) -> "DeveloperKey":
        """Create DeveloperKey from the given API JSON object."""
        json = _as_dict(json)
        return DeveloperKey(
            key_id=_str_or_empty(json, "key_id"),
            label=_str_or_empty(json, "label"),
            creation_time=_parse_utc_timestamp(json.get("creation_time")),
            deactivated_time=_parse_utc_timestamp(
                json.get("deactivated_time")
            ),
            is_deactivated=json.get("is_deactivated") is True,
            usage_limits=DeveloperKeyUsageLimits.from_json(
                json.get("usage_limits")
            ),
        )

    @property
    def key_id(self) -> str:
        """Returns the unique ID of the key."""
        return self._key_id

    @property
    def label(self) -> str:
        """Returns the label of the key."""
        return self._label

    @property
    def creation_time(self) -> Optional[datetime.datetime]:
        """Returns the creation timestamp."""
        return self._creation_time

    @property
    def deactivated_time(self) -> Optional[datetime.datetime]:
        """Returns the deactivation timestamp, or None if the key is active."""
        return self._deactivated_time

    @property
    def is_deactivated(self) -> bool:
        """Returns True if the key is deactivated."""
        return self._is_deactivated

    @property
    def usage_limits(self) -> DeveloperKeyUsageLimits:
        """Returns the usage limits of the key."""
        return self._usage_limits


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _dict_items(value: Any) -> List[dict]:
    """Returns the object entries of a list from the API, skipping any entry
    that is not an object."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _str_or_empty(d: dict, key: str) -> str:
    value = d.get(key)
    return value if isinstance(value, str) else ""


def _int_or_zero(d: Any, key: str) -> int:
    return get_int_safe(_as_dict(d), key) or 0


def _float_or_zero(d: Any, key: str) -> float:
    return get_float_safe(_as_dict(d), key) or 0.0


class AdminUsageBreakdown:
    """Usage totals in an admin usage analytics report."""

    def __init__(
        self,
        total_characters: int,
        text_translation_characters: int,
        document_translation_characters: int,
        text_improvement_characters: int,
        speech_to_text_minutes: float,
        speech_to_speech_minutes: float = 0.0,
    ):
        self._total_characters = total_characters
        self._text_translation_characters = text_translation_characters
        self._document_translation_characters = document_translation_characters
        self._text_improvement_characters = text_improvement_characters
        self._speech_to_text_minutes = speech_to_text_minutes
        self._speech_to_speech_minutes = speech_to_speech_minutes

    @staticmethod
    def from_json(json: Any) -> "AdminUsageBreakdown":
        """Create AdminUsageBreakdown from the given API JSON object."""
        return AdminUsageBreakdown(
            total_characters=_int_or_zero(json, "total_characters"),
            text_translation_characters=_int_or_zero(
                json, "text_translation_characters"
            ),
            document_translation_characters=_int_or_zero(
                json, "document_translation_characters"
            ),
            text_improvement_characters=_int_or_zero(
                json, "text_improvement_characters"
            ),
            speech_to_text_minutes=_float_or_zero(
                json, "speech_to_text_minutes"
            ),
            speech_to_speech_minutes=_float_or_zero(
                json, "speech_to_speech_minutes"
            ),
        )

    @property
    def total_characters(self) -> int:
        """Returns the total number of characters used."""
        return self._total_characters

    @property
    def text_translation_characters(self) -> int:
        """Returns the number of characters used for text translation."""
        return self._text_translation_characters

    @property
    def document_translation_characters(self) -> int:
        """Returns the number of characters used for document translation."""
        return self._document_translation_characters

    @property
    def text_improvement_characters(self) -> int:
        """Returns the number of characters used for text improvement."""
        return self._text_improvement_characters

    @property
    def speech_to_text_minutes(self) -> float:
        """Returns the number of speech-to-text minutes used."""
        return self._speech_to_text_minutes

    @property
    def speech_to_speech_minutes(self) -> float:
        """Returns the number of speech-to-speech minutes used."""
        return self._speech_to_speech_minutes


class KeyUsage:
    """Usage of a single API key in an admin usage analytics report.

    :param api_key: Masked API key.
    :param api_key_label: Label of the API key.
    :param usage: Usage of the API key.
    :param usage_date: Day of the usage, present when grouped by key and day.
    """

    def __init__(
        self,
        api_key: str,
        api_key_label: str,
        usage: AdminUsageBreakdown,
        usage_date: Optional[datetime.datetime] = None,
    ):
        self._api_key = api_key
        self._api_key_label = api_key_label
        self._usage = usage
        self._usage_date = usage_date

    @staticmethod
    def from_json(json: Any) -> "KeyUsage":
        """Create KeyUsage from the given API JSON object."""
        json = _as_dict(json)
        return KeyUsage(
            api_key=_str_or_empty(json, "api_key"),
            api_key_label=_str_or_empty(json, "api_key_label"),
            usage=AdminUsageBreakdown.from_json(json.get("usage")),
            usage_date=_parse_utc_timestamp(json.get("usage_date")),
        )

    @property
    def api_key(self) -> str:
        """Returns the masked API key."""
        return self._api_key

    @property
    def api_key_label(self) -> str:
        """Returns the label of the API key."""
        return self._api_key_label

    @property
    def usage(self) -> AdminUsageBreakdown:
        """Returns the usage of the API key."""
        return self._usage

    @property
    def usage_date(self) -> Optional[datetime.datetime]:
        """Returns the day of the usage, or None if not grouped by day."""
        return self._usage_date


class AdminUsageReport:
    """Admin usage analytics report for a date range.

    :param total_usage: Usage totals over the whole date range.
    :param start_date: Start of the report period.
    :param end_date: End of the report period.
    :param group_by: Grouping used for the report, if any.
    :param key_usages: Usage per key, present when grouped by key.
    :param key_and_day_usages: Usage per key and day, present when grouped by
        key and day.
    """

    def __init__(
        self,
        total_usage: AdminUsageBreakdown,
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
        group_by: Optional[str] = None,
        key_usages: Optional[List[KeyUsage]] = None,
        key_and_day_usages: Optional[List[KeyUsage]] = None,
    ):
        self._total_usage = total_usage
        self._start_date = start_date
        self._end_date = end_date
        self._group_by = group_by
        self._key_usages = key_usages or []
        self._key_and_day_usages = key_and_day_usages or []

    @staticmethod
    def from_json(json: Any) -> "AdminUsageReport":
        """Create AdminUsageReport from the given API JSON object."""
        report = _as_dict(_as_dict(json).get("usage_report"))
        return AdminUsageReport(
            total_usage=AdminUsageBreakdown.from_json(
                report.get("total_usage")
            ),
            start_date=_parse_utc_timestamp(report.get("start_date")),
            end_date=_parse_utc_timestamp(report.get("end_date")),
            group_by=_str_or_none(report.get("group_by")),
            key_usages=[
                KeyUsage.from_json(item)
                for item in _dict_items(report.get("key_usages"))
            ],
            key_and_day_usages=[
                KeyUsage.from_json(item)
                for item in _dict_items(report.get("key_and_day_usages"))
            ],
        )

    @property
    def total_usage(self) -> AdminUsageBreakdown:
        """Returns the usage totals over the whole date range."""
        return self._total_usage

    @property
    def start_date(self) -> Optional[datetime.datetime]:
        """Returns the start of the report period."""
        return self._start_date

    @property
    def end_date(self) -> Optional[datetime.datetime]:
        """Returns the end of the report period."""
        return self._end_date

    @property
    def group_by(self) -> Optional[str]:
        """Returns the grouping used for the report as the API returns it
        (currently "key" or "keyAndDay"), or None."""
        return self._group_by

    @property
    def key_usages(self) -> List[KeyUsage]:
        """Returns the usage per key, empty unless grouped by key."""
        return self._key_usages

    @property
    def key_and_day_usages(self) -> List[KeyUsage]:
        """Returns the usage per key and day, empty unless grouped by key and
        day."""
        return self._key_and_day_usages


class CustomTagUsageBreakdown:
    """Usage totals for a custom tag."""

    def __init__(
        self,
        total_characters: int,
        text_translation_characters: int,
        text_improvement_characters: int,
        speech_to_text_minutes: float,
        speech_to_speech_minutes: float,
    ):
        self._total_characters = total_characters
        self._text_translation_characters = text_translation_characters
        self._text_improvement_characters = text_improvement_characters
        self._speech_to_text_minutes = speech_to_text_minutes
        self._speech_to_speech_minutes = speech_to_speech_minutes

    @staticmethod
    def from_json(json: Any) -> "CustomTagUsageBreakdown":
        """Create CustomTagUsageBreakdown from the given API JSON object."""
        return CustomTagUsageBreakdown(
            total_characters=_int_or_zero(json, "total_characters"),
            text_translation_characters=_int_or_zero(
                json, "text_translation_characters"
            ),
            text_improvement_characters=_int_or_zero(
                json, "text_improvement_characters"
            ),
            speech_to_text_minutes=_float_or_zero(
                json, "speech_to_text_minutes"
            ),
            speech_to_speech_minutes=_float_or_zero(
                json, "speech_to_speech_minutes"
            ),
        )

    @property
    def total_characters(self) -> int:
        """Returns the total number of characters used."""
        return self._total_characters

    @property
    def text_translation_characters(self) -> int:
        """Returns the number of characters used for text translation."""
        return self._text_translation_characters

    @property
    def text_improvement_characters(self) -> int:
        """Returns the number of characters used for text improvement."""
        return self._text_improvement_characters

    @property
    def speech_to_text_minutes(self) -> float:
        """Returns the number of speech-to-text minutes used."""
        return self._speech_to_text_minutes

    @property
    def speech_to_speech_minutes(self) -> float:
        """Returns the number of speech-to-speech minutes used."""
        return self._speech_to_speech_minutes


class CustomTagUsage:
    """Usage of a single custom tag.

    :param custom_tag: The custom tag.
    :param breakdown: Usage of the custom tag.
    :param usage_date: Day of the usage, present when aggregated by day.
    """

    def __init__(
        self,
        custom_tag: str,
        breakdown: CustomTagUsageBreakdown,
        usage_date: Optional[datetime.datetime] = None,
    ):
        self._custom_tag = custom_tag
        self._breakdown = breakdown
        self._usage_date = usage_date

    @staticmethod
    def from_json(json: Any) -> "CustomTagUsage":
        """Create CustomTagUsage from the given API JSON object."""
        json = _as_dict(json)
        return CustomTagUsage(
            custom_tag=_str_or_empty(json, "custom_tag"),
            breakdown=CustomTagUsageBreakdown.from_json(json.get("breakdown")),
            usage_date=_parse_utc_timestamp(json.get("usage_date")),
        )

    @property
    def custom_tag(self) -> str:
        """Returns the custom tag."""
        return self._custom_tag

    @property
    def breakdown(self) -> CustomTagUsageBreakdown:
        """Returns the usage of the custom tag."""
        return self._breakdown

    @property
    def usage_date(self) -> Optional[datetime.datetime]:
        """Returns the day of the usage, or None if not aggregated by day."""
        return self._usage_date


class CustomTagUsageReport:
    """Admin custom tag usage analytics report for a date range.

    :param aggregate_by: Aggregation used for the report.
    :param start_date: Start of the report period.
    :param end_date: End of the report period.
    :param next_page: Page number to request the next page, or None if this
        is the last page.
    :param usage: Usage entries per custom tag.
    """

    def __init__(
        self,
        aggregate_by: Optional[str],
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
        next_page: Optional[int],
        usage: List[CustomTagUsage],
    ):
        self._aggregate_by = aggregate_by
        self._start_date = start_date
        self._end_date = end_date
        self._next_page = next_page
        self._usage = usage

    @staticmethod
    def from_json(json: Any) -> "CustomTagUsageReport":
        """Create CustomTagUsageReport from the given API JSON object."""
        report = _as_dict(_as_dict(json).get("custom_tag_usage_report"))
        return CustomTagUsageReport(
            aggregate_by=_str_or_none(report.get("aggregate_by")),
            start_date=_parse_utc_timestamp(report.get("start_date")),
            end_date=_parse_utc_timestamp(report.get("end_date")),
            next_page=get_int_safe(report, "next_page"),
            usage=[
                CustomTagUsage.from_json(item)
                for item in _dict_items(report.get("usage"))
            ],
        )

    @property
    def aggregate_by(self) -> Optional[str]:
        """Returns the aggregation used for the report as the API returns it
        (e.g. "period" or "day"), or None."""
        return self._aggregate_by

    @property
    def start_date(self) -> Optional[datetime.datetime]:
        """Returns the start of the report period."""
        return self._start_date

    @property
    def end_date(self) -> Optional[datetime.datetime]:
        """Returns the end of the report period."""
        return self._end_date

    @property
    def next_page(self) -> Optional[int]:
        """Returns the page number of the next page, or None if this is the
        last page."""
        return self._next_page

    @property
    def usage(self) -> List[CustomTagUsage]:
        """Returns the usage entries per custom tag."""
        return self._usage
