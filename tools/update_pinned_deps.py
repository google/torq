#!/usr/bin/env python3
#
# Copyright (C) 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Prints the pins for torq's runtime host dependencies at a given commit.

Usage:
  tools/update_pinned_deps.py simpleperf [<system/extras commit>]
  tools/update_pinned_deps.py trace_processor [<external/perfetto commit>]

Without a commit, the current refs/heads/main commit is used. For each file
this prints the SHA-256 of the decoded file (for src/pinned_files.py) and of
the base64 '?format=TEXT' response (for the http_file() entries in
MODULE.bazel). Review the upstream changes before updating the pins.
"""

import base64
import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import pinned_files  # pylint: disable=wrong-import-position

PROJECTS = {
    "simpleperf": ("platform/system/extras", "simpleperf/scripts", [
        *pinned_files.SIMPLEPERF_PYTHON_FILES, *[
            p for libs in pinned_files.SIMPLEPERF_HOST_LIBS.values()
            for p in libs
        ]
    ]),
    "trace_processor": ("platform/external/perfetto", "tools",
                        list(pinned_files.TRACE_PROCESSOR_FILES)),
}


def fetch(url):
  with urllib.request.urlopen(url, timeout=120) as response:
    return response.read()


def main():
  if len(sys.argv) not in (2, 3) or sys.argv[1] not in PROJECTS:
    print(__doc__)
    return 1
  project, subdir, files = PROJECTS[sys.argv[1]]
  base = f"{pinned_files.GITILES_BASE_URL}/{project}/+"
  if len(sys.argv) == 3:
    commit = sys.argv[2]
  else:
    # Gitiles prefixes JSON responses with ")]}'" to prevent XSSI.
    head = fetch(f"{base}/refs/heads/main?format=JSON").split(b"\n", 1)[1]
    commit = json.loads(head)["commit"]
  print(f"commit: {commit}")
  for relative_path in files:
    text = fetch(f"{base}/{commit}/{subdir}/{relative_path}?format=TEXT")
    decoded_sha256 = hashlib.sha256(base64.b64decode(text)).hexdigest()
    text_sha256 = hashlib.sha256(text).hexdigest()
    print(f"{relative_path}\n  pinned_files.py sha256: {decoded_sha256}"
          f"\n  MODULE.bazel sha256:    {text_sha256}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
