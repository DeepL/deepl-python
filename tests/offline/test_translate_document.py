# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import io

import deepl
import pytest

from .client import make_translator, url
from .matchers import json_request, multipart_request

HANDLE = deepl.DocumentHandle("doc-1", "key-1")
KEY_BODY = {"document_key": "key-1"}
BINARY_CONTENT = bytes(range(256)) * 4


def reply_with_handle(mocked, files, data=None):
    mocked.post(
        url("v2/document"),
        json={"document_id": "doc-1", "document_key": "key-1"},
        match=multipart_request(files, data),
    )


def reply_with_status(mocked, status, **fields):
    mocked.post(
        url("v2/document/doc-1"),
        json={"document_id": "doc-1", "status": status, **fields},
        match=json_request(KEY_BODY),
    )


def reply_with_result(mocked, content=b"translated", status=200):
    mocked.post(
        url("v2/document/doc-1/result"),
        body=content,
        status=status,
        match=json_request(KEY_BODY),
    )


def test_sends_file_object_as_multipart(mocked, tmp_path):
    path = tmp_path / "document.txt"
    path.write_text("hello")
    reply_with_handle(
        mocked, {"file": ("document.txt", b"hello")}, {"target_lang": "DE"}
    )

    with open(path, "rb") as input_file:
        make_translator().translate_document_upload(
            input_file, target_lang="de"
        )


@pytest.mark.parametrize("content", [b"hello", "hello"])
def test_sends_string_and_bytes_content_with_filename(mocked, content):
    reply_with_handle(
        mocked, {"file": ("a.txt", content)}, {"target_lang": "DE"}
    )

    make_translator().translate_document_upload(
        content, target_lang="DE", filename="a.txt"
    )


def test_sends_binary_file_content_unchanged(mocked):
    reply_with_handle(
        mocked, {"file": ("a.docx", BINARY_CONTENT)}, {"target_lang": "DE"}
    )

    make_translator().translate_document_upload(
        BINARY_CONTENT, target_lang="DE", filename="a.docx"
    )


def test_raises_when_uploading_content_without_filename():
    with pytest.raises(ValueError, match="filename is required"):
        make_translator().translate_document_upload(b"hello", target_lang="DE")


@pytest.mark.parametrize(
    "body",
    [
        [{"document_id": "doc-1", "document_key": "key-1"}],
        {"document_id": "doc-1"},
        {"document_key": "key-1"},
        {"document_id": "", "document_key": "key-1"},
    ],
)
def test_raises_when_upload_response_lacks_document_handle(mocked, body):
    mocked.post(url("v2/document"), json=body)

    with pytest.raises(deepl.DeepLException, match="document_id"):
        make_translator().translate_document_upload(
            b"hello", target_lang="DE", filename="a.txt"
        )


def test_accepts_source_and_target_lang_positionally_on_upload(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE", "source_lang": "EN"},
    )

    make_translator().translate_document_upload(
        b"hello", "en", "de", filename="a.txt"
    )


def test_accepts_source_and_target_lang_positionally(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE", "source_lang": "EN"},
    )
    reply_with_status(mocked, "done")
    reply_with_result(mocked)

    make_translator().translate_document(
        b"hello", io.BytesIO(), "EN", "DE", filename="a.txt"
    )


def test_accepts_source_and_target_lang_positionally_from_filepath(
    mocked, tmp_path
):
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello")
    reply_with_handle(
        mocked,
        {"file": ("input.txt", b"hello")},
        {"target_lang": "DE"},
    )
    reply_with_status(mocked, "done")
    reply_with_result(mocked)

    make_translator().translate_document_from_filepath(
        input_path, tmp_path / "output.txt", None, "DE"
    )


@pytest.mark.parametrize(
    "method, call",
    [
        (
            "translate_document_upload",
            lambda t, tmp: t.translate_document_upload(b"x", filename="a.txt"),
        ),
        (
            "translate_document",
            lambda t, tmp: t.translate_document(b"x", io.BytesIO(), "EN"),
        ),
        (
            "translate_document_from_filepath",
            lambda t, tmp: t.translate_document_from_filepath(
                tmp / "in.txt", tmp / "out.txt", source_lang="EN"
            ),
        ),
    ],
)
def test_raises_when_target_lang_is_missing(method, call, tmp_path):
    with pytest.raises(
        TypeError,
        match=rf"^{method}\(\) missing required argument: 'target_lang'$",
    ):
        call(make_translator(), tmp_path)


