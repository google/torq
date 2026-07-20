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

import enum
import os
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from urllib.parse import urlsplit
from .base import ValidationError
from .handle_input import HandleInput
from .uri import URIScheme
from .utils import poll_is_task_completed, POLLING_INTERVAL_SECS, run_subprocess, ShellExitCodes

WAIT_FOR_DEVICE_TIME_OUT_SECS = 5


@enum.unique
class OsCodes(enum.IntEnum):
  OS_UNKNOWN = 0
  OS_ANDROID = 1
  OS_QNX = 2

  @classmethod
  def get_supported_os_names(cls):
    return [
        os.name.removeprefix("OS_").capitalize()
        for os in cls
        if os != cls.OS_UNKNOWN
    ]


def get_shell(serial):
  parsed_serial = urlsplit(serial)
  scheme = parsed_serial.scheme
  if scheme == URIScheme.SSH:
    return SshShell(parsed_serial), None
  elif scheme == URIScheme.TTY:
    return TtyShell(parsed_serial), None
  elif scheme in URIScheme._value2member_map_:
    return None, ValidationError(
        f"The URI scheme '{scheme}' is not supported.",
        "The only supported URI schemes are 'ssh' and 'tty'.")
  else:
    error = AdbShell.verify_serial(serial)
    if error:
      return None, error

  return AdbShell(serial), None


class Process(ABC):
  """
  Abstract class representing a process
  """

  @abstractmethod
  def is_running(self):
    raise NotImplementedError


class ShellProcess(Process):

  def __init__(self, process):
    self.process = process

  def is_running(self):
    return self.process.poll() is None


class Shell(ABC):
  """
  Abstract base class for the communication channel to a device
  """

  @abstractmethod
  def id(self):
    raise NotImplementedError

  @abstractmethod
  def get_os(self):
    raise NotImplementedError

  @abstractmethod
  def popen(self, args, stdout=None, stderr=None):
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

  def get_os(self):
    return OsCodes.OS_ANDROID

  def popen(self, args, stdout=None, stderr=None):
    is_list = isinstance(args, list)
    prefix = ["adb", "-s", self.serial]
    cmd = prefix + args if is_list else f"{' '.join(prefix)} {args}"
    return ShellProcess(
        subprocess.Popen(
            cmd, shell=(not is_list), stdout=stdout, stderr=stderr))

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

  def wait_for_device(self, timeout=WAIT_FOR_DEVICE_TIME_OUT_SECS):
    return poll_is_task_completed(
        timeout, POLLING_INTERVAL_SECS,
        lambda: self.serial in AdbShell.get_adb_devices())


class SshShell(Shell):

  def __init__(self, uri):
    self.uri = uri
    self.host = self.uri.hostname
    if self.uri.username:
      self.host = f"{self.uri.username}@{self.host}"

    self.base_cmd = ["ssh", self.host]
    self.scp_base_cmd = ["scp"]
    if self.uri.port:
      self.base_cmd.extend(["-p", str(self.uri.port)])
      self.scp_base_cmd.extend(["-P", str(self.uri.port)])

  def id(self):
    return self.uri.geturl()

  def get_os(self):
    result = self.run(["PATH=$PATH:/ifs/bin:/mnt/bin; uname"],
                      capture_output=True,
                      ignore_returncodes=[
                          ShellExitCodes.EX_FAILURE, ShellExitCodes.EX_NOTFOUND
                      ])
    if result.returncode != 0:
      raise Exception(
          f"SshShell: failed to get the os: error: {result.returncode}")

    os_name = result.stdout.decode("utf-8").strip().lower()
    if os_name == "qnx":
      return OsCodes.OS_QNX

    return OsCodes.OS_UNKNOWN

  def popen(self, args, stdout=None, stderr=None):
    ssh_cmd = self.base_cmd.copy()
    if isinstance(args, list):
      ssh_cmd.extend(args)
    else:
      ssh_cmd.append(args)
    return ShellProcess(subprocess.Popen(ssh_cmd, stdout=stdout, stderr=stderr))

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
    return run_subprocess(self.base_cmd + args, ignore_returncodes, stdin,
                          input, stdout, stderr, capture_output, shell, cwd,
                          timeout, encoding, errors, text, env,
                          universal_newlines)

  def wait_for_device(self):
    raise NotImplementedError

  def pull_file(self, filepath, host_file):
    scp_cmd = self.scp_base_cmd + [f"{self.host}:{filepath}", host_file]
    output = run_subprocess(
        scp_cmd,
        capture_output=True,
        ignore_returncodes=[ShellExitCodes.EX_FAILURE])
    return not output.returncode


