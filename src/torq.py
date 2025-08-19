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
import sys

from .config import (add_config_parser, execute_config_command,
                     verify_config_args)
from .device import AdbDevice
from .open import (add_open_parser, execute_open_command, verify_open_args)
from .profiler import (add_profiler_parser, execute_profiler_command,
                       verify_profiler_args)
from .trigger import (add_trigger_parser, execute_trigger_command,
                      verify_trigger_args)
from .utils import set_default_subparser
from .vm import add_vm_parser, execute_vm_command, verify_vm_args

# Add default parser capability to argparse
argparse.ArgumentParser.set_default_subparser = set_default_subparser

# Torq supported commands
#
# NOTE: Add your new commands here
#
TORQ_COMMANDS = {
    'config': {
        'parse': add_config_parser,
        'verify': verify_config_args,
        'execute': execute_config_command,
    },
    'open': {
        'parse': add_open_parser,
        'verify': verify_open_args,
        'execute': execute_open_command,
    },
    'profiler': {
        'parse': add_profiler_parser,
        'verify': verify_profiler_args,
        'execute': execute_profiler_command,
    },
    'trigger': {
        'parse': add_trigger_parser,
        'verify': verify_trigger_args,
        'execute': execute_trigger_command,
    },
    'vm': {
        'parse': add_vm_parser,
        'verify': verify_vm_args,
        'execute': execute_vm_command,
    },
}


def create_parser():
  parser = argparse.ArgumentParser(
      prog='torq command',
      description=('Torq CLI tool for performance'
                   ' tests.'))
  # Global options
  # NOTE: All global options must have the 'nargs' option set to an int.
  parser.add_argument(
      '--serial',
      nargs=1,
      help=(('Specifies serial of the device that will be'
             ' used.')))

  subparsers = parser.add_subparsers(dest='subcommands', help='Subcommands')

  for command in TORQ_COMMANDS:
    TORQ_COMMANDS[command]['parse'](subparsers)

  # Set 'profiler' as the default parser
  parser.set_default_subparser('profiler')

  return parser


def verify_args(args):
  return TORQ_COMMANDS[args.subcommands]['verify'](args)


def execute_command(args, device):
  return TORQ_COMMANDS[args.subcommands]['execute'](args, device)


def print_error(error):
  print(error.message, file=sys.stderr)
  if error.suggestion is not None:
    print(f"Suggestion:\n\t{error.suggestion}", file=sys.stderr)


def run():
  parser = create_parser()
  args = parser.parse_args()
  if args.subcommands not in TORQ_COMMANDS:
    raise ValueError('Invalid command type used')
  args, error = verify_args(args)
  if error is not None:
    print_error(error)
    return
  serial = args.serial[0] if args.serial else None
  device = AdbDevice(serial)
  error = execute_command(args, device)
  if error is not None:
    print_error(error)
    return
