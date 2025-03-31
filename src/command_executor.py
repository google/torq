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

import datetime
import signal
import subprocess
import time
from abc import ABC, abstractmethod
from .config_builder import PREDEFINED_PERFETTO_CONFIGS, build_custom_config
from .handle_input import HandleInput
from .open_ui import open_trace
from .device import SIMPLEPERF_TRACE_FILE, POLLING_INTERVAL_SECS
from .utils import convert_simpleperf_to_gecko

PERFETTO_TRACE_FILE = "/data/misc/perfetto-traces/trace.perfetto-trace"
PERFETTO_BOOT_TRACE_FILE = "/data/misc/perfetto-traces/boottrace.perfetto-trace"
WEB_UI_ADDRESS = "https://ui.perfetto.dev"
TRACE_START_DELAY_SECS = 0.5
MAX_WAIT_FOR_INIT_USER_SWITCH_SECS = 180
ANDROID_SDK_VERSION_T = 33
SIMPLEPERF_STOP_TIMEOUT_SECS = 60


class CommandExecutor(ABC):
  """
  Abstract base class representing a command executor.
  """
  def __init__(self):
    pass

  def execute(self, command, device):
    for sig in [signal.SIGINT, signal.SIGTERM]:
      signal.signal(sig, lambda s, f: self.signal_handler(s,f))
    error = device.check_device_connection()
    if error is not None:
      return error
    device.root_device()
    error = command.validate(device)
    if error is not None:
      return error
    return self.execute_command(command, device)

  @abstractmethod
  def execute_command(self, command, device):
    raise NotImplementedError

  def signal_handler(self, sig, frame):
    pass

class ProfilerCommandExecutor(CommandExecutor):

  def __init__(self):
    self.trace_cancelled = False

  def execute_command(self, command, device):
    config, error = self.create_config(command, device.get_android_sdk_version())
    if error is not None:
      return error
    error = self.prepare_device(command, device, config)
    if error is not None:
      return error
    host_raw_trace_filename = None
    host_gecko_trace_filename = None
    for run in range(1, command.runs + 1):
      timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
      if command.profiler == "perfetto":
        host_raw_trace_filename = f"{command.out_dir}/trace-{timestamp}.perfetto-trace"
      else:
        host_raw_trace_filename = f"{command.out_dir}/perf-{timestamp}.data"
        host_gecko_trace_filename = f"{command.out_dir}/perf-{timestamp}.json"
      error = self.prepare_device_for_run(command, device)
      if error is not None:
        return error
      start_time = time.time()
      if self.trace_cancelled:
        return self.cleanup(command, device)
      error = self.execute_run(command, device, config, run)
      if error is not None:
        return error
      print("Run lasted for %.3f seconds." % (time.time() - start_time))
      error = self.retrieve_perf_data(command, device,
                                      host_raw_trace_filename,
                                      host_gecko_trace_filename)
      if error is not None:
        return error
      if command.runs != run:
        if self.trace_cancelled:
          if not HandleInput("Continue with remaining runs? [Y/n]: ",
                             "",
                             {"y": lambda: True,
                              "n": lambda: False}, "y").handle_input():
            return self.cleanup(command, device)
          self.trace_cancelled = False
        print("Waiting for %d seconds before next run."
              % (command.between_dur_ms / 1000))
        time.sleep(command.between_dur_ms / 1000)
    error = self.cleanup(command, device)
    if error is not None:
      return error
    if command.use_ui:
      error = open_trace(host_raw_trace_filename
                         if command.profiler == "perfetto" else
                         host_gecko_trace_filename, WEB_UI_ADDRESS, False)
      if error is not None:
        return error
    return None

  @staticmethod
  def create_config(command, android_sdk_version):
    if command.perfetto_config in PREDEFINED_PERFETTO_CONFIGS:
      return PREDEFINED_PERFETTO_CONFIGS[command.perfetto_config](
          command, android_sdk_version)
    else:
      return build_custom_config(command)

  def prepare_device(self, command, device, config):
    return None

  def prepare_device_for_run(self, command, device):
    if command.profiler == "perfetto":
      device.remove_file(PERFETTO_TRACE_FILE)
    else:
      device.remove_file(SIMPLEPERF_TRACE_FILE)

  def execute_run(self, command, device, config, run):
    print("Performing run %s. Press CTRL+C to end the trace." % run)
    if command.profiler == "perfetto":
      process = device.start_perfetto_trace(config)
    else:
      process = device.start_simpleperf_trace(command)
    time.sleep(TRACE_START_DELAY_SECS)
    error = self.trigger_system_event(command, device)
    if error is not None:
      print("Trace interrupted.")
      self.stop_process(device, command.profiler)
      return error
    while process.poll() is None and not self.trace_cancelled:
      continue
    if process.poll() is None:
      print("Trace interrupted.")
      self.stop_process(device, command.profiler)
    return None

  def trigger_system_event(self, command, device):
    return None

  def retrieve_perf_data(self, command, device, host_raw_trace_filename,
      host_gecko_trace_filename):
    if command.profiler == "perfetto":
      device.pull_file(PERFETTO_TRACE_FILE, host_raw_trace_filename)
    else:
      device.pull_file(SIMPLEPERF_TRACE_FILE, host_raw_trace_filename)
      convert_simpleperf_to_gecko(command.scripts_path, host_raw_trace_filename,
                                  host_gecko_trace_filename, command.symbols)

  def cleanup(self, command, device):
    return None

  def signal_handler(self, sig, frame):
    self.trace_cancelled = True

  def stop_process(self, device, name):
    if name == "simpleperf":
      device.send_signal(name, "SIGINT")
      # Simpleperf does post-processing, need to wait until the package stops
      # running
      print("Doing post-processing.")
      if not device.poll_is_task_completed(SIMPLEPERF_STOP_TIMEOUT_SECS,
                                           POLLING_INTERVAL_SECS,
                                           lambda:
                                           not device.is_package_running(name)):
        raise Exception("Simpleperf post-processing took too long.")
    else:
      device.kill_process(name)


