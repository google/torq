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

import argparse

from .config import (
    add_config_parser,
    verify_config_args,
    create_config_command,
    PREDEFINED_PERFETTO_CONFIGS
)
from .device import AdbDevice
from .open import (
    add_open_parser,
    OpenCommand,
    verify_open_args
)
from .profiler import (
    add_profiler_parser,
    verify_profiler_args,
    ProfilerCommand
)
from .utils import set_default_subparser
from .vm import add_vm_parser, create_vm_command

# Add default parser capability to argparse
argparse.ArgumentParser.set_default_subparser = set_default_subparser

def create_parser():
  parser = argparse.ArgumentParser(prog='torq command',
                                   description=('Torq CLI tool for performance'
                                                ' tests.'))
  # Global options
  # NOTE: All global options must have the 'nargs' option set to an int.
  parser.add_argument('--serial', nargs=1,
                      help=(('Specifies serial of the device that will be'
                             ' used.')))

  subparsers = parser.add_subparsers(dest='subcommands', help='Subcommands')

  add_profiler_parser(subparsers)
  add_config_parser(subparsers)
  add_open_parser(subparsers)
  add_vm_parser(subparsers)

  # Set 'profiler' as the default parser
  parser.set_default_subparser('profiler')

  return parser


def verify_args(args):
  match args.subcommands:
    case "profiler":
      return verify_profiler_args(args)
    case "config":
      return verify_config_args(args)
    case "open":
      return verify_open_args(args)
    case "vm":
      return args, None
    case _:
      raise ValueError("Invalid command type used")

def create_profiler_command(args):
  return ProfilerCommand("profiler", args.event, args.profiler, args.out_dir,
                         args.dur_ms,
                         args.app, args.runs, args.simpleperf_event,
                         args.perfetto_config, args.between_dur_ms,
                         args.ui, args.excluded_ftrace_events,
                         args.included_ftrace_events, args.from_user,
                         args.to_user, args.scripts_path, args.symbols)

def get_command(args):
  match args.subcommands:
    case "profiler":
      return create_profiler_command(args)
    case "config":
      return create_config_command(args)
    case "open":
      return OpenCommand(args.file_path, args.use_trace_processor)
    case "vm":
      return create_vm_command(args)
    case _:
      raise ValueError("Invalid command type used")


def print_error(error):
  print(error.message)
  if error.suggestion is not None:
    print("Suggestion:\n\t", error.suggestion)


def run():
  parser = create_parser()
  args = parser.parse_args()
  args, error = verify_args(args)
  if error is not None:
    print_error(error)
    return
  command = get_command(args)
  serial = args.serial[0] if args.serial else None
  device = AdbDevice(serial)
  error = command.execute(device)
  if error is not None:
    print_error(error)
    return
