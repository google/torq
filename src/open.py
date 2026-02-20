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
import readline
from perfetto.batch_trace_processor.api import BatchTraceProcessor
from .base import ValidationError
from .open_ui_utils import open_trace, WEB_UI_ADDRESS


def add_open_parser(subparsers):
  open_parser = subparsers.add_parser(
      'open',
      help=('The open subcommand is used '
            'to open trace files in the '
            'perfetto ui.'))
  open_parser.add_argument(
      'file_path', nargs='+', help='Path to trace file or directory.')
  open_parser.add_argument(
      '--use_trace_processor',
      default=False,
      action='store_true',
      help=('Enables using trace_processor to open '
            'the trace regardless of its size.'))


def verify_open_args(args):
  valid_extensions = ('.pftrace', '.perfetto-trace')
  valid_files = []
  # When running with bazel run, the current working directory is changed to
  # the bazel sandbox. To correctly resolve relative paths, we need to use
  # the BUILD_WORKING_DIRECTORY environment variable.
  working_dir = os.environ.get("BUILD_WORKING_DIRECTORY", os.getcwd())

  for path in args.file_path:
    full_path = path
    if not os.path.isabs(path):
      full_path = os.path.join(working_dir, path)
    full_path = os.path.expanduser(full_path)

    if not os.path.exists(full_path):
      return None, ValidationError(
          f"Command is invalid because '{path}' is not a valid file or directory path.",
          "Make sure the path exists.")

    if os.path.isfile(full_path):
      if not full_path.endswith(valid_extensions):
        return None, ValidationError(
            f"Command is invalid because '{os.path.basename(path)}' is not a supported trace file format.",
            "Provide a path to a supported trace file format (e.g. .pftrace, .perfetto-trace)."
        )
      valid_files.append(full_path)
    elif os.path.isdir(full_path):
      for file in os.listdir(full_path):
        if file.endswith(valid_extensions):
          valid_files.append(os.path.join(full_path, file))

  if not valid_files:
    return None, ValidationError(
        "Command is invalid because no valid trace files were found in the provided paths.",
        "Make sure the provided paths contain at least one valid trace file (e.g. .pftrace, .perfetto-trace)."
    )

  args.file_path = sorted(list(set(valid_files)))
  return args, None


def execute_repl(traces):
  print(f"Loading {len(traces)} traces into torq...")
  try:
    with BatchTraceProcessor(traces) as btp:
      print("[torq REPL] - Type 'quit' to exit.")
      print("[torq REPL] - Separate lines with Enter (or Shift+Enter).")
      print("[torq REPL] - Press Enter on an empty line to execute.")
      query_lines = []
      while True:
        try:
          prompt = "> " if not query_lines else ".. "
          line = input(prompt)

          if line.strip().lower() in ("exit", "quit"):
            if not query_lines:
              break
            else:
              print(
                  "Discarding current query buffer. Type 'quit' again to exit.")
              query_lines = []
              continue

          if not line.strip():
            if query_lines:
              full_query = "\n".join(query_lines)
              df = btp.query_and_flatten(full_query)
              print(df.to_string())
              query_lines = []
            continue

          query_lines.append(line)
        except KeyboardInterrupt:
          print()  # Move to next line
          query_lines = []
          continue
        except EOFError:
          break
        except Exception as e:
          print(f"Error executing query: {e}")
          query_lines = []
  except Exception as e:
    print(f"Failed to initialize the torq REPL: {e}")
  print("Exiting")


def execute_open_command(args, device):
  if len(args.file_path) == 1:
    return open_trace(args.file_path[0], WEB_UI_ADDRESS,
                      args.use_trace_processor)
  else:
    execute_repl(args.file_path)
    return None
