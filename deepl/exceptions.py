# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from typing import Optional

from deepl.api_data import DocumentHandle


class DeepLException(Exception):
    """Base class for deepl module exceptions.

    :param message: Message describing the error that occurred.
    :param should_retry: True if the request would normally be retried
        following this error, otherwise false.
    :param http_status_code: The HTTP status code in the response, if
        applicable, otherwise None.
    """

    def __init__(
        self,
        message: str,
        should_retry: bool = False,
        http_status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.should_retry = should_retry
        self.http_status_code = http_status_code


class AuthorizationException(DeepLException):
    """Authorization failed, check your authentication key."""

    pass


class NotFoundException(DeepLException):
    """The requested resource was not found (HTTP 404)."""

    pass


class QuotaExceededException(DeepLException):
    """Quota for this billing period has been exceeded."""

    pass


class TooManyRequestsException(DeepLException):
    """The maximum number of failed attempts were reached."""

    pass


class ConnectionException(DeepLException):
    """Connection to the DeepL API failed.

    :param message: Message describing the error that occurred.
    :param should_retry: True if the request would normally be retried
        following this error, otherwise false.
    """

    def __init__(
        self,
        message: str,
        should_retry: bool = False,
    ):
        super().__init__(
            message,
            should_retry=should_retry,
        )


class DocumentTranslationException(DeepLException):
    """Error occurred while translating document.

    :param message: Message describing the error that occurred.
    :param document_handle: The document handle of the associated document.
    """

    def __init__(self, message: str, document_handle: DocumentHandle):
        super().__init__(message)
        self.document_handle = document_handle

    def __str__(self):
        return f"{super().__str__()}, document handle: {self.document_handle}"

    @property
    def document_request(self):
        """Deprecated, use document_handle instead."""
        import warnings

        warnings.warn(
            "document_request is deprecated", DeprecationWarning, stacklevel=2
        )
        return self.document_handle


class GlossaryNotFoundException(NotFoundException):
    """The specified glossary was not found.

    .. deprecated::
        Catch NotFoundException instead, which is raised for every HTTP 404.
        This subclass will be removed in the next major version.
    """

    pass


class DocumentNotReadyException(DeepLException):
    """The translation of the specified document is not yet complete."""

    pass
