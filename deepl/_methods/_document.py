# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import json as json_module
import pathlib
import urllib.parse
from typing import Any, BinaryIO, Dict, Optional, TextIO, Union

from ..api_data import (
    DocumentHandle,
    DocumentStatus,
    Formality,
    GlossaryInfo,
    MultilingualGlossaryInfo,
)
from .._client_base import _check_language_and_formality
from .._http_types import (
    HttpRequest,
    HttpResponse,
    MultipartBody,
    make_file_factory,
)
from ..exceptions import DocumentTranslationException


def _build_document_upload_request(
    server_url: str,
    input_document: Union[TextIO, BinaryIO, str, bytes, Any],
    *,
    target_lang: str,
    source_lang: Optional[str] = None,
    formality: Union[str, Formality, None] = None,
    glossary: Union[str, GlossaryInfo, MultilingualGlossaryInfo, None] = None,
    filename: Optional[str] = None,
    output_format: Optional[str] = None,
    extra_body_parameters: Optional[dict] = None,
) -> HttpRequest:
    """Build a POST /v2/document multipart upload request."""
    if isinstance(input_document, (str, bytes)) and filename is None:
        raise ValueError(
            "filename is required if uploading file content as string or bytes"
        )

    lang_fields = _check_language_and_formality(
        source_lang, target_lang, formality, glossary
    )
    fields: Dict[str, str] = {k: str(v) for k, v in lang_fields.items()}
    if output_format:
        fields["output_format"] = output_format
    if extra_body_parameters:
        fields.update({k: str(v) for k, v in extra_body_parameters.items()})

    if filename is None:
        file_name = getattr(input_document, "name", "document")
        if isinstance(file_name, bytes):
            file_name = file_name.decode("utf-8", errors="replace")
        if isinstance(file_name, str):
            file_name = pathlib.PurePath(file_name).name or "document"
        else:
            file_name = "document"
    else:
        file_name = filename

    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(server_url, "v2/document"),
        multipart=MultipartBody(
            fields=fields,
            file_factory=make_file_factory(
                input_document  # type: ignore[arg-type]
            ),
            file_name=file_name,
            file_content_type="application/octet-stream",
        ),
    )


def _parse_document_upload_response(response: HttpResponse) -> DocumentHandle:
    json_data = json_module.loads(response.content) if response.content else {}
    if not isinstance(json_data, dict):
        json_data = {}
    return DocumentHandle(
        json_data.get("document_id", ""), json_data.get("document_key", "")
    )


def _safe_id(id_str: str) -> str:
    """URL-encode a document/glossary ID for safe path interpolation."""
    return urllib.parse.quote(id_str, safe="")


def _build_document_status_request(
    server_url: str, handle: DocumentHandle
) -> HttpRequest:
    """Build a POST /v2/document/{id} request."""
    body = json_module.dumps({"document_key": handle.document_key}).encode(
        "utf-8"
    )
    doc_id = _safe_id(handle.document_id)
    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(server_url, f"v2/document/{doc_id}"),
        headers={"Content-Type": "application/json"},
        body=body,
    )


def _parse_document_status_response(
    response: HttpResponse, handle: DocumentHandle
) -> DocumentStatus:
    json_data = json_module.loads(response.content) if response.content else {}
    if not isinstance(json_data, dict):
        json_data = {}

    status = json_data.get("status", None)
    if not status:
        raise DocumentTranslationException(
            "Querying document status gave an empty response", handle
        )
    seconds_remaining = json_data.get("seconds_remaining", None)
    billed_characters = json_data.get("billed_characters", None)
    error_message = json_data.get("error_message", None)
    return DocumentStatus(
        status, seconds_remaining, billed_characters, error_message
    )


def _build_document_download_request(
    server_url: str, handle: DocumentHandle
) -> HttpRequest:
    """Build a POST /v2/document/{id}/result streaming request."""
    body = json_module.dumps({"document_key": handle.document_key}).encode(
        "utf-8"
    )
    doc_id = _safe_id(handle.document_id)
    return HttpRequest(
        method="POST",
        url=urllib.parse.urljoin(server_url, f"v2/document/{doc_id}/result"),
        headers={"Content-Type": "application/json"},
        body=body,
    )
