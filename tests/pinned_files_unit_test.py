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

import hashlib
import os
import shutil
import stat
import tempfile
import unittest
from unittest import mock
from src import pinned_files
from src.pinned_files import (PinnedDownloadError, download_pinned_files,
                              ensure_private_dir, get_torq_cache_dir,
                              verify_files)

TEST_BASE_URL = "https://example.com/repo/+/commit/dir"
SCRIPT_CONTENT = b"#!/usr/bin/env python3\nprint('hello')\n"
LIB_CONTENT = b"\x7fELF fake library"
TEST_FILES = {
    "script.py": hashlib.sha256(SCRIPT_CONTENT).hexdigest(),
    "bin/linux/x86_64/lib.so": hashlib.sha256(LIB_CONTENT).hexdigest(),
}
TEST_CONTENTS = {
    "script.py": SCRIPT_CONTENT,
    "bin/linux/x86_64/lib.so": LIB_CONTENT,
}
TORQ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fake_fetch(base_url, relative_path):
  return TEST_CONTENTS[relative_path]


class PinnedFilesUnitTest(unittest.TestCase):

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
    env_patcher = mock.patch.dict(os.environ, {"XDG_CACHE_HOME": self.temp_dir})
    env_patcher.start()
    self.addCleanup(env_patcher.stop)
    self.dest_dir = os.path.join(get_torq_cache_dir(), "tool", "pin")
    fetch_patcher = mock.patch.object(
        pinned_files, "_fetch_gitiles_file", side_effect=fake_fetch)
    self.mock_fetch = fetch_patcher.start()
    self.addCleanup(fetch_patcher.stop)

  def staging_dirs(self):
    parent = os.path.dirname(self.dest_dir)
    return [d for d in os.listdir(parent) if d.startswith(".staging-")]

  def test_get_torq_cache_dir_uses_absolute_xdg_cache_home(self):
    self.assertEqual(get_torq_cache_dir(), os.path.join(self.temp_dir, "torq"))

  @mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "relative/dir"})
  def test_get_torq_cache_dir_ignores_relative_xdg_cache_home(self):
    self.assertEqual(get_torq_cache_dir(),
                     os.path.join(os.path.expanduser("~"), ".cache", "torq"))

  def test_download_pinned_files_success(self):
    download_pinned_files(
        TEST_BASE_URL, TEST_FILES, self.dest_dir, executables={"script.py"})

    self.assertTrue(verify_files(self.dest_dir, TEST_FILES))
    for relative_path, content in TEST_CONTENTS.items():
      with open(os.path.join(self.dest_dir, relative_path), "rb") as f:
        self.assertEqual(f.read(), content)
    self.assertEqual(
        stat.S_IMODE(os.stat(os.path.join(self.dest_dir, "script.py")).st_mode),
        0o700)
    self.assertEqual(
        stat.S_IMODE(
            os.stat(os.path.join(self.dest_dir,
                                 "bin/linux/x86_64/lib.so")).st_mode), 0o600)
    self.assertEqual(stat.S_IMODE(os.stat(self.dest_dir).st_mode), 0o700)
    self.assertEqual(self.staging_dirs(), [])

  def test_download_pinned_files_checksum_mismatch_error(self):
    tampered = dict(TEST_CONTENTS,
                    **{"script.py": b"import os; os.system('x')"})
    self.mock_fetch.side_effect = lambda url, path: tampered[path]

    with self.assertRaises(PinnedDownloadError) as e:
      download_pinned_files(TEST_BASE_URL, TEST_FILES, self.dest_dir)

    self.assertIn("Checksum mismatch for 'script.py'", str(e.exception))
    self.assertFalse(os.path.exists(self.dest_dir))
    self.assertEqual(self.staging_dirs(), [])

  def test_download_pinned_files_fetch_failure_error(self):
    self.mock_fetch.side_effect = OSError("network down")

    with self.assertRaises(PinnedDownloadError) as e:
      download_pinned_files(TEST_BASE_URL, TEST_FILES, self.dest_dir)

    self.assertIn("network down", str(e.exception))
    self.assertFalse(os.path.exists(self.dest_dir))
    self.assertEqual(self.staging_dirs(), [])

  def test_download_pinned_files_replaces_tampered_copy(self):
    download_pinned_files(TEST_BASE_URL, TEST_FILES, self.dest_dir)
    with open(os.path.join(self.dest_dir, "script.py"), "wb") as f:
      f.write(b"tampered")
    self.assertFalse(verify_files(self.dest_dir, TEST_FILES))

    download_pinned_files(TEST_BASE_URL, TEST_FILES, self.dest_dir)

    self.assertTrue(verify_files(self.dest_dir, TEST_FILES))

  def test_verify_files_missing_file(self):
    download_pinned_files(TEST_BASE_URL, TEST_FILES, self.dest_dir)
    os.remove(os.path.join(self.dest_dir, "script.py"))

    self.assertFalse(verify_files(self.dest_dir, TEST_FILES))

  def test_verify_files_symlinks(self):
    download_pinned_files(TEST_BASE_URL, TEST_FILES, self.dest_dir)
    link_dir = os.path.join(self.temp_dir, "links")
    os.makedirs(os.path.join(link_dir, "bin/linux/x86_64"))
    for relative_path in TEST_FILES:
      os.symlink(
          os.path.join(self.dest_dir, relative_path),
          os.path.join(link_dir, relative_path))

    self.assertFalse(verify_files(link_dir, TEST_FILES))
    self.assertTrue(verify_files(link_dir, TEST_FILES, follow_symlinks=True))

  def test_ensure_private_dir_creates_private_dir(self):
    ensure_private_dir(self.dest_dir)

    self.assertTrue(os.path.isdir(self.dest_dir))
    self.assertEqual(stat.S_IMODE(os.stat(self.dest_dir).st_mode), 0o700)

  def test_ensure_private_dir_rejects_writable_by_others(self):
    ensure_private_dir(self.dest_dir)
    os.chmod(os.path.dirname(self.dest_dir), 0o777)

    with self.assertRaises(PinnedDownloadError) as e:
      ensure_private_dir(self.dest_dir)

    self.assertIn("writable by other users", str(e.exception))

  def test_ensure_private_dir_rejects_symlink(self):
    real_dir = os.path.join(self.temp_dir, "elsewhere")
    os.makedirs(real_dir, mode=0o700)
    os.makedirs(os.path.dirname(self.dest_dir), mode=0o700)
    os.symlink(real_dir, self.dest_dir)

    with self.assertRaises(PinnedDownloadError) as e:
      ensure_private_dir(self.dest_dir)

    self.assertIn("is not a directory", str(e.exception))

  @unittest.skipUnless(hasattr(os, "geteuid"), "requires POSIX ownership")
  def test_ensure_private_dir_rejects_dir_owned_by_other_user(self):
    ensure_private_dir(self.dest_dir)

    with mock.patch.object(os, "geteuid", return_value=os.geteuid() + 1):
      with self.assertRaises(PinnedDownloadError) as e:
        ensure_private_dir(self.dest_dir)

    self.assertIn("not owned by the current user", str(e.exception))

  def test_simpleperf_pins_match_bazel_module(self):
    module_bazel = os.path.join(TORQ_ROOT, "MODULE.bazel")
    if not os.path.exists(module_bazel):
      self.skipTest("MODULE.bazel is not available")
    with open(module_bazel) as f:
      module = f.read()

    self.assertIn('SIMPLEPERF_COMMIT = "%s"' % pinned_files.SIMPLEPERF_COMMIT,
                  module)
    pinned_paths = list(pinned_files.SIMPLEPERF_PYTHON_FILES)
    for libs in pinned_files.SIMPLEPERF_HOST_LIBS.values():
      pinned_paths.extend(libs)
    for relative_path in pinned_paths:
      self.assertIn("/simpleperf/scripts/%s?format=TEXT" % relative_path,
                    module)


if __name__ == '__main__':
  unittest.main()
