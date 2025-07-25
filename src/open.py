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

from .command import Command
from .open_ui_utils import open_trace, WEB_UI_ADDRESS
from .utils import path_exists
from .validation_error import ValidationError

def add_open_parser(subparsers):
  open_parser = subparsers.add_parser('open',
                                      help=('The open subcommand is used '
                                            'to open trace files in the '
                                            'perfetto ui.'))
  open_parser.add_argument('file_path', help='Path to trace file.')
  open_parser.add_argument('--use_trace_processor', default=False,
                           action='store_true',
                                  help=('Enables using trace_processor to open '
                                        'the trace regardless of its size.'))


def verify_open_args(args):
  if not path_exists(args.file_path):
    return None, ValidationError(
        "Command is invalid because %s is an invalid file path."
        % args.file_path, "Make sure your file exists.")

  return args, None


class OpenCommand(Command):
  """
  Represents commands which open traces.
  """
  def __init__(self, file_path, use_trace_processor):
    super().__init__(type)
    self.file_path = file_path
    self.use_trace_processor = use_trace_processor

  def validate(self, device):
    raise NotImplementedError

  def execute(self, device):
    return open_trace(self.file_path, WEB_UI_ADDRESS, self.use_trace_processor)