class UserSwitchCommandExecutor(ProfilerCommandExecutor):

  def prepare_device_for_run(self, command, device):
    super().prepare_device_for_run(command, device)
    current_user = device.get_current_user()
    if self.trace_cancelled:
      return None
    if command.from_user != current_user:
      print("Switching from the current user, %s, to the from-user, %s."
            % (current_user, command.from_user))
      device.perform_user_switch(command.from_user)
      if not device.poll_is_task_completed(MAX_WAIT_FOR_INIT_USER_SWITCH_SECS,
                                           POLLING_INTERVAL_SECS,
                                           lambda: device.get_current_user()
                                                   == command.from_user):
        raise Exception(("Device with serial %s took more than %d secs to "
                         "switch to the initial user."
                         % (device.serial, dur_seconds)))

  def trigger_system_event(self, command, device):
    print("Switching from the from-user, %s, to the to-user, %s."
          % (command.from_user, command.to_user))
    device.perform_user_switch(command.to_user)

  def cleanup(self, command, device):
    if device.get_current_user() != command.original_user:
      print("Switching from the to-user, %s, back to the original user, %s."
            % (command.to_user, command.original_user))
      device.perform_user_switch(command.original_user)


class BootCommandExecutor(ProfilerCommandExecutor):

  def prepare_device(self, command, device, config):
    device.write_to_file("/data/misc/perfetto-configs/boottrace.pbtxt", config)

  def prepare_device_for_run(self, command, device):
    device.remove_file(PERFETTO_BOOT_TRACE_FILE)
    device.set_prop("persist.debug.perfetto.boottrace", "1")

  def execute_run(self, command, device, config, run):
    print("Performing run %s. Triggering reboot." % run)
    self.trigger_system_event(command, device)
    device.wait_for_device()
    device.root_device()
    if command.dur_ms is not None:
      print("Tracing for %s seconds. Press CTRL+C to end early."
            % (command.dur_ms / 1000))
    else:
      print("Tracing. Press CTRL+C to end.")
    device.wait_for_boot_to_complete()
    while (device.is_package_running(command.profiler)
           and not self.trace_cancelled):
      continue
    if device.is_package_running(command.profiler):
      print("Trace interrupted.")
      self.stop_process(device, command.profiler)
    return None

  def trigger_system_event(self, command, device):
    device.reboot()

  def retrieve_perf_data(self, command, device, host_raw_trace_filename,
      host_gecko_trace_filename):
    device.pull_file(PERFETTO_BOOT_TRACE_FILE, host_raw_trace_filename)


class AppStartupCommandExecutor(ProfilerCommandExecutor):

  def execute_run(self, command, device, config, run):
    error = super().execute_run(command, device, config, run)
    if error is not None:
      return error
    device.force_stop_package(command.app)

  def trigger_system_event(self, command, device):
    return device.start_package(command.app)


class ConfigCommandExecutor(CommandExecutor):

  def execute(self, command, device):
    return self.execute_command(command, device)

  def execute_command(self, command, device):
    match command.get_type():
      case "config list":
        print("\n".join(list(PREDEFINED_PERFETTO_CONFIGS.keys())))
        return None
      case "config show" | "config pull":
        return self.execute_config_command(command, device)
      case _:
        raise ValueError("Invalid config subcommand was used.")

  def execute_config_command(self, command, device):
    android_sdk_version = ANDROID_SDK_VERSION_T
    error = device.check_device_connection()
    if error is None:
      device.root_device()
      android_sdk_version = device.get_android_sdk_version()

    config, error = PREDEFINED_PERFETTO_CONFIGS[command.config_name](
        command, android_sdk_version)

    if error is not None:
      return error

    if command.get_type() == "config pull":
      subprocess.run(("cat > %s %s" % (command.file_path, config)), shell=True)
    else:
      print("\n".join(config.strip().split("\n")[2:-2]))

    return None
