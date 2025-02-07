#
# Copyright (C) 2024 The Android Open Source Project
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

import unittest
import subprocess
import os
from unittest import mock
from src.device import AdbDevice
from src.utils import convert_simpleperf_to_gecko


class UtilsUnitTest(unittest.TestCase):

  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_success(self, mock_exists,
      mock_subprocess_run):
    mock_exists.return_value = True
    mock_subprocess_run.return_value = None

    # No exception is expected to be thrown
    convert_simpleperf_to_gecko("/scripts", "/path/file.data",
                                "/path/file.json", "/symbols")

  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_failure(self, mock_exists,
      mock_subprocess_run):
    mock_exists.return_value = False
    mock_subprocess_run.return_value = None

    with self.assertRaises(Exception) as e:
      convert_simpleperf_to_gecko("/scripts", "/path/file.data",
                                  "/path/file.json", "/symbols")

      self.assertEqual(str(e.exception), "Gecko file was not created.")


if __name__ == '__main__':
  unittest.main()
