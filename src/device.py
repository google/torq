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

import enum
import math
import os
import sys
import time
from abc import ABC, abstractmethod
from .base import ValidationError
from .handle_input import HandleInput
from .shell import AdbShell
from .utils import poll_is_task_completed, run_subprocess, ShellExitCodes

ADB_ROOT_TIMED_OUT_LIMIT_SECS = 5
ADB_BOOT_COMPLETED_TIMED_OUT_LIMIT_SECS = 30
POLLING_INTERVAL_SECS = 0.5
SIMPLEPERF_TRACE_FILE = "/tmp/simpleperf-traces/perf.data"


def get_device(args, is_device_required):
  device = None
  if args.serial:
    serial = args.serial[0]
    error = AdbShell.verify_serial(serial)
    if error is not None:
      return None, error
    device = AndroidDevice(AdbShell(serial))
  else:
    serial, error = AdbShell.get_default_serial()
    if error is None:
      device = AndroidDevice(AdbShell(serial))
    elif is_device_required:
      return None, error
  return device, None


@enum.unique
class OSCodes(enum.IntEnum):
  OS_UNKNOWN = 0
  OS_ANDROID = 1


class Device(ABC):
  """
  Abstract base class representing a device
  """

  def __init__(self, shell):
    assert shell is not None, "shell cannot be None"
    self.shell = shell

  @abstractmethod
  def id(self):
    raise NotImplementedError

  @abstractmethod
  def os(self):
    raise NotImplementedError

  @abstractmethod
  def root_device(self):
    raise NotImplementedError

  @abstractmethod
  def send_signal(self, process_name, signal):
    raise NotImplementedError

  @abstractmethod
  def kill_process(self, process_name):
    raise NotImplementedError

  @abstractmethod
  def pull_file(self, filepath):
    raise NotImplementedError

  @abstractmethod
  def remove_file(self, filepath):
    raise NotImplementedError

  @abstractmethod
  def is_process_running(self, process_name):
    raise NotImplementedError

  @abstractmethod
  def get_current_user(self):
    raise NotImplementedError

  @abstractmethod
  def start_perfetto_trace(self, config):
    raise NotImplementedError


