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
import os
import subprocess
from unittest import mock
from device import AdbDevice

TEST_DEVICE_SERIAL = "test-device-serial"
TEST_DEVICE_SERIAL2 = "test-device-serial2"
TEST_FILE_PATH = "test-file-path"
TEST_FAILURE_MSG = "Test failure."
TEST_EXCEPTION = Exception(TEST_FAILURE_MSG)


class DeviceUnitTest(unittest.TestCase):

  @staticmethod
  def generate_adb_devices_result(devices, adb_started=True):
    devices = [device.encode('utf-8') for device in devices]
    stdout_string = b'List of devices attached\n'
    if not adb_started:
      stdout_string = (b'* daemon not running; starting now at tcp:1234\n'
                       b'* daemon started successfully\n') + stdout_string
    if len(devices) > 0:
      stdout_string += b'\tdevice\n'.join(devices) + b'\tdevice\n'
      stdout_string += b'\n'
    return subprocess.CompletedProcess(args=['adb', 'devices'], returncode=0,
                                       stdout=stdout_string)

  @staticmethod
  def generate_mock_completed_process():
    return mock.create_autospec(subprocess.CompletedProcess, instance=True)

  @staticmethod
  def subprocess_output(first_return_value, polling_return_value):
    # Mocking the return value of a call to adb root and the return values of
    # many followup calls to adb devices
    yield first_return_value
    while True:
      yield polling_return_value

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_devices(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL,
                                          TEST_DEVICE_SERIAL2]))
    adbDevice = AdbDevice(None)

    devices = adbDevice.get_adb_devices()

    self.assertEqual(len(devices), 2)
    self.assertEqual(devices[0], TEST_DEVICE_SERIAL)
    self.assertEqual(devices[1], TEST_DEVICE_SERIAL2)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_devices_and_adb_not_started(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL,
                                          TEST_DEVICE_SERIAL2], False))
    adbDevice = AdbDevice(None)

    devices = adbDevice.get_adb_devices()

    self.assertEqual(len(devices), 2)
    self.assertEqual(devices[0], TEST_DEVICE_SERIAL)
    self.assertEqual(devices[1], TEST_DEVICE_SERIAL2)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_no_device(self, mock_subprocess_run):
    mock_subprocess_run.return_value = self.generate_adb_devices_result([])
    adbDevice = AdbDevice(None)

    devices = adbDevice.get_adb_devices()

    self.assertEqual(devices, [])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_returns_no_device_and_adb_not_started(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([], False))
    adbDevice = AdbDevice(None)

    devices = adbDevice.get_adb_devices()

    self.assertEqual(devices, [])

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_get_adb_devices_command_failure_error(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    adbDevice = AdbDevice(None)

    with self.assertRaises(Exception) as e:
      adbDevice.get_adb_devices()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_serial_arg_in_devices(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL]))
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    error = adbDevice.check_device_connection()

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_serial_arg_not_in_devices_error(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL]))
    invalid_device_serial = "invalid-device-serial"
    adbDevice = AdbDevice(invalid_device_serial)

    error = adbDevice.check_device_connection()

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, ("Device with serial %s is not connected."
                                     % invalid_device_serial))
    self.assertEqual(error.suggestion, None)

  @mock.patch.dict(os.environ, {"ANDROID_SERIAL": TEST_DEVICE_SERIAL},
                   clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_env_variable_in_devices(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL]))
    adbDevice = AdbDevice(None)

    error = adbDevice.check_device_connection()

    self.assertEqual(error, None)
    self.assertEqual(adbDevice.serial, TEST_DEVICE_SERIAL)

  @mock.patch.dict(os.environ, {"ANDROID_SERIAL": "invalid-device-serial"},
                   clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_env_variable_not_in_devices_error(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL]))
    adbDevice = AdbDevice(None)

    error = adbDevice.check_device_connection()

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, ("Device with serial invalid-device-serial"
                                     " is set as environment variable,"
                                     " ANDROID_SERIAL, but is not connected."))
    self.assertEqual(error.suggestion, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_adb_devices_command_fails_error(self,
      mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    adbDevice = AdbDevice(None)

    with self.assertRaises(Exception) as e:
      adbDevice.check_device_connection()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_no_devices_connected_error(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (self.generate_adb_devices_result([]))
    adbDevice = AdbDevice(None)

    error = adbDevice.check_device_connection()

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, "There are currently no devices connected.")
    self.assertEqual(error.suggestion, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_no_devices_connected_adb_not_started_error(
      self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([], False))
    adbDevice = AdbDevice(None)

    error = adbDevice.check_device_connection()

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, "There are currently no devices connected.")
    self.assertEqual(error.suggestion, None)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_only_one_device(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL]))
    adbDevice = AdbDevice(None)

    error = adbDevice.check_device_connection()

    self.assertEqual(error, None)
    self.assertEqual(adbDevice.serial, TEST_DEVICE_SERIAL)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_check_device_connection_multiple_devices_error(self,
      mock_subprocess_run):
    mock_subprocess_run.return_value = (
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL,
                                          TEST_DEVICE_SERIAL2]))
    adbDevice = AdbDevice(None)

    error = adbDevice.check_device_connection()

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, ("There is more than one device currently"
                                     " connected."))
    self.assertEqual(error.suggestion, ("Run one of the following commands to"
                                        " choose one of the connected devices:"
                                        "\n\t torq --serial %s"
                                        "\n\t torq --serial %s"
                                        % (TEST_DEVICE_SERIAL,
                                           TEST_DEVICE_SERIAL2)))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_success(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = [
        self.generate_mock_completed_process(),
        self.generate_adb_devices_result([TEST_DEVICE_SERIAL])]
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    # No exception is expected to be thrown
    adbDevice.root_device()

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    with self.assertRaises(Exception) as e:
      adbDevice.root_device()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_times_out_error(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = lambda args, capture_output=True: (
      next(self.subprocess_output(self.generate_adb_devices_result([]),
                                  self.generate_mock_completed_process())))
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    with self.assertRaises(Exception) as e:
      adbDevice.root_device()

    self.assertEqual(str(e.exception), ("Device with serial %s took too long to"
                                        " reconnect after being rooted."
                                        % TEST_DEVICE_SERIAL))

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_root_device_and_adb_devices_fails_error(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = [self.generate_mock_completed_process(),
                                       TEST_EXCEPTION]
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    with self.assertRaises(Exception) as e:
      adbDevice.root_device()

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_remove_file_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = self.generate_mock_completed_process()
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    # No exception is expected to be thrown
    adbDevice.remove_file(TEST_FILE_PATH)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_remove_file_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    with self.assertRaises(Exception) as e:
      adbDevice.remove_file(TEST_FILE_PATH)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_start_perfetto_trace_success(self, mock_subprocess_popen):
    # Mocking the return value of subprocess.Popen to ensure it's
    # not modified and returned by AdbDevice.start_perfetto_trace
    mock_subprocess_popen.return_value = mock.Mock()
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    mock_process = adbDevice.start_perfetto_trace(None)

    # No exception is expected to be thrown
    self.assertEqual(mock_process, mock_subprocess_popen.return_value)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_start_perfetto_trace_failure(self, mock_subprocess_popen):
    mock_subprocess_popen.side_effect = TEST_EXCEPTION
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    with self.assertRaises(Exception) as e:
      adbDevice.start_perfetto_trace(None)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_pull_file_success(self, mock_subprocess_run):
    mock_subprocess_run.return_value = self.generate_mock_completed_process()
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    # No exception is expected to be thrown
    adbDevice.pull_file(TEST_FILE_PATH, TEST_FILE_PATH)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_pull_file_failure(self, mock_subprocess_run):
    mock_subprocess_run.side_effect = TEST_EXCEPTION
    adbDevice = AdbDevice(TEST_DEVICE_SERIAL)

    with self.assertRaises(Exception) as e:
      adbDevice.pull_file(TEST_FILE_PATH, TEST_FILE_PATH)

    self.assertEqual(str(e.exception), TEST_FAILURE_MSG)


if __name__ == '__main__':
  unittest.main()
