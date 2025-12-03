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

import argparse
import datetime
import os
import time

from .base import (ANDROID_SDK_VERSION_T, Command, CommandExecutor,
                   ValidationError)
from .config_builder import (build_custom_config, create_common_config_parser,
                             PREDEFINED_PERFETTO_CONFIGS)
from .device import SIMPLEPERF_TRACE_FILE, POLLING_INTERVAL_SECS
from .handle_input import HandleInput
from .open_ui_utils import open_trace, WEB_UI_ADDRESS
from .utils import convert_simpleperf_to_gecko
from .validate_simpleperf import verify_simpleperf_args

DEFAULT_DUR_MS = 10000
DEFAULT_OUT_DIR = "."
MAX_WAIT_FOR_INIT_USER_SWITCH_SECS = 180
MIN_DURATION_MS = 3000
MIN_STOP_DELAY_MS = 1000
PERFETTO_DEVICE_FOLDER = "/data/misc/perfetto-traces"
PERFETTO_TRACE_FILE = PERFETTO_DEVICE_FOLDER + "/trace.perfetto-trace"
PERFETTO_BOOT_TRACE_FILE = PERFETTO_DEVICE_FOLDER + "/boottrace.perfetto-trace"
SIMPLEPERF_DEVICE_TRACE_FOLDER = "/tmp/simpleperf-traces"
SIMPLEPERF_STOP_TIMEOUT_SECS = 60
TRACE_START_DELAY_SECS = 0.5
DEFAULT_TRIGGER_DUR_MS = 604800000  # 7 days in millis
DEFAULT_TRIGGER_STOP_DELAY_MS = [1000]
DEFAULT_TRIGGER_MODE = "STOP_TRACING"


def add_profiler_parser(subparsers):
  profiler_parser = subparsers.add_parser(
      'profiler',
      help=('Profiler subcommand'
            ' used to trace and'
            ' profile Android'),
      parents=[create_common_config_parser()])
  profiler_parser.add_argument(
      '-e',
      '--event',
      choices=['boot', 'user-switch', 'app-startup', 'custom'],
      default='custom',
      help='The event to trace/profile.')
  profiler_parser.add_argument(
      '-p',
      '--profiler',
      choices=['perfetto', 'simpleperf'],
      default='perfetto',
      help='The performance data source.')
  profiler_parser.add_argument(
      '-o',
      '--out-dir',
      default=DEFAULT_OUT_DIR,
      help='The path to the output directory.')
  profiler_parser.add_argument(
      '-a', '--app', help='The package name of the app we want to start.')
  profiler_parser.add_argument(
      '-r',
      '--runs',
      type=int,
      default=1,
      help=('The number of times to run the event and'
            ' capture the perf data.'))
  profiler_parser.add_argument(
      '-s',
      '--simpleperf-event',
      action='append',
      help=('Simpleperf supported events to be collected.'
            ' e.g. cpu-cycles, instructions'))
  profiler_parser.add_argument(
      '--perfetto-config',
      default='default',
      help=('Predefined perfetto configs can be used:'
            ' %s. A filepath with a custom config could'
            ' also be provided.' %
            (", ".join(PREDEFINED_PERFETTO_CONFIGS.keys()))))
  profiler_parser.add_argument(
      '--between-dur-ms',
      type=int,
      default=DEFAULT_DUR_MS,
      help='Time (ms) to wait before executing the next event.')
  profiler_parser.add_argument(
      '--ui',
      action=argparse.BooleanOptionalAction,
      help=('Specifies opening of UI visualization tool'
            ' after profiling is complete.'))
  profiler_parser.add_argument(
      '--from-user',
      type=int,
      help='The user id from which to start the user switch')
  profiler_parser.add_argument(
      '--to-user',
      type=int,
      help='The user id of user that system is switching to.')
  profiler_parser.add_argument(
      '--symbols', help='Specifies path to symbols library.')


