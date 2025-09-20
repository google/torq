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
import os

from .base import ANDROID_SDK_VERSION_T, Command, ValidationError
from .config_builder import create_common_config_parser, PREDEFINED_PERFETTO_CONFIGS
from .profiler import verify_trigger_args
from .utils import run_subprocess


def add_config_parser(subparsers):
  common_config_args = argparse.ArgumentParser(add_help=False)
  common_config_args.add_argument(
      'config_name',
      choices=['lightweight', 'default', 'memory'],
      help='Name of the predefined config to copy')

  common_profiler_args = create_common_config_parser()

  config_parser = subparsers.add_parser(
      'config',
      help=('The config subcommand used'
            ' to list and show the'
            ' predefined perfetto configs.'))
  config_subparsers = config_parser.add_subparsers(
      dest='config_subcommand', help=('torq config'
                                      ' subcommands'))
  config_subparsers.add_parser(
      'list', help=('Command to list the predefined'
                    ' perfetto configs'))
  config_subparsers.add_parser(
      'show',
      help=('Command to print'
            ' the '
            ' perfetto config'
            ' in the terminal.'),
      parents=[common_profiler_args, common_config_args])

  config_pull_parser = config_subparsers.add_parser(
      'pull',
      help=('Command to copy'
            ' a predefined config'
            ' to the specified'
            ' file path.'),
      parents=[common_profiler_args, common_config_args])
  config_pull_parser.add_argument(
      'file_path',
      nargs='?',
      help=('File path to copy the predefined'
            ' config to'))


def verify_config_args(args):
  if args.config_subcommand is None:
    return None, ValidationError(
        ("Command is invalid because torq config cannot be called"
         " without a subcommand."), ("Use one of the following subcommands:\n"
                                     "\t torq config list\n"
                                     "\t torq config show\n"
                                     "\t torq config pull\n"))

  if args.config_subcommand == "pull":
    if args.file_path is None:
      args.file_path = "./" + args.config_name + ".pbtxt"
    elif not os.path.isfile(args.file_path):
      return None, ValidationError(
          ("Command is invalid because %s is not a valid filepath." %
           args.file_path),
          ("A default filepath can be used if you do not specify a file-path:\n"
           "\t torq pull default to copy to ./default.pbtxt\n"
           "\t torq pull lightweight to copy to ./lightweight.pbtxt\n"
           "\t torq pull memory to copy to ./memory.pbtxt"))

  if args.config_subcommand != "list":
    args.runs = 1
    args.profiler = "perfetto"
    return verify_trigger_args(args)

  return args, None


def create_config_command(args):
  type = "config " + args.config_subcommand
  config_name = None
  file_path = None
  dur_ms = None
  excluded_ftrace_events = None
  included_ftrace_events = None
  trigger_names = None
  trigger_stop_delay_ms = None
  trigger_timeout_ms = None
  trigger_mode = None
  if args.config_subcommand == "pull" or args.config_subcommand == "show":
    config_name = args.config_name
    dur_ms = args.dur_ms
    excluded_ftrace_events = args.excluded_ftrace_events
    included_ftrace_events = args.included_ftrace_events
    trigger_names = args.trigger_names
    trigger_stop_delay_ms = args.trigger_stop_delay_ms
    trigger_timeout_ms = args.trigger_timeout_ms
    trigger_mode = args.trigger_mode
    if args.config_subcommand == "pull":
      file_path = args.file_path

  command = ConfigCommand(type, config_name, file_path, dur_ms,
                          excluded_ftrace_events, included_ftrace_events,
                          trigger_names, trigger_stop_delay_ms,
                          trigger_timeout_ms, trigger_mode)
  return command


def execute_show_or_pull_command(command, device):
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
    run_subprocess(("cat > %s %s" % (command.file_path, config)), shell=True)
  else:
    print("\n".join(config.strip().split("\n")[2:-2]))
  return None


def execute_config_command(args, device):
  command = create_config_command(args)
  match command.get_type():
    case "config list":
      print("\n".join(list(PREDEFINED_PERFETTO_CONFIGS.keys())))
      return None
    case "config show" | "config pull":
      return execute_show_or_pull_command(command, device)
    case _:
      raise ValueError("Invalid config subcommand was used.")


class ConfigCommand(Command):
  """
  Represents commands which get information about the predefined configs.
  """

  def __init__(self, type, config_name, file_path, dur_ms,
               excluded_ftrace_events, included_ftrace_events, trigger_names,
               trigger_stop_delay_ms, trigger_timeout_ms, trigger_mode):
    super().__init__(type)
    self.config_name = config_name
    self.file_path = file_path
    self.dur_ms = dur_ms
    self.excluded_ftrace_events = excluded_ftrace_events
    self.included_ftrace_events = included_ftrace_events
    self.trigger_names = trigger_names
    self.trigger_stop_delay_ms = trigger_stop_delay_ms
    self.trigger_timeout_ms = trigger_timeout_ms
    self.trigger_mode = trigger_mode

  def validate(self, device):
    raise NotImplementedError