def test_sends_all_options_as_form_fields(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {
            "target_lang": "EN-US",
            "source_lang": "DE",
            "formality": "prefer_more",
            "glossary_ids": "g1,g2",
            "style_id": "style-1",
            "style_profile_id": "sp-1",
            "translation_memory_id": "tm-1",
            "translation_memory_threshold": 80,
            "output_format": "pdf",
            "extra": "value",
        },
    )

    make_translator().translate_document_upload(
        b"hello",
        filename="a.txt",
        source_lang="de",
        target_lang="en-us",
        formality=deepl.Formality.PREFER_MORE,
        glossary_ids=["g1", "g2"],
        style_rule="style-1",
        style_profile="sp-1",
        translation_memory="tm-1",
        translation_memory_threshold=80,
        output_format="pdf",
        extra_body_parameters={"extra": "value"},
    )


@pytest.mark.parametrize(
    "profile",
    [
        "sp-1",
        deepl.StyleProfile.from_json(
            {
                "style_profile_id": "sp-1",
                "name": "profile",
                "creation_time": "2026-10-26T16:27:10Z",
                "updated_time": "2026-10-26T16:27:10Z",
            }
        ),
    ],
)
def test_sends_style_profile_id_as_form_field(mocked, profile):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE", "style_profile_id": "sp-1"},
    )

    make_translator().translate_document_upload(
        b"hello", filename="a.txt", target_lang="DE", style_profile=profile
    )


@pytest.mark.parametrize(
    "enable_watermark, expected", [(True, "true"), (False, "false")]
)
def test_sends_enable_watermark_with_output_format(
    mocked, enable_watermark, expected
):
    reply_with_handle(
        mocked,
        {"file": ("a.docx", BINARY_CONTENT)},
        {
            "target_lang": "DE",
            "output_format": "pdf",
            "enable_watermark": expected,
        },
    )

    make_translator().translate_document_upload(
        BINARY_CONTENT,
        filename="a.docx",
        target_lang="DE",
        output_format="pdf",
        enable_watermark=enable_watermark,
    )


def test_omits_enable_watermark_when_unset(mocked):
    reply_with_handle(
        mocked, {"file": ("a.docx", BINARY_CONTENT)}, {"target_lang": "DE"}
    )

    make_translator().translate_document_upload(
        BINARY_CONTENT, filename="a.docx", target_lang="DE"
    )


def test_sends_enable_watermark_when_translating_from_filepath(
    mocked, tmp_path
):
    input_path = tmp_path / "input.docx"
    input_path.write_bytes(BINARY_CONTENT)
    output_path = tmp_path / "output.docx"
    reply_with_handle(
        mocked,
        {"file": ("input.docx", BINARY_CONTENT)},
        {
            "target_lang": "DE",
            "enable_watermark": "true",
        },
    )
    reply_with_status(mocked, "done")
    reply_with_result(mocked)

    make_translator().translate_document_from_filepath(
        input_path, output_path, target_lang="DE", enable_watermark=True
    )


def test_sends_glossary_id_as_form_field(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE", "source_lang": "EN", "glossary_id": "g1"},
    )

    make_translator().translate_document_upload(
        b"hello",
        filename="a.txt",
        source_lang="EN",
        target_lang="DE",
        glossary="g1",
    )


def test_sends_extra_body_parameters_over_form_fields(mocked):
    reply_with_handle(
        mocked, {"file": ("a.txt", b"hello")}, {"target_lang": "FR"}
    )

    make_translator().translate_document_upload(
        b"hello",
        filename="a.txt",
        target_lang="DE",
        extra_body_parameters={"target_lang": "FR"},
    )


def test_raises_when_uploading_with_invalid_glossary_options():
    with pytest.raises(ValueError, match="source_lang is required"):
        make_translator().translate_document_upload(
            b"hello", filename="a.txt", target_lang="DE", glossary_ids=["g"]
        )