def verify_profiler_args(args):
  if args.out_dir != DEFAULT_OUT_DIR and not os.path.isdir(args.out_dir):
    return None, ValidationError(
        ("Command is invalid because --out-dir is not a valid directory"
         " path: %s." % args.out_dir), None)

  if args.dur_ms is not None and args.dur_ms < MIN_DURATION_MS:
    return None, ValidationError(
        ("Command is invalid because --dur-ms cannot be set to a value smaller"
         " than %d." % MIN_DURATION_MS),
        ("Set --dur-ms %d to capture a trace for %d seconds." %
         (MIN_DURATION_MS, (MIN_DURATION_MS / 1000))))

  if args.from_user is not None and args.event != "user-switch":
    return None, ValidationError(
        ("Command is invalid because --from-user is passed, but --event is not"
         " set to user-switch."),
        ("Set --event user-switch --from-user %s to perform a user-switch from"
         " user %s." % (args.from_user, args.from_user)))

  if args.to_user is not None and args.event != "user-switch":
    return None, ValidationError((
        "Command is invalid because --to-user is passed, but --event is not set"
        " to user-switch."
    ), ("Set --event user-switch --to-user %s to perform a user-switch to user"
        " %s." % (args.to_user, args.to_user)))

  if args.event == "user-switch" and args.to_user is None:
    return None, ValidationError(
        "Command is invalid because --to-user is not passed.",
        ("Set --event %s --to-user <user-id> to perform a %s." %
         (args.event, args.event)))

  # TODO(b/374313202): Support for simpleperf boot event will
  #                    be added in the future
  if args.event == "boot" and args.profiler == "simpleperf":
    return None, ValidationError(
        "Boot event is not yet implemented for simpleperf.",
        "Please try another event.")

  if args.app is not None and args.event != "app-startup":
    return None, ValidationError(
        ("Command is invalid because --app is passed and --event is not set"
         " to app-startup."),
        ("To profile an app startup run:"
         " torq --event app-startup --app <package-name>"))

  if args.event == "app-startup" and args.app is None:
    return None, ValidationError(
        "Command is invalid because --app is not passed.",
        ("Set --event %s --app <package> to perform an %s." %
         (args.event, args.event)))

  if args.runs < 1:
    return None, ValidationError(
        ("Command is invalid because --runs cannot be set to a value smaller"
         " than 1."), None)

  if args.runs > 1 and args.ui:
    return None, ValidationError(
        ("Command is invalid because --ui cannot be"
         " passed if --runs is set to a value greater"
         " than 1."),
        ("Set torq -r %d --no-ui to perform %d runs." % (args.runs, args.runs)))

  if args.simpleperf_event is not None and args.profiler != "simpleperf":
    return None, ValidationError(
        ("Command is invalid because --simpleperf-event cannot be passed"
         " if --profiler is not set to simpleperf."),
        ("To capture the simpleperf event run:"
         " torq --profiler simpleperf --simpleperf-event %s" %
         " --simpleperf-event ".join(args.simpleperf_event)))

  if (args.simpleperf_event is not None and
      len(args.simpleperf_event) != len(set(args.simpleperf_event))):
    return None, ValidationError(
        ("Command is invalid because redundant calls to --simpleperf-event"
         " cannot be made."),
        ("Only set --simpleperf-event cpu-cycles once if you want"
         " to collect cpu-cycles."))

  if args.perfetto_config != "default":
    if args.profiler != "perfetto":
      return None, ValidationError(
          ("Command is invalid because --perfetto-config cannot be passed"
           " if --profiler is not set to perfetto."),
          ("Set --profiler perfetto to choose a perfetto-config"
           " to use."))

  if (args.perfetto_config not in PREDEFINED_PERFETTO_CONFIGS and
      not os.path.isfile(args.perfetto_config)):
    return None, ValidationError(
        ("Command is invalid because --perfetto-config is not a valid"
         " file path: %s" % args.perfetto_config),
        ("Predefined perfetto configs can be used:\n"
         "\t torq --perfetto-config %s\n"
         "\t A filepath with a config can also be used:\n"
         "\t torq --perfetto-config <config-filepath>" %
         ("\n\t torq --perfetto-config"
          " ".join(PREDEFINED_PERFETTO_CONFIGS.keys()))))

  if args.between_dur_ms < MIN_DURATION_MS:
    return None, ValidationError(
        ("Command is invalid because --between-dur-ms cannot be set to a"
         " smaller value than %d." % MIN_DURATION_MS),
        ("Set --between-dur-ms %d to wait %d seconds between"
         " each run." % (MIN_DURATION_MS, (MIN_DURATION_MS / 1000))))

  if args.between_dur_ms != DEFAULT_DUR_MS and args.runs == 1:
    return None, ValidationError(
        ("Command is invalid because --between-dur-ms cannot be passed"
         " if --runs is not a value greater than 1."),
        "Set --runs 2 to run 2 tests.")

  if args.excluded_ftrace_events is not None and args.profiler != "perfetto":
    return None, ValidationError(
        ("Command is invalid because --excluded-ftrace-events cannot be passed"
         " if --profiler is not set to perfetto."),
        ("Set --profiler perfetto to exclude an ftrace event"
         " from perfetto config."))

  if (args.excluded_ftrace_events is not None and len(
      args.excluded_ftrace_events) != len(set(args.excluded_ftrace_events))):
    return None, ValidationError(
        ("Command is invalid because duplicate ftrace events cannot be"
         " included in --excluded-ftrace-events."),
        ("--excluded-ftrace-events should only include one instance of an"
         " ftrace event."))

  if args.included_ftrace_events is not None and args.profiler != "perfetto":
    return None, ValidationError(
        ("Command is invalid because --included-ftrace-events cannot be passed"
         " if --profiler is not set to perfetto."),
        ("Set --profiler perfetto to include an ftrace event"
         " in perfetto config."))

  if (args.included_ftrace_events is not None and len(
      args.included_ftrace_events) != len(set(args.included_ftrace_events))):
    return None, ValidationError(
        ("Command is invalid because duplicate ftrace events cannot be"
         " included in --included-ftrace-events."),
        ("--included-ftrace-events should only include one instance of an"
         " ftrace event."))

  if (args.included_ftrace_events is not None and
      args.excluded_ftrace_events is not None):
    ftrace_event_intersection = sorted(
        (set(args.excluded_ftrace_events) & set(args.included_ftrace_events)))
    if len(ftrace_event_intersection):
      return None, ValidationError(
          ("Command is invalid because ftrace event(s): %s cannot be both"
           " included and excluded." % ", ".join(ftrace_event_intersection)),
          ("\n\t ".join("Only set --excluded-ftrace-events %s if you want to"
                        " exclude %s from the config or"
                        " --included-ftrace-events %s if you want to include %s"
                        " in the config." % (event, event, event, event)
                        for event in ftrace_event_intersection)))

  if args.profiler == "simpleperf" and args.simpleperf_event is None:
    args.simpleperf_event = ['cpu-cycles']

  if args.ui is None:
    args.ui = args.runs == 1

  if args.profiler == "simpleperf":
    args, error = verify_simpleperf_args(args)
    if error is not None:
      return None, error
  else:
    args.scripts_path = None

  return verify_trigger_args(args)


