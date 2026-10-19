# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
import random
import string
import time
from typing import Callable, TypeVar

import deepl

# Identifies the resources created by this test process.
_RUN_ID = "{}-{}".format(
    datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M"),
    "".join(random.choices(string.ascii_lowercase + string.digits, k=6)),
)

# A job is done within about a minute; the document polling interval is 5 s.
JOB_TIMEOUT_S = 180

T = TypeVar("T")


def get_unique_name(label: str) -> str:
    """Returns a resource name that no other run uses and that shows who
    created the resource: sdktest-python-<yyyymmddHHMM>-<rand6>-<label>."""
    return f"sdktest-python-{_RUN_ID}-{label}"


def get_when_visible(get_resource: Callable[[], T]) -> T:
    """Calls get_resource until the API finds a resource that was just
    created: it can be briefly invisible."""
    for _ in range(9):
        try:
            return get_resource()
        except deepl.GlossaryNotFoundException:
            time.sleep(1)
    return get_resource()
