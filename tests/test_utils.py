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

import shlex
import subprocess
import sys
from src.torq import create_parser, run
from unittest import mock


def parameterized(items, setup_func=None):
  """
  Function to create a decorator function that parameterizes a test method using
  unittest.subTest given a setup function and a list of items.

  Args:
      items: A list of items to iterate over for the test.
      setup_func: A function to setup subtests.

  Returns:
      A decorator function that runs setup function and subtests for each item.
  """

  def decorator(test_method):

    def decorated_test(self, *args, **kwargs):
      for item in items:
        with self.subTest(item=item):
          if setup_func:
            setup_func(self, item)
          test_method(self, item, *args, **kwargs)

    return decorated_test

  return decorator


def parameterized_profiler(setup_func):
  return parameterized(["perfetto", "simpleperf"], setup_func)


def parameterized_config_builder():
  return parameterized(["pull", "show"])


def create_parser_from_cli(command_string):
  sys.argv = shlex.split(command_string)
  return create_parser()


def parse_cli(command_string):
  parser, error = create_parser_from_cli(command_string)
  if error is not None:
    raise Exception(error.message)
  return parser.parse_args()


def run_cli(command_string):
  sys.argv = shlex.split(command_string)
  run()


def generate_mock_completed_process(stdout_string=b'\n',
                                    stderr_string=b'\n',
                                    returncode=0):

  def check_returncode():
    if returncode != 0:
      raise Exception()

  mock_completed_process = mock.create_autospec(
      subprocess.CompletedProcess,
      instance=True,
      stdout=stdout_string,
      stderr=stderr_string,
      returncode=returncode)
  mock_completed_process.check_returncode = check_returncode
  return mock_completed_process


def generate_adb_devices_result(devices, adb_started=True):
  devices = [device.encode('utf-8') for device in devices]
  stdout_string = b'List of devices attached\n'
  if not adb_started:
    stdout_string = (b'* daemon not running; starting now at tcp:1234\n'
                     b'* daemon started successfully\n') + stdout_string
  if len(devices) > 0:
    stdout_string += b'\tdevice\n'.join(devices) + b'\tdevice\n'
    stdout_string += b'\n'
  return subprocess.CompletedProcess(
      args=['adb', 'devices'], returncode=0, stdout=stdout_string)


def adb_create_user(serial, user_name):
  """Creates a new user on the Android device.

  Args:
    serial: The serial number of the Android device.
    user_name: The name of the user to be created.

  Returns:
    The integer ID of the newly created user.

  Raises:
    RuntimeError: If the adb command fails (e.g. device not found).
    ValueError: If user creation fails on the device (e.g. max users reached)
  """
  command_output = subprocess.run(
      ["adb", "-s", serial, "shell", "pm", "create-user", user_name],
      capture_output=True,
      text=True,
      check=True,
  )

  output_str = command_output.stdout.strip()
  if "Error:" in output_str:
    raise ValueError(
        f"Failed to create user '{user_name}' on device '{serial}':"
        f" {output_str}")

  return int(output_str.split()[-1])


def adb_delete_user(serial, user):
  """Removes a user from the Android device.

  Args:
    serial: The serial number of the Android device.
    user: The integer ID or string representation of the user to be removed.

  Raises:
    RuntimeError: If the adb command fails (e.g. device not found).
    ValueError: If user removal fails on the device
  """
  command_output = subprocess.run(
      ["adb", "-s", serial, "shell", "pm", "remove-user",
       str(user)],
      capture_output=True,
      text=True,
      check=True,
  )

  output_str = command_output.stdout.strip()
  if "Error:" in output_str:
    raise ValueError(
        f"Failed to delete user '{user}' on device '{serial}': {output_str}")


def adb_set_enforce(serial, mode):
  """Sets the SELinux enforcement mode on the Android device.

  Args:
    serial: The serial number of the Android device.
    mode: The mode to set (e.g. 0 for permissive, 1 for enforcing).

  Raises:
    RuntimeError: If the adb command fails (e.g. device not found or permission
      denied).
  """
  subprocess.run(
      ["adb", "-s", serial, "shell", "setenforce",
       str(mode)],
      capture_output=True,
      text=True,
      check=True,
  )
