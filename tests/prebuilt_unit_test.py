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
import tempfile
import unittest

from tools.build_prebuilt import (
    build_universal_zipapp,
    calculate_sha256,
    generate_checksums,
    verify_artifact,
)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PrebuiltUnitTest(unittest.TestCase):

  def setUp(self):
    self.test_dir = tempfile.mkdtemp(prefix="torq_prebuilt_test_")

  def tearDown(self):
    shutil.rmtree(self.test_dir, ignore_errors=True)

  def test_build_universal_zipapp(self):
    built_files = build_universal_zipapp(self.test_dir)
    self.assertEqual(len(built_files), 2)

    torq_bin = os.path.join(self.test_dir, 'torq')
    torq_pyz = os.path.join(self.test_dir, 'torq.pyz')

    self.assertTrue(os.path.exists(torq_bin))
    self.assertTrue(os.path.exists(torq_pyz))
    self.assertTrue(os.path.getsize(torq_bin) > 1000)  # > 1 KB

    # Verify execution
    self.assertTrue(verify_artifact(torq_bin))
    self.assertTrue(verify_artifact(torq_pyz))

  def test_calculate_sha256_and_generate_checksums(self):
    sample_file = os.path.join(self.test_dir, "sample.txt")
    sample_content = b"Torq prebuilt test string"
    with open(sample_file, "wb") as f:
      f.write(sample_content)

    expected_sha = hashlib.sha256(sample_content).hexdigest()
    actual_sha = calculate_sha256(sample_file)
    self.assertEqual(expected_sha, actual_sha)

    checksum_file = generate_checksums(self.test_dir, [sample_file])
    self.assertTrue(os.path.exists(checksum_file))

    with open(checksum_file, "r") as f:
      content = f.read()
    self.assertIn(expected_sha, content)
    self.assertIn("sample.txt", content)


if __name__ == '__main__':
  unittest.main()
