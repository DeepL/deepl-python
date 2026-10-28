# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .version import VERSION as __version__  # noqa

__author__ = "DeepL SE <python-api@deepl.com>"

from .admin_client import DeepLAdminClient

from .api_data import (  # noqa
    AdminUsageBreakdown,
    AppInfo,
    AdminUsageGroupBy,
    AdminUsageReport,
    CustomTagUsage,
    CustomTagUsageAggregateBy,
    CustomTagUsageBreakdown,
    CustomTagUsageReport,
    DeveloperKey,
    DeveloperKeyUsageLimits,
    KeyUsage,
)

from .deepl_client import DeepLClient

from .exceptions import (  # noqa
    AuthorizationException,
    ConnectionException,
    DeepLException,
    DocumentNotReadyException,
    DocumentTranslationException,
    GlossaryNotFoundException,
    NotFoundException,
    TooManyRequestsException,
    QuotaExceededException,
)

from . import http_client  # noqa

from .api_data import (  # noqa
    SpokenTerms,
    SpokenTermsEntries,
    SpokenTermsList,
    StyleProfile,
)

from .translator import (  # noqa
    DocumentHandle,
    DocumentStatus,
    Formality,
    GlossaryInfo,
    Language,
    ModelType,
    SplitSentences,
    TextResult,
    Translator,
    Usage,
)

from .util import (  # noqa
    auth_key_is_free_account,
    convert_tsv_to_dict,
    is_free_account_auth_key,
    convert_dict_to_tsv,
    validate_glossary_term,
)

__all__ = [
    "__version__",
    "__author__",
    "AdminUsageBreakdown",
    "AdminUsageGroupBy",
    "AdminUsageReport",
    "AppInfo",
    "CustomTagUsage",
    "CustomTagUsageAggregateBy",
    "CustomTagUsageBreakdown",
    "CustomTagUsageReport",
    "DeepLAdminClient",
    "DeepLClient",
    "DeveloperKey",
    "DeveloperKeyUsageLimits",
    "KeyUsage",
    "DocumentHandle",
    "DocumentStatus",
    "Formality",
    "GlossaryInfo",
    "Language",
    "SplitSentences",
    "SpokenTerms",
    "SpokenTermsEntries",
    "SpokenTermsList",
    "StyleProfile",
    "TextResult",
    "Translator",
    "Usage",
    "http_client",
    "AuthorizationException",
    "ConnectionException",
    "DeepLException",
    "DocumentNotReadyException",
    "DocumentTranslationException",
    "GlossaryNotFoundException",
    "NotFoundException",
    "TooManyRequestsException",
    "QuotaExceededException",
    "auth_key_is_free_account",
    "convert_tsv_to_dict",
    "convert_dict_to_tsv",
    "is_free_account_auth_key",
    "validate_glossary_term",
]
