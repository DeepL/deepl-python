# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl

from ..fixtures import example_text
from .client import make_translator
from .helpers import JOB_TIMEOUT_S


def test_sends_document_requests_upload_status_and_download(tmp_path):
    input_path = tmp_path / "document.txt"
    input_path.write_text(example_text["EN"])
    output_path = tmp_path / "translated.txt"

    status = make_translator().translate_document_from_filepath(
        input_path, output_path, target_lang="DE", timeout_s=JOB_TIMEOUT_S
    )

    assert status.status == deepl.DocumentStatus.Status.DONE
    assert isinstance(status.billed_characters, int)
    assert output_path.stat().st_size > 0