class AndroidDevice(Device):
  """
  Class representing a device. APIs interact with the current device through
  the adb bridge.
  """

  def id(self):
    return self.shell.id()

  def os(self):
    return OSCodes.OS_ANDROID

  def root_device(self):
    self.shell.run(["root"])
    if not poll_is_task_completed(
        ADB_ROOT_TIMED_OUT_LIMIT_SECS, POLLING_INTERVAL_SECS,
        lambda: self.shell.id() in AdbShell.get_adb_devices()):
      raise Exception(("Device with serial %s took too long to reconnect after"
                       " being rooted." % self.shell.id()))

  def remove_file(self, filepath):
    output = self.shell.run(["shell", "rm", filepath],
                            capture_output=True,
                            ignore_returncodes=[ShellExitCodes.EX_FAILURE])
    return not output.returncode

  def file_exists(self, file):
    output = self.shell.run(["shell", "ls", file],
                            capture_output=True,
                            ignore_returncodes=[ShellExitCodes.EX_FAILURE])
    return not output.returncode

  def start_perfetto_trace(self, config):
    return self.shell.popen("shell perfetto -c - --txt -o "
                            "/data/misc/perfetto-traces/trace.perfetto-trace " +
                            config)

  def trigger_perfetto(self, trigger_name):
    self.shell.run(["shell", "trigger_perfetto", trigger_name])

  def start_simpleperf_trace(self, command):
    events_param = "-e " + ",".join(command.simpleperf_event)
    duration = ""
    if command.dur_ms is not None:
      duration = "--duration %d" % int(math.ceil(command.dur_ms / 1000))
    return self.shell.popen([
        "shell", "simpleperf", "record", "-a", "-f", "1000", "--exclude-perf",
        "--post-unwind=yes", "-m", "8192", "-g", duration, events_param, "-o",
        SIMPLEPERF_TRACE_FILE
    ])

  def pull_file(self, filepath, host_file):
    output = self.shell.run(["pull", filepath, host_file],
                            capture_output=True,
                            ignore_returncodes=[ShellExitCodes.EX_FAILURE])
    return not output.returncode

  def get_all_users(self):
    command_output = self.shell.run(["shell", "pm", "list", "users"],
                                    capture_output=True)
    output_lines = command_output.stdout.decode("utf-8").split("\n")[1:-1]
    return [
        int((line.split("{", 1)[1]).split(":", 1)[0]) for line in output_lines
    ]

  def user_exists(self, user):
    users = self.get_all_users()
    if user not in users:
      return ValidationError(("User ID %s does not exist on device with serial"
                              " %s." % (user, self.shell.id())),
                             ("Select from one of the following user IDs on"
                              " device with serial %s: %s" %
                              (self.shell.id(), ", ".join(map(str, users)))))
    return None

  def get_current_user(self):
    command_output = self.shell.run(["shell", "am", "get-current-user"],
                                    capture_output=True)
    return int(command_output.stdout.decode("utf-8").split()[0])

  def perform_user_switch(self, user):
    self.shell.run(["shell", "am", "switch-user", str(user)])

  def write_to_file(self, file_path, host_file_string):
    self.shell.run(["shell", f"cat > {file_path} {host_file_string}"])

  def set_prop(self, prop, value):
    self.shell.run(["shell", "setprop", prop, value])

  def clear_prop(self, prop):
    self.shell.run(["shell", "setprop", prop, "\"\""])

  def reboot(self):
    self.shell.run(["reboot"])
    if not poll_is_task_completed(
        ADB_ROOT_TIMED_OUT_LIMIT_SECS, POLLING_INTERVAL_SECS,
        lambda: self.shell.id() not in AdbShell.get_adb_devices()):
      raise Exception(("Device with serial %s took too long to start"
                       " rebooting." % self.shell.id()))

  def wait_for_device(self):
    self.shell.run(["wait-for-device"])

  def is_boot_completed(self):
    command_output = self.shell.run(["shell", "getprop", "sys.boot_completed"],
                                    capture_output=True)
    return command_output.stdout.decode("utf-8").strip() == "1"

  def wait_for_boot_to_complete(self):
    if not poll_is_task_completed(ADB_BOOT_COMPLETED_TIMED_OUT_LIMIT_SECS,
                                  POLLING_INTERVAL_SECS,
                                  self.is_boot_completed):
      raise Exception(("Device with serial %s took too long to finish"
                       " rebooting." % self.shell.id()))

  def get_packages(self):
    return [
        package.removeprefix("package:")
        for package in self.shell.run(["shell", "pm", "list", "packages"],
                                      capture_output=True).stdout.decode(
                                          "utf-8").splitlines()
    ]

  def get_pid(self, process_name):
    return self.shell.run(["shell", "pidof", process_name],
                          capture_output=True,
                          ignore_returncodes=[
                              ShellExitCodes.EX_FAILURE
                          ]).stdout.decode("utf-8").split("\n")[0]

  def is_process_running(self, process_name):
    return self.get_pid(process_name) != ""

  def start_package(self, package):
    if self.shell.run(["shell", "am", "start", package],
                      capture_output=True,
                      ignore_returncodes=[
                          ShellExitCodes.EX_FAILURE
                      ]).stderr.decode("utf-8").split("\n")[0] != "":
      return ValidationError(("Cannot start package %s on device with"
                              " serial %s because %s is a service package,"
                              " which doesn't implement a MAIN activity." %
                              (package, self.shell.id(), package)), None)
    return None

  def kill_process(self, name):
    pid = self.get_pid(name)
    if pid != "":
      self.shell.run(["shell", "kill", "-9", pid])

  def send_signal(self, process_name, signal):
    self.shell.run(["shell", "pkill", "-l", signal, process_name])

  def force_stop_package(self, package):
    self.shell.run(["shell", "am", "force-stop", package])

  def get_prop(self, prop):
    return self.shell.run(
        ["shell", "getprop", prop],
        capture_output=True).stdout.decode("utf-8").split("\n")[0]

  def get_android_sdk_version(self):
    return int(self.get_prop("ro.build.version.sdk"))

  def create_directory(self, directory):
    self.shell.run(["shell", "mkdir", "-p", directory], capture_output=True)
    return None

  def simpleperf_event_exists(self, simpleperf_events):
    events_copy = simpleperf_events.copy()
    grep_command = "grep"
    for event in simpleperf_events:
      grep_command += " -e " + event.lower()

    if not self.file_exists("/system/bin/simpleperf"):
      return ValidationError("Simpleperf was not found in the device.",
                             "Push the simpleperf binary to the device.")

    output = self.shell.run(["shell", "simpleperf", "list", "|", grep_command],
                            capture_output=True,
                            ignore_returncodes=[ShellExitCodes.EX_FAILURE])

    lines = output.stdout.decode("utf-8").split("\n")

    # Anything that does not start with two spaces is not a command.
    # Any command with a space will have the command before the first space.
    for line in lines:
      if len(line) <= 3 or line[:2] != "  " or line[2] == "#":
        # Line doesn't contain a simpleperf event
        continue
      event = line[2:].split(" ")[0]
      if event in events_copy:
        events_copy.remove(event)
        if len(events_copy) == 0:
          # All of the events exist, exit early
          break

    if len(events_copy) > 0:
      return ValidationError(
          "The following simpleperf event(s) are invalid:"
          " %s." % events_copy, "Run adb shell simpleperf list to"
          " see valid simpleperf events.")
    return None
