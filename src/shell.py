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

import os
import subprocess
import sys
from abc import ABC, abstractmethod
from .base import ValidationError
from .handle_input import HandleInput
from .utils import poll_is_task_completed, POLLING_INTERVAL_SECS, run_subprocess, ShellExitCodes

WAIT_FOR_DEVICE_TIME_OUT_SECS = 5


class Shell(ABC):
  """
  Abstract base class for the communication channel to a device
  """

  @abstractmethod
  def id(self):
    raise NotImplementedError

  @abstractmethod
  def popen(self, args):
    raise NotImplementedError

  @abstractmethod
  def run(self,
          args,
          ignore_returncodes=[],
          stdin=None,
          input=None,
          stdout=None,
          stderr=None,
          capture_output=False,
          shell=False,
          cwd=None,
          timeout=None,
          encoding=None,
          errors=None,
          text=None,
          env=None,
          universal_newlines=None):
    raise NotImplementedError

  @abstractmethod
  def wait_for_device(self):
    raise NotImplementedError


class AdbShell(Shell):

  @staticmethod
  def adb_exists():
    # adb returns 1 when it runs, so ignore this error code.
    return not run_subprocess(
        "adb",
        capture_output=True,
        shell=True,
        ignore_returncodes=[
            ShellExitCodes.EX_FAILURE, ShellExitCodes.EX_NOTFOUND
        ]).returncode == ShellExitCodes.EX_NOTFOUND

  @staticmethod
  def get_adb_devices():
    """
    Returns a list of devices connected to the adb bridge.
    The output of the command 'adb devices' is expected to be of the form:
    List of devices attached
    SOMEDEVICE1234    device
    device2:5678    device
    """
    command_output = run_subprocess(["adb", "devices"], capture_output=True)
    output_lines = command_output.stdout.decode("utf-8").split("\n")
    devices = []
    for line in output_lines[:-2]:
      if line[0] == "*" or line == "List of devices attached":
        continue
      words_in_line = line.split('\t')
      if words_in_line[1] == "device":
        devices.append(words_in_line[0])
    return devices

  @staticmethod
  def get_default_serial():
    if not AdbShell.adb_exists():
      return None, ValidationError("adb could not be found on the host device.",
                                   None)
    devices = AdbShell.get_adb_devices()
    if len(devices) == 0:
      return None, ValidationError("There are currently no devices connected.",
                                   None)
    if "ANDROID_SERIAL" in os.environ:
      if os.environ["ANDROID_SERIAL"] not in devices:
        return None, ValidationError(
            ("Device with serial %s is set as environment"
             " variable, ANDROID_SERIAL, but is not"
             " connected." % os.environ["ANDROID_SERIAL"]), None)
      serial = os.environ["ANDROID_SERIAL"]
    elif len(devices) == 1:
      serial = devices[0]
    else:
      options = ""
      choices = {}
      for i, device in enumerate(devices):
        options += ("%d: torq --serial %s %s\n\t" %
                    (i, device, " ".join(sys.argv[1:])))
        # Lambdas are bound to local scope, so assign var d to prevent
        # future values of device from overriding the current value we want
        choices[str(i)] = lambda d=device: d
      # Remove last \t
      options = options[:-1]
      chosen_serial = (
          HandleInput(
              "There is more than one device currently "
              "connected. Press the corresponding number "
              "for the following options to choose the "
              "device you want to use.\n\t%sSelect "
              "device[0-%d]: " % (options, len(devices) - 1),
              "Please select a valid option.", choices).handle_input())
      if isinstance(chosen_serial, ValidationError):
        return None, chosen_serial
      print("Using device with serial %s" % chosen_serial)
      serial = chosen_serial
    return serial, None

  @staticmethod
  def verify_serial(serial):
    assert serial is not None, "serial cannot be None"
    if not AdbShell.adb_exists():
      return ValidationError("adb could not be found on the host device.", None)
    devices = AdbShell.get_adb_devices()
    if len(devices) == 0:
      return ValidationError("There are currently no devices connected.", None)
    if serial not in devices:
      return ValidationError(
          ("Device with serial %s is not connected." % serial), None)
    return None

  def __init__(self, serial):
    self.serial = serial

  def id(self):
    return self.serial

  def popen(self, args):
    is_list = isinstance(args, list)
    prefix = ["adb", "-s", self.serial]
    cmd = prefix + args if is_list else f"{' '.join(prefix)} {args}"
    return subprocess.Popen(cmd, shell=(not is_list))

  def run(self,
          args,
          ignore_returncodes=[],
          stdin=None,
          input=None,
          stdout=None,
          stderr=None,
          capture_output=False,
          shell=False,
          cwd=None,
          timeout=None,
          encoding=None,
          errors=None,
          text=None,
          env=None,
          universal_newlines=None):
    return run_subprocess(["adb", "-s", self.serial] + args, ignore_returncodes,
                          stdin, input, stdout, stderr, capture_output, shell,
                          cwd, timeout, encoding, errors, text, env,
                          universal_newlines)

  def wait_for_device(self):
    return poll_is_task_completed(
        WAIT_FOR_DEVICE_TIME_OUT_SECS, POLLING_INTERVAL_SECS,
        lambda: self.serial in AdbShell.get_adb_devices())