@pytest.mark.parametrize(
    "fields, status",
    [
        ({"seconds_remaining": 7}, deepl.DocumentStatus.Status.QUEUED),
        ({"billed_characters": 5}, deepl.DocumentStatus.Status.DONE),
        ({"error_message": "bad file"}, deepl.DocumentStatus.Status.ERROR),
    ],
)
def test_parses_document_status(mocked, fields, status):
    reply_with_status(mocked, status.value, **fields)

    result = make_translator().translate_document_get_status(HANDLE)

    assert result.status == status
    assert result.ok == (status != deepl.DocumentStatus.Status.ERROR)
    assert result.done == (status == deepl.DocumentStatus.Status.DONE)
    assert str(result) == status.value


def test_parses_document_id_from_status_response(mocked):
    mocked.post(
        url("v2/document/doc-1"),
        json={"document_id": "doc-from-api", "status": "queued"},
        match=json_request(KEY_BODY),
    )

    result = make_translator().translate_document_get_status(HANDLE)

    assert result.document_id == "doc-from-api"


@pytest.mark.parametrize("document_id", [None, 5])
def test_falls_back_to_handle_document_id(mocked, document_id):
    mocked.post(
        url("v2/document/doc-1"),
        json={"document_id": document_id, "status": "queued"},
        match=json_request(KEY_BODY),
    )

    result = make_translator().translate_document_get_status(HANDLE)

    assert result.document_id == "doc-1"
    assert result.status == deepl.DocumentStatus.Status.QUEUED


def test_keeps_unknown_document_status_as_string(mocked):
    reply_with_status(mocked, "postprocessing")

    result = make_translator().translate_document_get_status(HANDLE)

    assert result.status == "postprocessing"
    assert str(result) == "postprocessing"
    assert result.ok
    assert not result.done


def test_keeps_polling_while_document_status_is_unknown(mocked, no_sleep):
    reply_with_status(mocked, "postprocessing")
    reply_with_status(mocked, "done")

    status = make_translator().translate_document_wait_until_done(HANDLE)

    assert status.done


def test_url_encodes_document_id_in_status_and_download_paths(mocked):
    handle = deepl.DocumentHandle("doc/1 ?", "key-1")
    mocked.post(
        url("v2/document/doc%2F1%20%3F"),
        json={"document_id": "doc/1 ?", "status": "done"},
        match=json_request(KEY_BODY),
    )
    mocked.post(
        url("v2/document/doc%2F1%20%3F/result"),
        body=b"translated",
        match=json_request(KEY_BODY),
    )
    translator = make_translator()

    translator.translate_document_get_status(handle)
    translator.translate_document_download(handle, io.BytesIO())


def test_raises_when_document_status_is_empty(mocked):
    mocked.post(
        url("v2/document/doc-1"), json={}, match=json_request(KEY_BODY)
    )

    with pytest.raises(
        deepl.DocumentTranslationException, match="empty response"
    ) as exc_info:
        make_translator().translate_document_get_status(HANDLE)

    assert exc_info.value.document_handle is HANDLE


def test_polls_status_until_document_is_done(mocked):
    reply_with_status(mocked, "translating", seconds_remaining=1)
    reply_with_status(mocked, "done", billed_characters=3)

    status = make_translator().translate_document_wait_until_done(HANDLE)

    assert status.done


def test_raises_with_error_message_when_waited_document_fails(mocked):
    reply_with_status(mocked, "error", error_message="bad file")

    with pytest.raises(deepl.DeepLException, match="bad file") as exc_info:
        make_translator().translate_document_wait_until_done(HANDLE)

    assert not isinstance(exc_info.value, deepl.DocumentTranslationException)


def test_raises_when_waiting_exceeds_timeout(mocked):
    reply_with_status(mocked, "translating")

    # A negative timeout is exceeded on the first check without any sleep.
    with pytest.raises(deepl.DeepLException, match="Manual timeout of -1s"):
        make_translator().translate_document_wait_until_done(
            HANDLE, timeout_s=-1
        )


def test_translates_document_through_upload_status_and_download(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE"},
    )
    reply_with_status(mocked, "done", billed_characters=5)
    reply_with_result(mocked, b"translated")
    output = io.BytesIO()

    make_translator().translate_document(
        b"hello",
        output,
        target_lang="DE",
        filename="a.txt",
    )

    assert output.getvalue() == b"translated"