def verify_trigger_args(args):
  if args.trigger_names and args.profiler != "perfetto":
    return None, ValidationError(
        ("Command is invalid because --trigger-names cannot be passed"
         " if --profiler is not set to perfetto."),
        "Set -p perfetto to use trigger-names.")

  if args.trigger_names and args.dur_ms is not None:
    return None, ValidationError(
        ("Command is invalid because --dur-ms cannot be passed"
         " if a perfetto trigger is being set."),
        "Run command with a --trigger-timeout-ms option instead of --dur-ms.")

  if args.trigger_names and args.runs > 1:
    return None, ValidationError(
        "Command is invalid because the number of runs cannot be more than 1"
        " when including trigger configs.",
        "Run command without the -r option.")

  if not args.trigger_names and args.trigger_stop_delay_ms:
    return None, ValidationError(
        "Command is invalid because --trigger-stop-delay-ms cannot be set"
        " without --trigger-names.",
        "Set --trigger-names or remove --trigger-stop-delay-ms.")

  if args.trigger_names and not args.trigger_stop_delay_ms:
    args.trigger_stop_delay_ms = DEFAULT_TRIGGER_STOP_DELAY_MS

  if not args.trigger_names and args.trigger_timeout_ms:
    return None, ValidationError(
        "Command is invalid because --trigger-timeout-ms cannot be set without"
        " --trigger-names.",
        "Set --trigger-names or remove --trigger-timeout-ms.")

  if args.trigger_names and not args.trigger_timeout_ms:
    args.trigger_timeout_ms = DEFAULT_TRIGGER_DUR_MS

  if not args.trigger_names and args.trigger_mode:
    return None, ValidationError(
        "Command is invalid because --trigger-mode cannot be set without"
        " --trigger-names.", "Set --trigger-names or remove --trigger-mode.")

  if args.trigger_names and not args.trigger_mode:
    args.trigger_mode = DEFAULT_TRIGGER_MODE

  if (len(args.trigger_stop_delay_ms) > 1 and
      len(args.trigger_names) != len(args.trigger_stop_delay_ms)):
    return None, ValidationError(
        "Command is invalid because number of trigger names passed is not"
        " equal to number of stop-delay-ms values passed.",
        "Pass only one stop-delay-ms value to use for all triggers, pass none"
        " to use the default value for all triggers, or pass an equal number"
        " of trigger names and stop-delay-ms values.")

  if (args.trigger_timeout_ms is not None and
      args.trigger_timeout_ms < MIN_DURATION_MS):
    return None, ValidationError(
        ("Command is invalid because --trigger-timeout-ms cannot be set to a"
         " value smaller than %d." % MIN_DURATION_MS),
        ("Set --trigger-timeout-ms %d to timeout after %d seconds." %
         (MIN_DURATION_MS, (MIN_DURATION_MS / 1000))))

  if (args.trigger_stop_delay_ms is not None and
      any(x < MIN_STOP_DELAY_MS for x in args.trigger_stop_delay_ms)):
    return None, ValidationError(
        ("Command is invalid because --trigger-stop-delay-ms cannot be set to a"
         " value smaller than %d." % MIN_STOP_DELAY_MS),
        ("Set --trigger-stop-delay-ms %d to keep tracing after a trigger for %d"
         " seconds." % (MIN_STOP_DELAY_MS, (MIN_STOP_DELAY_MS / 1000))))

  match args.trigger_mode:
    case "stop":
      args.trigger_mode = "STOP_TRACING"
    case "start":
      args.trigger_mode = "START_TRACING"
    case "clone":
      args.trigger_mode = "CLONE_SNAPSHOT"

  # CLONE_SNAPSHOT will generate multiple traces, so don't automatically open
  # traces in the Perfetto UI
  if args.trigger_mode == "CLONE_SNAPSHOT":
    args.ui = False

  return args, None


