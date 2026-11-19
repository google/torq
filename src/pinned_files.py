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
Pinned, integrity-checked host dependencies that torq fetches at runtime.

Files are fetched one at a time from a pinned Gitiles commit (the
'?format=TEXT' endpoint serves the base64-encoded blob, which is byte-stable,
unlike Gitiles '+archive' tarballs) and every file is checked against a pinned
SHA-256 before it is stored or used. Files are stored in a private per-user
cache directory instead of a shared, predictable location such as /tmp.

When updating a pin, also update the matching http_file() entries in
MODULE.bazel. tools/update_pinned_deps.py prints the values for both.
"""

import base64
import hashlib
import os
import shutil
import stat
import sys
import tempfile
import urllib.request

GITILES_BASE_URL = "https://android.googlesource.com"
DOWNLOAD_TIMEOUT_SECS = 120

# simpleperf host scripts, from platform/system/extras/simpleperf/scripts.
SIMPLEPERF_COMMIT = "fc2494a2abd7ab21774d03deb09c1362bbb0bba8"
SIMPLEPERF_BASE_URL = (f"{GITILES_BASE_URL}/platform/system/extras/+/"
                       f"{SIMPLEPERF_COMMIT}/simpleperf/scripts")
SIMPLEPERF_PYTHON_FILES = {
    "binary_cache_builder.py":
        "81ae285c008442dafce668b94312ad3f266777607413ae2005beebd91449a703",
    "gecko_profile_generator.py":
        "d552c14370f2b9d514abfd463fc1d6e44a8a698cd059d37d679c3d893f67babe",
    "simpleperf_utils.py":
        "3e4f859c08441c577f8c7a1175b738f9480f4af7848f249ed755021792d14239",
    "simpleperf_report_lib.py":
        "b14d3d8a497e8ea410db660f1b2dabc2be24fbef28fc4890784c267c1faf3241",
    "etm_types.py":
        "c014cf4876d8f665e06e0b475a2a8748be618ff9e574bc8d3b6a7265e59f3122",
    "report_sample_pb2.py":
        "d5e0f10c795d7bc3462e9b735db706c6d56fec61f4bb2a549dcda008c5e48510",
}
# Native library loaded by simpleperf_report_lib.py, keyed by sys.platform.
SIMPLEPERF_HOST_LIBS = {
    "linux": {
        "bin/linux/x86_64/libsimpleperf_report.so":
            "b27416a7d235a03f70bf04200f30abb1819ce10bbfbbce0bd00abef979bd9653",
    },
    "darwin": {
        "bin/darwin/x86_64/libsimpleperf_report.dylib":
            "091cbbfc8d983ee4f08bbd4fcb1daf2f7d822be57b1f5464db4fc156507c4f42",
    },
}
SIMPLEPERF_EXECUTABLES = {
    "binary_cache_builder.py", "gecko_profile_generator.py"
}

# trace_processor launcher, from platform/external/perfetto/tools. The
# launcher itself verifies the SHA-256 of the native binary it downloads.
TRACE_PROCESSOR_COMMIT = "40b529923598b739b2892a536a7692eedbed5685"
TRACE_PROCESSOR_BASE_URL = (f"{GITILES_BASE_URL}/platform/external/perfetto/+/"
                            f"{TRACE_PROCESSOR_COMMIT}/tools")
TRACE_PROCESSOR_FILES = {
    "trace_processor":
        "6652199a3d7efa306fefd9b306171cd427a5f60bb3cdcdbf16a89f17e4d4d9ad",
}


class PinnedDownloadError(Exception):
  pass


def get_simpleperf_files():
  """Returns {relative path: sha256} of the simpleperf files torq needs."""
  files = dict(SIMPLEPERF_PYTHON_FILES)
  files.update(SIMPLEPERF_HOST_LIBS.get(sys.platform, {}))
  return files


def get_torq_cache_dir():
  cache_home = os.environ.get("XDG_CACHE_HOME")
  if not cache_home or not os.path.isabs(cache_home):
    cache_home = os.path.join(os.path.expanduser("~"), ".cache")
  return os.path.join(cache_home, "torq")


def get_simpleperf_cache_dir():
  return os.path.join(get_torq_cache_dir(), "simpleperf",
                      SIMPLEPERF_COMMIT[:12])


def get_trace_processor_cache_dir():
  return os.path.join(get_torq_cache_dir(), "trace_processor",
                      TRACE_PROCESSOR_COMMIT[:12])


def _check_private_dir(path):
  """
  Raises PinnedDownloadError unless path is a real directory (not a symlink)
  owned by the current user that other users cannot write to.
  """
  st = os.lstat(path)
  if not stat.S_ISDIR(st.st_mode):
    raise PinnedDownloadError(f"'{path}' is not a directory.")
  if hasattr(os, "geteuid") and st.st_uid != os.geteuid():
    raise PinnedDownloadError(
        f"'{path}' is not owned by the current user; refusing to use it.")
  if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
    raise PinnedDownloadError(
        f"'{path}' is writable by other users; refusing to use it.")


def ensure_private_dir(path):
  """
  Creates path (mode 0700) if needed and checks that every directory from the
  torq cache directory down to path is private to the current user.
  """
  torq_cache_dir = os.path.abspath(get_torq_cache_dir())
  current = os.path.abspath(path)
  os.makedirs(current, mode=0o700, exist_ok=True)
  _check_private_dir(current)
  while (current != torq_cache_dir and
         os.path.commonpath([current, torq_cache_dir]) == torq_cache_dir):
    current = os.path.dirname(current)
    _check_private_dir(current)


def sha256_of_file(path):
  digest = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def verify_files(directory, files, follow_symlinks=False):
  """
  Returns True if every file in files ({relative path: sha256}) exists in
  directory as a regular file with the expected SHA-256. Symlinks are rejected
  unless follow_symlinks is set (e.g. for Bazel runfiles trees, which consist
  of symlinks into Bazel's output directory).
  """
  for relative_path, expected_sha256 in files.items():
    path = os.path.join(directory, relative_path)
    try:
      st = os.stat(path) if follow_symlinks else os.lstat(path)
      if not stat.S_ISREG(st.st_mode):
        return False
      if sha256_of_file(path) != expected_sha256:
        return False
    except OSError:
      return False
  return True


def _fetch_gitiles_file(base_url, relative_path):
  url = f"{base_url}/{relative_path}?format=TEXT"
  with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECS) as response:
    return base64.b64decode(response.read())


def download_pinned_files(base_url, files, dest_dir, executables=()):
  """
  Downloads files ({relative path: sha256}) from a pinned Gitiles base_url into
  the private directory dest_dir, verifying each file's SHA-256 before it is
  written. Files are staged in a private temporary directory and moved into
  place atomically, so dest_dir never contains partially downloaded or
  unverified files. Raises PinnedDownloadError on any failure.
  """
  parent_dir = os.path.dirname(os.path.abspath(dest_dir))
  ensure_private_dir(parent_dir)
  staging_dir = tempfile.mkdtemp(prefix=".staging-", dir=parent_dir)
  try:
    for relative_path, expected_sha256 in files.items():
      try:
        content = _fetch_gitiles_file(base_url, relative_path)
      except Exception as e:
        raise PinnedDownloadError(
            f"Failed to download '{relative_path}': {e}") from e
      actual_sha256 = hashlib.sha256(content).hexdigest()
      if actual_sha256 != expected_sha256:
        raise PinnedDownloadError(
            f"Checksum mismatch for '{relative_path}': expected "
            f"{expected_sha256}, got {actual_sha256}.")
      path = os.path.join(staging_dir, relative_path)
      os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
      mode = 0o700 if relative_path in executables else 0o600
      fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
      with os.fdopen(fd, "wb") as f:
        f.write(content)
    if os.path.lexists(dest_dir):
      # A stale or corrupted copy inside our private cache directory.
      if os.path.isdir(dest_dir) and not os.path.islink(dest_dir):
        shutil.rmtree(dest_dir)
      else:
        os.remove(dest_dir)
    os.replace(staging_dir, dest_dir)
  finally:
    if os.path.isdir(staging_dir):
      shutil.rmtree(staging_dir, ignore_errors=True)
  ensure_private_dir(dest_dir)
  if not verify_files(dest_dir, files):
    raise PinnedDownloadError(
        f"Downloaded files in '{dest_dir}' failed verification.")