def test_raises_with_handle_when_document_translation_fails(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE"},
    )
    reply_with_status(mocked, "error", error_message="bad file")

    with pytest.raises(
        deepl.DocumentTranslationException, match="bad file"
    ) as exc_info:
        make_translator().translate_document(
            b"hello",
            io.BytesIO(),
            target_lang="DE",
            filename="a.txt",
        )

    assert exc_info.value.document_handle.document_id == "doc-1"


def test_wraps_upload_failure_without_handle(mocked):
    mocked.post(url("v2/document"), status=456, json={"message": "limit"})

    with pytest.raises(deepl.DocumentTranslationException) as exc_info:
        make_translator().translate_document(
            b"hello", io.BytesIO(), target_lang="DE", filename="a.txt"
        )

    assert exc_info.value.document_handle is None
    assert isinstance(exc_info.value.__cause__, deepl.QuotaExceededException)
    assert "Quota for this billing period has been exceeded" in str(
        exc_info.value
    )


def test_raises_with_handle_when_document_status_fails(mocked):
    reply_with_handle(
        mocked,
        {"file": ("a.txt", b"hello")},
        {"target_lang": "DE"},
    )
    mocked.post(
        url("v2/document/doc-1"),
        status=456,
        json={"message": "limit"},
        match=json_request(KEY_BODY),
    )

    with pytest.raises(deepl.DocumentTranslationException) as exc_info:
        make_translator().translate_document(
            b"hello",
            io.BytesIO(),
            target_lang="DE",
            filename="a.txt",
        )

    assert "Quota for this billing period has been exceeded" in str(
        exc_info.value
    )
    assert exc_info.value.document_handle.document_key == "key-1"


def test_raises_when_downloading_document_that_is_not_ready(
    mocked, no_retries
):
    reply_with_result(mocked, b"", status=503)

    with pytest.raises(deepl.DocumentNotReadyException) as exc_info:
        make_translator().translate_document_download(HANDLE, io.BytesIO())

    assert exc_info.value.should_retry
    assert exc_info.value.http_status_code == 503


def test_warns_and_returns_streaming_response_when_downloading_without_file(
    mocked,
):
    reply_with_result(mocked, b"translated")

    with pytest.warns(DeprecationWarning, match="pass output_file"):
        response = make_translator().translate_document_download(HANDLE)

    assert b"".join(response.iter_content(chunk_size=4)) == b"translated"


def test_writes_download_into_file_object_in_chunks(mocked):
    reply_with_result(mocked, BINARY_CONTENT)
    output = io.BytesIO()

    result = make_translator().translate_document_download(
        HANDLE, output, chunk_size=64
    )

    assert result is None
    assert output.getvalue() == BINARY_CONTENT


def test_retries_upload_when_rate_limited(mocked):
    mocked.post(url("v2/document"), status=429)
    reply_with_handle(
        mocked, {"file": ("a.txt", b"hello")}, {"target_lang": "DE"}
    )

    make_translator().translate_document_upload(
        b"hello", filename="a.txt", target_lang="DE"
    )