def get_executor(event):
  match event:
    case "custom":
      return ProfilerCommandExecutor()
    case "user-switch":
      return UserSwitchCommandExecutor()
    case "boot":
      return BootCommandExecutor()
    case "app-startup":
      return AppStartupCommandExecutor()
    case _:
      raise ValueError("Invalid event name was used.")


def execute_profiler_command(args, device):
  command = ProfilerCommand(
      "profiler", args.event, args.profiler, args.out_dir, args.dur_ms,
      args.app, args.runs, args.simpleperf_event, args.perfetto_config,
      args.between_dur_ms, args.ui, args.excluded_ftrace_events,
      args.included_ftrace_events, args.from_user, args.to_user,
      args.scripts_path, args.symbols, args.trigger_names,
      args.trigger_timeout_ms, args.trigger_stop_delay_ms, args.trigger_mode)

  executor = get_executor(command.event)

  return executor.execute(command, device)


class ProfilerCommand(Command):
  """
  Represents commands which profile and trace the system.
  """

  def __init__(self, type, event, profiler, out_dir, dur_ms, app, runs,
               simpleperf_event, perfetto_config, between_dur_ms, ui,
               excluded_ftrace_events, included_ftrace_events, from_user,
               to_user, scripts_path, symbols, trigger_names,
               trigger_timeout_ms, trigger_stop_delay_ms, trigger_mode):
    super().__init__(type)
    self.event = event
    self.profiler = profiler
    self.out_dir = out_dir
    self.dur_ms = dur_ms
    self.app = app
    self.runs = runs
    self.simpleperf_event = simpleperf_event
    self.perfetto_config = perfetto_config
    self.between_dur_ms = between_dur_ms
    self.use_ui = ui
    self.excluded_ftrace_events = excluded_ftrace_events
    self.included_ftrace_events = included_ftrace_events
    self.from_user = from_user
    self.to_user = to_user
    self.scripts_path = scripts_path
    self.symbols = symbols
    self.trigger_names = trigger_names
    self.trigger_timeout_ms = trigger_timeout_ms
    self.trigger_stop_delay_ms = trigger_stop_delay_ms
    self.trigger_mode = trigger_mode

    if self.event == "user-switch":
      self.original_user = None

  def validate(self, device):
    print("Further validating arguments of ProfilerCommand.")
    if self.profiler == "perfetto":
      error = self.validate_trace_folder(device)
      if error is not None:
        return error
    elif self.profiler == "simpleperf":
      error = device.create_directory(SIMPLEPERF_DEVICE_TRACE_FOLDER)
      if error is not None:
        return error
      if self.simpleperf_event is not None:
        error = device.simpleperf_event_exists(self.simpleperf_event)
        if error is not None:
          return error
    match self.event:
      case "user-switch":
        return self.validate_user_switch(device)
      case "boot":
        return self.validate_boot(device)
      case "app-startup":
        return self.validate_app_startup(device)

  def validate_user_switch(self, device):
    error = device.user_exists(self.to_user)
    if error is not None:
      return error
    self.original_user = device.get_current_user()
    if self.from_user is None:
      self.from_user = self.original_user
    else:
      error = device.user_exists(self.from_user)
      if error is not None:
        return error
    if self.from_user == self.to_user:
      return ValidationError(
          "Cannot perform user-switch to user %s because"
          " the current user on device %s is already %s." %
          (self.to_user, device.serial, self.from_user),
          "Choose a --to-user ID that is different than"
          " the --from-user ID.")
    return None

  @staticmethod
  def validate_boot(device):
    if device.get_android_sdk_version() < ANDROID_SDK_VERSION_T:
      return ValidationError((
          "Cannot perform trace on boot because only devices with version Android 13"
          " (T) or newer can be configured to automatically start recording traces on"
          " boot."), ("Update your device or use a different device with"
                      " Android 13 (T) or newer."))
    return None

  def validate_app_startup(self, device):
    packages = device.get_packages()
    if self.app not in packages:
      return ValidationError(
          ("Package %s does not exist on device with serial"
           " %s." % (self.app, device.serial)),
          ("Select from one of the following packages on"
           " device with serial %s: \n\t %s" % (device.serial,
                                                (",\n\t ".join(packages)))))
    if device.is_package_running(self.app):
      return ValidationError(("Package %s is already running on device with"
                              " serial %s." % (self.app, device.serial)),
                             ("Run 'adb -s %s shell am force-stop %s' to close"
                              " the package %s before trying to start it." %
                              (device.serial, self.app, self.app)))
    return None

  def validate_trace_folder(self, device):
    if not device.file_exists(PERFETTO_DEVICE_FOLDER):
      return ValidationError(
          "%s folder does not exist on device with"
          " serial %s." % (PERFETTO_DEVICE_FOLDER, device.serial),
          "Make sure that your device has %s properly"
          " configured." % self.profiler.capitalize())
    return None


