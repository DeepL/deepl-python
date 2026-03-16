# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from .version import VERSION as __version__  # noqa

__author__ = "DeepL SE <python-api@deepl.com>"

from .deepl_client import DeepLClient  # noqa
from .requests_client import RequestsClient  # noqa
from .retry_config import RetryConfig  # noqa
from ._http_types import SslConfig  # noqa

try:
    from .aiohttp_client import AioHttpClient  # noqa
    from .deepl_client_async import DeepLClientAsync  # noqa

    _have_async = True
except ImportError:
    _have_async = False

from .exceptions import (  # noqa
    AuthorizationException,
    ConnectionException,
    DeepLException,
    DocumentNotReadyException,
    DocumentTranslationException,
    GlossaryNotFoundException,
    TooManyRequestsException,
    QuotaExceededException,
)

from . import http_client  # noqa

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
    convert_dict_to_tsv,
    validate_glossary_term,
)

__all__ = [
    "__version__",
    "__author__",
    "DeepLClient",
    "RequestsClient",
    "RetryConfig",
    "SslConfig",
    "DocumentHandle",
    "DocumentStatus",
    "Formality",
    "GlossaryInfo",
    "Language",
    "ModelType",
    "SplitSentences",
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
    "TooManyRequestsException",
    "QuotaExceededException",
    "auth_key_is_free_account",
    "convert_tsv_to_dict",
    "convert_dict_to_tsv",
    "validate_glossary_term",
]

if _have_async:
    __all__ += ["DeepLClientAsync", "AioHttpClient"]