def test_translates_document_between_file_paths(mocked, tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello")
    output_path = tmp_path / "output.txt"
    reply_with_handle(
        mocked,
        {"file": ("input.txt", b"hello")},
        {"target_lang": "DE", "source_lang": "EN"},
    )
    reply_with_status(mocked, "done", billed_characters=5)
    reply_with_result(mocked, b"translated")

    make_translator().translate_document_from_filepath(
        input_path, output_path, source_lang="EN", target_lang="DE"
    )

    assert output_path.read_bytes() == b"translated"


def test_sends_output_format_from_different_output_extension(mocked, tmp_path):
    input_path = tmp_path / "input.docx"
    input_path.write_bytes(BINARY_CONTENT)
    output_path = tmp_path / "output.PDF"
    reply_with_handle(
        mocked,
        {"file": ("input.docx", BINARY_CONTENT)},
        {"target_lang": "DE", "output_format": "pdf"},
    )
    reply_with_status(mocked, "done")
    reply_with_result(mocked, b"%PDF")

    make_translator().translate_document_from_filepath(
        input_path, output_path, target_lang="DE"
    )


def test_overwrites_existing_output_file(mocked, tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello")
    output_path = tmp_path / "output.txt"
    output_path.write_text("old content that is longer than the result")
    reply_with_handle(
        mocked,
        {"file": ("input.txt", b"hello")},
        {"target_lang": "DE"},
    )
    reply_with_status(mocked, "done")
    reply_with_result(mocked, b"new")

    make_translator().translate_document_from_filepath(
        input_path, output_path, target_lang="DE"
    )

    assert output_path.read_bytes() == b"new"


def test_removes_output_file_when_document_translation_fails(mocked, tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello")
    output_path = tmp_path / "output.txt"
    reply_with_handle(
        mocked,
        {"file": ("input.txt", b"hello")},
        {"target_lang": "DE"},
    )
    reply_with_status(mocked, "error", error_message="bad file")

    with pytest.raises(deepl.DocumentTranslationException):
        make_translator().translate_document_from_filepath(
            input_path, output_path, target_lang="DE"
        )

    assert not output_path.exists()


def test_sends_glossary_style_and_memory_when_translating_from_filepath(
    mocked, tmp_path
):
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello")
    output_path = tmp_path / "output.txt"
    reply_with_handle(
        mocked,
        {"file": ("input.txt", b"hello")},
        {
            "target_lang": "DE",
            "source_lang": "EN",
            "formality": "less",
            "glossary_ids": "g1,g2",
            "style_id": "style-1",
            "translation_memory_id": "tm-1",
            "extra": "1",
        },
    )
    reply_with_status(mocked, "done")
    reply_with_result(mocked)

    make_translator().translate_document_from_filepath(
        input_path,
        output_path,
        source_lang="EN",
        target_lang="DE",
        formality="less",
        glossary_ids=["g1", "g2"],
        style_rule="style-1",
        translation_memory="tm-1",
        extra_body_parameters={"extra": "1"},
    )


@pytest.mark.parametrize(
    "status, body, error, message",
    [
        (400, {"message": "bad key"}, deepl.DeepLException, "bad key"),
        (404, {"message": "gone"}, deepl.NotFoundException, "gone"),
        (456, {"message": "limit"}, deepl.QuotaExceededException, "limit"),
        (409, {"message": "conflict"}, deepl.DeepLException, "conflict"),
        (300, {"message": "choices"}, deepl.DeepLException, "choices"),
    ],
)
def test_raises_with_api_message_when_document_download_fails(
    mocked, status, body, error, message
):
    mocked.post(
        url("v2/document/doc-1/result"),
        status=status,
        json=body,
        match=json_request(KEY_BODY),
    )

    with pytest.raises(error, match=message) as exc_info:
        make_translator().translate_document_download(HANDLE, io.BytesIO())

    assert exc_info.value.http_status_code == status


def test_copies_status_code_and_retry_flag_into_document_exception(
    mocked, no_retries
):
    reply_with_handle(
        mocked, {"file": ("a.txt", b"hello")}, {"target_lang": "DE"}
    )
    mocked.post(url("v2/document/doc-1"), status=500, body="")

    with pytest.raises(deepl.DocumentTranslationException) as exc_info:
        make_translator().translate_document(
            b"hello", io.BytesIO(), target_lang="DE", filename="a.txt"
        )

    assert exc_info.value.http_status_code == 500
    assert exc_info.value.should_retry


def test_raises_value_error_before_any_request_when_input_file_is_missing(
    tmp_path,
):
    with pytest.raises(ValueError, match="file does not exist"):
        make_translator().translate_document_from_filepath(
            tmp_path / "missing.txt", tmp_path / "out.txt", target_lang="DE"
        )

    assert not (tmp_path / "out.txt").exists()


@pytest.mark.parametrize("bad", ["input", "output"])
def test_wraps_file_open_failure_in_document_exception(tmp_path, bad):
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello")
    output_path = tmp_path / "output.txt"
    directory = tmp_path / "dir.txt"
    directory.mkdir()
    if bad == "input":
        input_path = directory
    else:
        output_path = directory

    with pytest.raises(deepl.DocumentTranslationException) as exc_info:
        make_translator().translate_document_from_filepath(
            input_path, output_path, target_lang="DE"
        )

    assert exc_info.value.document_handle is None
    assert isinstance(exc_info.value.__cause__, OSError)
