# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

from typing import Optional

from deepl.api_data import DocumentHandle, TranslationMemoryJob


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
    """Authorization failed (HTTP 401 or 403), check your authentication
    key."""

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
    :param document_handle: The document handle of the associated document,
        or None if the error occurred before the document was uploaded.
    :param should_retry: True if the request would normally be retried
        following this error; copied from a DeepLException cause.
    :param http_status_code: The HTTP status code of a DeepLException cause,
        if it has one, otherwise None.
    """

    def __init__(
        self,
        message: str,
        document_handle: Optional[DocumentHandle],
        should_retry: bool = False,
        http_status_code: Optional[int] = None,
    ):
        super().__init__(
            message,
            should_retry=should_retry,
            http_status_code=http_status_code,
        )
        self.document_handle = document_handle

    def __str__(self):
        if self.document_handle is None:
            return super().__str__()
        return f"{super().__str__()}, document handle: {self.document_handle}"


class TranslationMemoryJobException(DeepLException):
    """Error occurred in import_translation_memory_from_filepath() or
    export_translation_memory_to_filepath().

    :param message: Message describing the error that occurred.
    :param job_id: ID of the import or export job, or None if the error
        occurred before the job was created.
    :param job: The last TranslationMemoryJob status retrieved for the job,
        or None if no status was retrieved yet.
    :param should_retry: True if the request would normally be retried
        following this error; copied from a DeepLException cause.
    :param http_status_code: The HTTP status code of a DeepLException cause,
        if it has one, otherwise None.
    """

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        job: Optional[TranslationMemoryJob] = None,
        should_retry: bool = False,
        http_status_code: Optional[int] = None,
    ):
        super().__init__(
            message,
            should_retry=should_retry,
            http_status_code=http_status_code,
        )
        self.job_id = job.job_id if job_id is None and job else job_id
        self.job = job

    def __str__(self):
        if self.job_id is None:
            return super().__str__()
        return f"{super().__str__()}, job ID: {self.job_id}"


class DocumentNotReadyException(DeepLException):
    """The translation of the specified document is not yet complete."""

    pass
