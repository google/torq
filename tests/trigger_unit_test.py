#
# Copyright (C) 2025 The Android Open Source Project
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

import os
import time
import unittest

from src.base import ANDROID_SDK_VERSION_T, PERFETTO_VERSION_WITH_MULTI_VM_SUPPORT
from src.device import AdbDevice
from src.profiler import PERFETTO_TRACE_FILE
from tests.test_utils import parameterized, run_cli
from unittest import mock
from unittest.mock import ANY

TEST_SERIAL = "test-serial"
TEST_TRIGGER_NAMES = [
    "team.package.test-trigger-name", "team2.package2.test-trigger-name2"
]
TEST_TRIGGER_DUR_MS = 10000
TEST_TRIGGER_STOP_DELAY_MS = 1000
TEST_MULTIPLE_TRIGGER_STOP_DELAY_MS = ["1000", "2000"]
TEST_TRIGGER_MODE = "stop"


class TriggerSubcommandUnitTest(unittest.TestCase):

  @mock.patch('src.torq.AdbDevice', autospec=True)
  def test_trigger_names(self, mock_device):
    self.mock_device = mock_device.return_value
    self.mock_device.check_device_connection.return_value = None

    run_cli(f"torq trigger {TEST_TRIGGER_NAMES[0]}")

    self.mock_device.trigger_perfetto.assert_called_with(TEST_TRIGGER_NAMES[0])


class ProfilerTriggerUnitTest(unittest.TestCase):

  def setUp(self):
    self.mock_device = mock.create_autospec(
        AdbDevice, instance=True, serial=TEST_SERIAL)
    self.mock_device.check_device_connection.return_value = None
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)
    self.mock_device.get_perfetto_version.return_value = PERFETTO_VERSION_WITH_MULTI_VM_SUPPORT
    self.mock_device.create_directory.return_value = None
    self.mock_device.remove_file.return_value = False
    self.mock_device.pull_file.return_value = False
    self.mock_sleep_patcher = mock.patch.object(
        time, 'sleep', return_value=None)
    self.mock_sleep_patcher.start()

  def tearDown(self):
    self.mock_sleep_patcher.stop()

  @parameterized([""] + [
      f"--trigger-stop-delay-ms {delays}" for delays in [
          TEST_TRIGGER_STOP_DELAY_MS, ' '.join(
              TEST_MULTIPLE_TRIGGER_STOP_DELAY_MS)
      ]
  ] + [f"--trigger-mode {mode}" for mode in ["start", "clone", "stop"]])
  @mock.patch('src.torq.AdbDevice', autospec=True)
  def test_trigger_names(self, trigger_args, mock_device_creator):
    mock_device_creator.return_value = self.mock_device

    with (mock.patch("src.profiler.open_trace", autospec=True) as
          mock_open_trace):
      mock_open_trace.return_value = None
      run_cli(
          f"torq --trigger-names {' '.join(TEST_TRIGGER_NAMES)} {trigger_args}")

    mock_device_creator.assert_called_once_with(None)

    self.mock_device.pull_file.assert_called_with(
        PERFETTO_TRACE_FILE + (".0" if "clone" in trigger_args else ""), ANY)

    self.mock_device.start_perfetto_trace.assert_called()

  @mock.patch('src.torq.AdbDevice', autospec=True)
  def test_trigger_names_incorrect_stop_delays(self, mock_device_creator):
    mock_device_creator.return_value = self.mock_device

    with (mock.patch("src.profiler.open_trace", autospec=True) as
          mock_open_trace):
      mock_open_trace.return_value = None
      run_cli(f"torq --trigger-names {' '.join(TEST_TRIGGER_NAMES)}"
              f" --trigger-stop-delay-ms"
              f" {' '.join(TEST_MULTIPLE_TRIGGER_STOP_DELAY_MS)} 3000")

    mock_device_creator.assert_not_called()

    self.mock_device.pull_file.assert_not_called()

    self.mock_device.start_perfetto_trace.assert_not_called()


if __name__ == '__main__':
  unittest.main()
