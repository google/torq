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
import subprocess

from .base import ANDROID_SDK_VERSION_T
from .command import Command
from .command_executor import CommandExecutor
from .config_builder import PREDEFINED_PERFETTO_CONFIGS
from .validation_error import ValidationError


def add_config_parser(subparsers):
  config_parser = subparsers.add_parser('config',
                                        help=('The config subcommand used'
                                              ' to list and show the'
                                              ' predefined perfetto configs.'))
  config_subparsers = config_parser.add_subparsers(dest='config_subcommand',
                                                   help=('torq config'
                                                         ' subcommands'))
  config_subparsers.add_parser('list',
                               help=('Command to list the predefined'
                                     ' perfetto configs'))
  config_show_parser = config_subparsers.add_parser('show',
                                                    help=('Command to print'
                                                          ' the '
                                                          ' perfetto config'
                                                          ' in the terminal.'))
  config_show_parser.add_argument('config_name',
                                  choices=['lightweight', 'default', 'memory'],
                                  help=('Name of the predefined perfetto'
                                        ' config to print.'))
  config_show_parser.add_argument('-d', '--dur-ms', type=int,
                      help=('The duration (ms) of the event. Determines when'
                            ' to stop collecting performance data.'))
  config_show_parser.add_argument('--excluded-ftrace-events', action='append',
                      help=('Excludes specified ftrace event from the perfetto'
                            ' config events.'))
  config_show_parser.add_argument('--included-ftrace-events', action='append',
                      help=('Includes specified ftrace event in the perfetto'
                            ' config events.'))

  config_pull_parser = config_subparsers.add_parser('pull',
                                                    help=('Command to copy'
                                                          ' a predefined config'
                                                          ' to the specified'
                                                          ' file path.'))
  config_pull_parser.add_argument('config_name',
                                  choices=['lightweight', 'default', 'memory'],
                                  help='Name of the predefined config to copy')
  config_pull_parser.add_argument('file_path', nargs='?',
                                  help=('File path to copy the predefined'
                                        ' config to'))
  config_pull_parser.add_argument('-d', '--dur-ms', type=int,
                      help=('The duration (ms) of the event. Determines when'
                            ' to stop collecting performance data.'))
  config_pull_parser.add_argument('--excluded-ftrace-events', action='append',
                      help=('Excludes specified ftrace event from the perfetto'
                            ' config events.'))
  config_pull_parser.add_argument('--included-ftrace-events', action='append',
                      help=('Includes specified ftrace event in the perfetto'
                            ' config events.'))

def verify_config_args(args):
  if args.config_subcommand is None:
    return None, ValidationError(
        ("Command is invalid because torq config cannot be called"
         " without a subcommand."),
        ("Use one of the following subcommands:\n"
         "\t torq config list\n"
         "\t torq config show\n"
         "\t torq config pull\n"))

  if args.config_subcommand == "pull":
    if args.file_path is None:
      args.file_path = "./" + args.config_name + ".pbtxt"
    elif not os.path.isfile(args.file_path):
      return None, ValidationError(
          ("Command is invalid because %s is not a valid filepath."
           % args.file_path),
          ("A default filepath can be used if you do not specify a file-path:\n"
           "\t torq pull default to copy to ./default.pbtxt\n"
           "\t torq pull lightweight to copy to ./lightweight.pbtxt\n"
           "\t torq pull memory to copy to ./memory.pbtxt"))

  return args, None


def create_config_command(args):
  type = "config " + args.config_subcommand
  config_name = None
  file_path = None
  dur_ms = None
  excluded_ftrace_events = None
  included_ftrace_events = None
  if args.config_subcommand == "pull" or args.config_subcommand == "show":
    config_name = args.config_name
    dur_ms = args.dur_ms
    excluded_ftrace_events = args.excluded_ftrace_events
    included_ftrace_events = args.included_ftrace_events
    if args.config_subcommand == "pull":
      file_path = args.file_path

  command = ConfigCommand(type, config_name, file_path, dur_ms,
      excluded_ftrace_events, included_ftrace_events)
  return command


class ConfigCommand(Command):
  """
  Represents commands which get information about the predefined configs.
  """
  def __init__(self, type, config_name, file_path, dur_ms,
      excluded_ftrace_events, included_ftrace_events):
    super().__init__(type)
    self.config_name = config_name
    self.file_path = file_path
    self.dur_ms = dur_ms
    self.excluded_ftrace_events = excluded_ftrace_events
    self.included_ftrace_events = included_ftrace_events
    self.command_executor = ConfigCommandExecutor()

  def validate(self, device):
    raise NotImplementedError


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
