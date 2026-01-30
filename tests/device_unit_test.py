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

import builtins
import unittest
import os
import subprocess
from unittest import mock
from src.device import AndroidDevice
from src.profiler import ProfilerCommand
from src.shell import AdbShell
from src.utils import ShellExitCodes
from tests.test_utils import generate_adb_devices_result, generate_mock_completed_process

TEST_DEVICE_SERIAL = "test-device-serial"
TEST_DEVICE_SERIAL2 = "test-device-serial2"
TEST_FILE_PATH = "test-file-path"
TEST_STRING_FILE = "test-string-file"
TEST_FAILURE_MSG = "test-failure"
TEST_EXCEPTION = Exception(TEST_FAILURE_MSG)
TEST_USER_ID_1 = 0
TEST_USER_ID_2 = 1
TEST_USER_ID_3 = 2
TEST_PACKAGE_1 = "test-package-1"
TEST_PACKAGE_2 = "test-package-2"
TEST_PROP = "test-prop"
TEST_PROP_VALUE = "test-prop-value"
TEST_PID_OUTPUT = b"8241\n"
BOOT_COMPLETE_OUTPUT = b"1\n"
ANDROID_SDK_VERSION_T = 33


class DeviceUnitTest(unittest.TestCase):

  @staticmethod
  def subprocess_output(first_return_value, polling_return_value):
    # Mocking the return value of a call to adb root and the return values of
    # many followup calls to adb devices
    yield first_return_value
    while True:
      yield polling_return_value

  @staticmethod
  def mock_users(returncode=0):
    return mock.create_autospec(
        subprocess.CompletedProcess,
        instance=True,
        stdout=(b'Users:\n\tUserInfo{%d:Driver:813}'
                b' running\n\tUserInfo{%d:Driver:412}\n' %
                (TEST_USER_ID_1, TEST_USER_ID_2)),
        returncode=returncode)

  @staticmethod
  def mock_packages(returncode=0):
    return mock.create_autospec(
        subprocess.CompletedProcess,
        instance=True,
        stdout=(
            b'package:%b\npackage:%b\n' %
            (TEST_PACKAGE_1.encode("utf-8"), TEST_PACKAGE_2.encode("utf-8"))),
        returncode=returncode)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_devices(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL, TEST_DEVICE_SERIAL2]))

    devices = AdbShell.get_adb_devices()

    self.assertEqual(len(devices), 2)
    self.assertEqual(devices[0], TEST_DEVICE_SERIAL)
    self.assertEqual(devices[1], TEST_DEVICE_SERIAL2)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_devices_and_adb_not_started(
      self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL, TEST_DEVICE_SERIAL2],
                                    False))

    devices = AdbShell.get_adb_devices()

    self.assertEqual(len(devices), 2)
    self.assertEqual(devices[0], TEST_DEVICE_SERIAL)
    self.assertEqual(devices[1], TEST_DEVICE_SERIAL2)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_no_device(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_adb_devices_result([])

    devices = AdbShell.get_adb_devices()

    self.assertEqual(devices, [])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_no_device_and_adb_not_started(
      self, mock_subprocess_run):
    mock_subprocess_run.return_value = (generate_adb_devices_result([], False))

    devices = AdbShell.get_adb_devices()

    self.assertEqual(devices, [])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_command_failure_error(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      AdbShell.get_adb_devices()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_verify_serial_arg_in_devices(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL]))

    error = AdbShell.verify_serial(TEST_DEVICE_SERIAL)

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_verify_serial_arg_not_in_devices_error(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL]))

    error = AdbShell.verify_serial("invalid-device-serial")

    self.assertNotEqual(error, None)
    self.assertEqual(
        error.message,
        "Device with serial invalid-device-serial is not connected.")
    self.assertEqual(error.suggestion, None)

  @mock.patch.dict(
      os.environ, {"ANDROID_SERIAL": TEST_DEVICE_SERIAL}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_default_serial_env_variable_in_devices(self,
                                                      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL]))

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(error, None)
    self.assertEqual(serial, TEST_DEVICE_SERIAL)

  @mock.patch.dict(
      os.environ, {"ANDROID_SERIAL": "invalid-device-serial"}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_default_serial_env_variable_not_in_devices_error(
      self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL]))

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(serial, None)
    self.assertNotEqual(error, None)
    self.assertEqual(error.message, ("Device with serial invalid-device-serial"
                                     " is set as environment variable,"
                                     " ANDROID_SERIAL, but is not connected."))
    self.assertEqual(error.suggestion, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_default_serial_adb_devices_command_fails_error(
      self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      AdbShell.get_default_serial()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_default_serial_no_devices_connected_error(
      self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_adb_devices_result([])

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(serial, None)
    self.assertNotEqual(error, None)
    self.assertEqual(error.message, "There are currently no devices connected.")
    self.assertEqual(error.suggestion, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_default_serial_no_devices_connected_adb_not_started_error(
      self, mock_subprocess_run):
    mock_subprocess_run.return_value = (generate_adb_devices_result([], False))

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(serial, None)
    self.assertNotEqual(error, None)
    self.assertEqual(error.message, "There are currently no devices connected.")
    self.assertEqual(error.suggestion, None)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_default_serial_only_one_device(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL]))

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(error, None)
    self.assertEqual(serial, TEST_DEVICE_SERIAL)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_get_default_serial_multiple_devices_select_first(
      self, mock_input, mock_subprocess_run):
    mock_input.return_value = "0"
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL, TEST_DEVICE_SERIAL2]))

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(error, None)
    self.assertEqual(serial, TEST_DEVICE_SERIAL)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_get_default_serial_multiple_devices_select_second(
      self, mock_input, mock_subprocess_run):
    mock_input.return_value = "1"
    mock_subprocess_run.return_value = (
        generate_adb_devices_result([TEST_DEVICE_SERIAL, TEST_DEVICE_SERIAL2]))

    serial, error = AdbShell.get_default_serial()

    self.assertEqual(error, None)
    self.assertEqual(serial, TEST_DEVICE_SERIAL2)

  @mock.patch("src.device.poll_is_task_completed", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_success(self, mock_subprocess_run,
                               mock_poll_is_task_completed):
    mock_subprocess_run.side_effect = [
        generate_mock_completed_process(),
        generate_adb_devices_result([TEST_DEVICE_SERIAL])
    ]
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    mock_poll_is_task_completed.return_value = True

    # No exception is expected to be thrown
    device.root_device()

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.root_device()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch("src.device.poll_is_task_completed", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_times_out_error(self, mock_subprocess_run,
                                       mock_poll_is_task_completed):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    mock_poll_is_task_completed.return_value = False

    with self.assertRaises(Exception) as e:
      device.root_device()

    self.assertEqual(
        str(e.exception),
        ("Device with serial %s took too long to"
         " reconnect after being rooted." % TEST_DEVICE_SERIAL))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_and_adb_devices_fails_error(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = [
        generate_mock_completed_process(), TEST_EXCEPTION
    ]
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.root_device()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_remove_file_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.remove_file(TEST_FILE_PATH)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_remove_file_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.remove_file(TEST_FILE_PATH)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_start_perfetto_trace_success(self, mock_subprocess_popen):
    # Mocking the return value of subprocess.Popen to ensure it's
    # not modified and returned by AndroidDevice.start_perfetto_trace
    mock_subprocess_popen.return_value = mock.Mock()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    mock_process = device.start_perfetto_trace("")

    # No exception is expected to be thrown
    self.assertEqual(mock_process, mock_subprocess_popen.return_value)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_start_perfetto_trace_failure(self, mock_subprocess_popen):
    mock_subprocess_popen.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.start_perfetto_trace("")

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_start_simpleperf_trace_success(self, mock_subprocess_popen):
    # Mocking the return value of subprocess.Popen to ensure it's
    # not modified and returned by AndroidDevice.start_simpleperf_trace
    mock_subprocess_popen.return_value = mock.Mock()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    command = ProfilerCommand("profiler", "custom", None, None, 10000, None,
                              None, ["cpu-cycles"], None, None, None, None,
                              None, None, None, None, None, None, None, None,
                              None)
    mock_process = device.start_simpleperf_trace(command)

    # No exception is expected to be thrown
    self.assertEqual(mock_process, mock_subprocess_popen.return_value)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_start_simpleperf_trace_failure(self, mock_subprocess_popen):
    mock_subprocess_popen.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    command = ProfilerCommand("profiler", "custom", None, None, 10000, None,
                              None, ["cpu-cycles"], None, None, None, None,
                              None, None, None, None, None, None, None, None,
                              None)

    with self.assertRaises(Exception) as e:
      device.start_simpleperf_trace(command)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_pull_file_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    self.assertTrue(device.pull_file(TEST_FILE_PATH, TEST_FILE_PATH))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_pull_file_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.pull_file(TEST_FILE_PATH, TEST_FILE_PATH)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_all_users_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = self.mock_users()

    users = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL)).get_all_users()

    self.assertEqual(users, [TEST_USER_ID_1, TEST_USER_ID_2])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_all_users_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.get_all_users()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_user_exists_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = self.mock_users()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    error = device.user_exists(TEST_USER_ID_1)

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_user_exists_and_user_does_not_exist_failure(self,
                                                       mock_subprocess_run):
    mock_subprocess_run.return_value = self.mock_users()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    error = device.user_exists(TEST_USER_ID_3)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message,
                     ("User ID %s does not exist on device with"
                      " serial %s." % (TEST_USER_ID_3, TEST_DEVICE_SERIAL)))
    self.assertEqual(error.suggestion,
                     ("Select from one of the following user IDs on device with"
                      " serial %s: %s, %s" %
                      (TEST_DEVICE_SERIAL, TEST_USER_ID_1, TEST_USER_ID_2)))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_user_exists_and_get_all_users_fails_error(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.user_exists(TEST_USER_ID_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_current_user_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process(
        stdout_string=b'%d\n' % TEST_USER_ID_1)
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    user = device.get_current_user()

    self.assertEqual(user, TEST_USER_ID_1)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_current_user_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.get_current_user()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_perform_user_switch_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.perform_user_switch(TEST_USER_ID_1)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_perform_user_switch_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.perform_user_switch(TEST_USER_ID_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_write_to_file_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.write_to_file(TEST_FILE_PATH, TEST_STRING_FILE)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_write_to_file_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.write_to_file(TEST_FILE_PATH, TEST_STRING_FILE)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_set_prop_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.set_prop(TEST_PROP, TEST_PROP_VALUE)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_set_prop_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.set_prop(TEST_PROP, TEST_PROP_VALUE)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch("src.device.poll_is_task_completed", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_reboot_success(self, mock_subprocess_run,
                          mock_poll_is_task_completed):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    mock_poll_is_task_completed.return_value = True

    # No exception is expected to be thrown
    device.reboot()

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_reboot_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.reboot()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_wait_for_device_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.wait_for_device()

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_wait_for_device_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.wait_for_device()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_is_boot_completed_and_is_completed(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(BOOT_COMPLETE_OUTPUT))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    is_completed = device.is_boot_completed()

    self.assertEqual(is_completed, True)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_is_boot_completed_and_is_not_completed(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    is_completed = device.is_boot_completed()

    self.assertFalse(is_completed)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_is_boot_completed_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.is_boot_completed()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch("src.device.poll_is_task_completed", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_wait_for_boot_to_complete_success(self, mock_subprocess_run,
                                             mock_poll_is_task_completed):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(BOOT_COMPLETE_OUTPUT))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    mock_poll_is_task_completed.return_value = True

    # No exception is expected to be thrown
    device.wait_for_boot_to_complete()

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_wait_for_boot_to_complete_and_is_boot_completed_fails_error(
      self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.wait_for_boot_to_complete()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch("src.device.poll_is_task_completed", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_wait_for_boot_to_complete_times_out_error(
      self, mock_subprocess_run, mock_poll_is_task_completed):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))
    mock_poll_is_task_completed.return_value = False

    with self.assertRaises(Exception) as e:
      device.wait_for_boot_to_complete()

    self.assertEqual(
        str(e.exception), ("Device with serial %s took too long to"
                           " finish rebooting." % TEST_DEVICE_SERIAL))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_packages_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = self.mock_packages()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    packages = device.get_packages()

    self.assertEqual(packages, [TEST_PACKAGE_1, TEST_PACKAGE_2])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_packages_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.get_packages()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_pid_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process(
        TEST_PID_OUTPUT)
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    process_id = device.get_pid(TEST_PACKAGE_1)

    self.assertEqual(process_id, "8241")

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_pid_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.get_pid(TEST_PACKAGE_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_package_running(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process(
        TEST_PID_OUTPUT)
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    is_running = device.is_process_running(TEST_PACKAGE_1)

    self.assertEqual(is_running, True)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_package_not_running(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    is_running = device.is_process_running(TEST_PACKAGE_1)

    self.assertFalse(is_running)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_package_running_and_get_pid_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.is_process_running(TEST_PACKAGE_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_start_package_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    error = device.start_package(TEST_PACKAGE_1)

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_start_package_fails_with_service_app(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process(
        stderr_string=b'%s\n' % TEST_FAILURE_MSG.encode("utf-8"))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    error = device.start_package(TEST_PACKAGE_1)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message,
                     ("Cannot start package %s on device with"
                      " serial %s because %s is a service"
                      " package, which doesn't implement a MAIN"
                      " activity." %
                      (TEST_PACKAGE_1, TEST_DEVICE_SERIAL, TEST_PACKAGE_1)))
    self.assertEqual(error.suggestion, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_start_package_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.start_package(TEST_PACKAGE_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_kill_process_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process(
        TEST_PID_OUTPUT)
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.kill_process(TEST_PACKAGE_1)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_kill_process_and_get_pid_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.kill_process(TEST_PACKAGE_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_kill_process_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = [
        generate_mock_completed_process(TEST_PID_OUTPUT), TEST_EXCEPTION
    ]
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.kill_process(TEST_PACKAGE_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_force_stop_package_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    # No exception is expected to be thrown
    device.force_stop_package(TEST_PACKAGE_1)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_force_stop_package_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.force_stop_package(TEST_PACKAGE_1)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_prop_success(self, mock_subprocess_run):
    test_prop_value = ANDROID_SDK_VERSION_T
    mock_subprocess_run.return_value = generate_mock_completed_process(
        stdout_string=b'%d\n' % test_prop_value)
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    prop_value = int(device.get_prop(TEST_PROP))

    self.assertEqual(prop_value, test_prop_value)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_prop_package_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.get_prop(TEST_PROP)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_android_sdk_version_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process(
        stdout_string=b'%d\n' % ANDROID_SDK_VERSION_T)
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    prop_value = device.get_android_sdk_version()

    self.assertEqual(prop_value, ANDROID_SDK_VERSION_T)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_android_sdk_version_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    with self.assertRaises(Exception) as e:
      device.get_android_sdk_version()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_simpleperf_event_exists_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(b'List of software events:\n  '
                                        b'alignment-faults\n  '
                                        b'context-switches\n  '
                                        b'cpu-clock\n  '
                                        b'cpu-migrations\n  '
                                        b'emulation-faults\n  '
                                        b'major-faults\n  '
                                        b'minor-faults\n  page-faults\n  '
                                        b'task-clock'))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    events = ["cpu-clock", "minor-faults"]
    # No exception is expected to be thrown
    error = device.simpleperf_event_exists(events)

    self.assertEqual(error, None)
    # Check that the list passed to the function is unchanged
    self.assertEqual(events, ["cpu-clock", "minor-faults"])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_simpleperf_event_exists_failure(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(b'List of software events:\n  '
                                        b'alignment-faults\n  '
                                        b'context-switches\n  '
                                        b'cpu-clock\n  '
                                        b'cpu-migrations\n  '
                                        b'emulation-faults\n  '
                                        b'major-faults\n  '
                                        b'minor-faults\n  page-faults\n  '
                                        b'task-clock'))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    error = device.simpleperf_event_exists(
        ["cpu-clock", "minor-faults", "List"])

    self.assertEqual(
        error.message, "The following simpleperf event(s) are "
        "invalid: ['List'].")
    self.assertEqual(
        error.suggestion, "Run adb shell simpleperf list to"
        " see valid simpleperf events.")

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_simpleperf_not_installed(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(
            returncode=ShellExitCodes.EX_FAILURE.value))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    error = device.simpleperf_event_exists(
        ["cpu-clock", "minor-faults", "List"])

    self.assertEqual(error.message, "Simpleperf was not found in the device.")
    self.assertEqual(error.suggestion,
                     "Push the simpleperf binary to the device.")

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_file_exists_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    self.assertTrue(device.file_exists("perfetto"))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_file_exists_failure(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(
            returncode=ShellExitCodes.EX_FAILURE.value))
    device = AndroidDevice(AdbShell(TEST_DEVICE_SERIAL))

    self.assertFalse(device.file_exists("perfetto"))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_adb_exists(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_mock_completed_process(
            returncode=ShellExitCodes.EX_NOTFOUND.value))

    self.assertFalse(AdbShell.adb_exists())


if __name__ == '__main__':
  unittest.main()