class ProfilerCommandExecutor(CommandExecutor):

  def __init__(self):
    self.trace_cancelled = False

  def execute_command(self, command, device):
    config, error = self.create_config(command,
                                       device.get_android_sdk_version(),
                                       device.get_perfetto_version())
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
      error = self.retrieve_perf_data(command, device, host_raw_trace_filename,
                                      host_gecko_trace_filename)
      if error is not None:
        return error
      if command.runs != run:
        if self.trace_cancelled:
          if not HandleInput("Continue with remaining runs? [Y/n]: ", "", {
              "y": lambda: True,
              "n": lambda: False
          }, "y").handle_input():
            return self.cleanup(command, device)
          self.trace_cancelled = False
        print("Waiting for %d seconds before next run." %
              (command.between_dur_ms / 1000))
        time.sleep(command.between_dur_ms / 1000)
    error = self.cleanup(command, device)
    if error is not None:
      return error
    if command.use_ui:
      error = open_trace(
          host_raw_trace_filename if command.profiler == "perfetto" else
          host_gecko_trace_filename, WEB_UI_ADDRESS, False)
      if error is not None:
        return error
    return None

  @staticmethod
  def create_config(command, android_sdk_version, perfetto_version):
    if command.perfetto_config in PREDEFINED_PERFETTO_CONFIGS:
      return PREDEFINED_PERFETTO_CONFIGS[command.perfetto_config](
          command, android_sdk_version, perfetto_version)
    else:
      return build_custom_config(command)

  def prepare_device(self, command, device, config):
    return None

  def prepare_device_for_run(self, command, device):
    if command.profiler == "perfetto":
      device.remove_file(f"{PERFETTO_TRACE_FILE}*")
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
    self.wait_for_trace(command, device, process)
    if device.is_package_running(command.profiler):
      print("\nTrace interrupted.")
      self.stop_process(device, command.profiler)
    return None

  def wait_for_trace(self, command, device, process):
    cur_dots = 1
    total_dots = 3
    while not self.is_trace_cancelled(command.profiler, device, process):
      if cur_dots > total_dots:
        cur_dots = 1
      print(
          '\rTracing' + '.' * cur_dots + ' ' * (total_dots - cur_dots),
          end='',
          flush=True)
      cur_dots += 1
      time.sleep(0.5)
    print()

  def trigger_system_event(self, command, device):
    return None

  def retrieve_perf_data(self, command, device, host_raw_trace_filename,
                         host_gecko_trace_filename):
    if command.profiler == "perfetto":
      if command.trigger_names and command.trigger_mode == "CLONE_SNAPSHOT":
        i = 0
        while device.pull_file(f"{PERFETTO_TRACE_FILE}.{i}",
                               f"{host_raw_trace_filename}.{i}"):
          i += 1
      else:
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
      if not device.poll_is_task_completed(
          SIMPLEPERF_STOP_TIMEOUT_SECS, POLLING_INTERVAL_SECS,
          lambda: not device.is_package_running(name)):
        raise Exception("Simpleperf post-processing took too long.")
    else:
      device.kill_process(name)

  def is_trace_cancelled(self, profiler, device, process):
    return process.poll() is not None or self.trace_cancelled