class TtyShell(Shell):

  def __init__(self, uri):
    self.uri = uri
    # For tty:///dev/ttyUSB0, netloc is empty and path is /dev/ttyUSB0
    # For tty://dev/ttyUSB0, netloc is dev and path is /ttyUSB0
    self.tty_device = self.uri.netloc + self.uri.path
    self.base_cmd = ["torq-serial", "-d", self.tty_device, "-c"]
    self.os = None

  def id(self):
    return self.tty_device

  def get_os(self):
    if self.os is not None:
      return self.os

    result = self.run(["uname"],
                      capture_output=True,
                      ignore_returncodes=[
                          ShellExitCodes.EX_FAILURE, ShellExitCodes.EX_NOTFOUND
                      ])
    if result.returncode != 0:
      raise Exception(
          f"TtyShell: failed to get the OS (exitcode: {result.returncode}):"
          f"{result.stderr.decode('utf-8')}")

    os_name = result.stdout.decode("utf-8").strip().split(
        "\n")[0].strip().lower()
    if os_name == "qnx":
      self.os = OsCodes.OS_QNX
    else:
      self.os = OsCodes.OS_UNKNOWN

    return self.os

  def popen(self, args, stdout=None, stderr=None):
    assert isinstance(args, str), "args must be a string"
    # Given TTY is a one channel communication protocol, popen commands need
    # to be pushed to the background so they don't block the rest of the
    # communication with the TTY device.
    # We need to insert the '&' before the first newline/carriage return
    # to correctly background multi-line commands.
    newline_idx = next((i for i, char in enumerate(args) if char in '\n\r'), -1)
    if newline_idx != -1:
      args = args[:newline_idx] + " &" + args[newline_idx:]
    else:
      args += " &"
    # We run the command and then fetch the PID ($!)
    self.run([args], stdout=stdout, stderr=stderr)

    output = self.run(["echo $!"],
                      capture_output=True,
                      ignore_returncodes=[
                          ShellExitCodes.EX_FAILURE, ShellExitCodes.EX_NOTFOUND
                      ]).stdout.decode("utf-8").strip()
    pid = None
    for line in reversed(output.splitlines()):
      line = line.strip()
      if line.isdigit():
        pid = line
        break

    if pid is None:
      raise Exception(
          f"TtyShell: failed to capture remote PID for Popen process")

    return self.TtyProcess(self, pid)

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
    return run_subprocess(self.base_cmd + args, ignore_returncodes, stdin,
                          input, stdout, stderr, capture_output, shell, cwd,
                          timeout, encoding, errors, text, env,
                          universal_newlines)

  def wait_for_device(self):
    raise NotImplementedError

  def pull_file(self, filepath, host_file):
    with tempfile.NamedTemporaryFile() as uuencoded_file:
      # Since base64 binary isn't supported in QNX SDP 7.1, we will use
      # uuencode instead for binary file transmission
      self.run([f"uuencode {filepath} /dev/stdout"], stdout=uuencoded_file)
      # Decode on the host machine
      output = run_subprocess(
          ["uudecode", "-o", host_file, uuencoded_file.name],
          capture_output=True)

      return output.returncode == 0

  class TtyProcess(Process):

    def __init__(self, shell, pid):
      self.shell = shell
      self.pid = pid

    def is_running(self):
      if self.shell.get_os() == OsCodes.OS_QNX:
        results = self.shell.run([f"pidin -p {self.pid} -f a"],
                                 capture_output=True,
                                 ignore_returncodes=[
                                     ShellExitCodes.EX_FAILURE
                                 ]).stdout.decode("utf-8").strip().split("\n")
        # We have to account for the header in the output
        return len(results) > 1

      # Rest of POSIX OSes
      result = self.shell.run(["ps", "--no-headers", "-p", self.pid],
                              capture_output=True,
                              ignore_returncodes=[
                                  ShellExitCodes.EX_FAILURE,
                                  ShellExitCodes.EX_NOTFOUND
                              ])
      return result.returncode == 0