class UserSwitchCommandExecutor(ProfilerCommandExecutor):

  def prepare_device_for_run(self, command, device):
    super().prepare_device_for_run(command, device)
    current_user = device.get_current_user()
    if self.trace_cancelled:
      return None
    if command.from_user != current_user:
      print("Switching from the current user, %s, to the from-user, %s." %
            (current_user, command.from_user))
      device.perform_user_switch(command.from_user)
      if not device.poll_is_task_completed(
          MAX_WAIT_FOR_INIT_USER_SWITCH_SECS, POLLING_INTERVAL_SECS,
          lambda: device.get_current_user() == command.from_user):
        raise Exception(
            ("Device with serial %s took more than %d secs to "
             "switch to the initial user." % (device.serial, dur_seconds)))

  def trigger_system_event(self, command, device):
    print("Switching from the from-user, %s, to the to-user, %s." %
          (command.from_user, command.to_user))
    device.perform_user_switch(command.to_user)

  def cleanup(self, command, device):
    if device.get_current_user() != command.original_user:
      print("Switching from the to-user, %s, back to the original user, %s." %
            (command.to_user, command.original_user))
      device.perform_user_switch(command.original_user)


class BootCommandExecutor(ProfilerCommandExecutor):

  def prepare_device(self, command, device, config):
    device.write_to_file("/data/misc/perfetto-configs/boottrace.pbtxt", config)

  def prepare_device_for_run(self, command, device):
    device.remove_file(f'{PERFETTO_BOOT_TRACE_FILE}*')
    device.set_prop("persist.debug.perfetto.boottrace", "1")

  def execute_run(self, command, device, config, run):
    print("Performing run %s. Triggering reboot." % run)
    self.trigger_system_event(command, device)
    device.wait_for_device()
    device.root_device()
    if command.dur_ms is not None:
      print("Tracing for %s seconds. Press CTRL+C to end early." %
            (command.dur_ms / 1000))
    else:
      print("Tracing. Press CTRL+C to end.")
    device.wait_for_boot_to_complete()
    self.wait_for_trace(command, device, None)
    if device.is_package_running(command.profiler):
      print("Trace interrupted.")
      self.stop_process(device, command.profiler)
    return None

  def trigger_system_event(self, command, device):
    device.reboot()

  def retrieve_perf_data(self, command, device, host_raw_trace_filename,
                         host_gecko_trace_filename):
    if command.trigger_names and command.trigger_mode == "CLONE_SNAPSHOT":
      i = 0
      while device.pull_file(f'{PERFETTO_BOOT_TRACE_FILE}.{i}',
                             f'{host_raw_trace_filename}.{i}'):
        i += 1
    else:
      device.pull_file(PERFETTO_BOOT_TRACE_FILE, host_raw_trace_filename)

  def is_trace_cancelled(self, profiler, device, process):
    return not device.is_package_running(profiler) or self.trace_cancelled


class AppStartupCommandExecutor(ProfilerCommandExecutor):

  def execute_run(self, command, device, config, run):
    error = super().execute_run(command, device, config, run)
    if error is not None:
      return error
    device.force_stop_package(command.app)

  def trigger_system_event(self, command, device):
    return device.start_package(command.app)
