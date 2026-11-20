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
import enum
import os
import signal
import stat
import subprocess
import sys
import pathlib
import time

from .base import ValidationError

# Timing constants
POLLING_INTERVAL_SECS = 0.5

# File constants
TEXTPROTO_FILE_EXTENSIONS = [".txtpb", ".textproto", ".textpb", ".pbtxt"]

# Perfetto constants
PERFETTO_DEVICE_FOLDER = "/data/misc/perfetto-traces"
PERFETTO_TRACE_FILE = PERFETTO_DEVICE_FOLDER + "/trace.perfetto-trace"
PERFETTO_BOOT_TRACE_FILE = PERFETTO_DEVICE_FOLDER + "/boottrace.perfetto-trace"


class ShellExitCodes(enum.IntEnum):
  EX_SUCCESS = 0
  EX_FAILURE = 1
  EX_NOEXEC = 126
  EX_NOTFOUND = 127


def path_exists(path: str):
  if path is None:
    return False
  return os.path.exists(os.path.expanduser(path))


def is_file_path(path: str):
  path_obj = None
  try:
    path_obj = pathlib.Path(path)
    if path_obj.is_file():
      return True
  except Exception as e:
    return False


def dir_exists(path: str):
  if path is None:
    return False
  return os.path.isdir(os.path.expanduser(path))


def extract_port(address):
  """
  Extracts the port number from a TCP/IP or VSOCK address.
  """
  colon_idx = address.rfind(':')
  if colon_idx == -1:
    return None
  return address[colon_idx + 1:]


def are_mutually_exclusive(*args):
  """
  Returns true only if none or at most one of the args is not None.

  Used for guaranteeing mutual exclusivety of CLI arguments.
  """
  cnt = sum(arg is not None for arg in args)
  return cnt == 0 or cnt == 1


def poll_is_task_completed(timed_out_limit, interval, check_is_completed):
  start_time = time.time()
  while True:
    time.sleep(interval)
    if check_is_completed():
      return True
    if time.time() - start_time > timed_out_limit:
      return False


def _is_trusted_stat(st, euid, require_owner, allow_symlink=False):
  if require_owner and st.st_uid != euid:
    return False
  if allow_symlink and stat.S_ISLNK(st.st_mode):
    return True
  return not (st.st_mode & stat.S_IWOTH)


def _trusted_ancestor_uids(euid):
  trusted_uids = {euid, 0}
  try:
    with open("/proc/self/uid_map", "r") as f:
      uid_map = [line.split() for line in f if line.strip()]
    has_root_mapping = any(int(parts[0]) == 0 for parts in uid_map)
    if not has_root_mapping:
      with open("/proc/sys/kernel/overflowuid", "r") as f:
        trusted_uids.add(int(f.read().strip()))
  except (OSError, ValueError):
    pass
  return trusted_uids


def _has_trusted_ancestors(path, euid, require_owner):
  trusted_uids = _trusted_ancestor_uids(euid) if require_owner else None
  cur = os.path.dirname(path)
  while cur != path:
    st = os.lstat(cur)
    if require_owner and st.st_uid not in trusted_uids:
      return False
    if (not stat.S_ISLNK(st.st_mode) and (st.st_mode & stat.S_IWOTH) and
        not (st.st_mode & stat.S_ISVTX)):
      return False
    path = cur
    cur = os.path.dirname(path)
  return True


def _are_subtree_components_trusted(base, target, euid, require_owner,
                                    allow_symlinks):
  cur = base
  rel = os.path.relpath(target, base)
  parts = [] if rel == "." else rel.split(os.sep)
  for part in [None] + parts:
    if part is not None:
      cur = os.path.join(cur, part)
    if not _is_trusted_stat(os.lstat(cur), euid, require_owner, allow_symlinks):
      return False
  return True


def is_trusted_path(path, root_dir=None, require_owner=True):
  if not path:
    return False
  try:
    euid = os.geteuid()
    abs_target = os.path.abspath(os.path.expanduser(path))
    resolved_target = os.path.realpath(abs_target)

    if root_dir is not None:
      abs_root = os.path.abspath(os.path.expanduser(root_dir))
      resolved_root = os.path.realpath(abs_root)
      if (os.path.commonpath([abs_root, abs_target]) != abs_root or
          os.path.commonpath([resolved_root, resolved_target
                             ]) != resolved_root):
        return False
      if not _has_trusted_ancestors(abs_root, euid, require_owner):
        return False
      if (resolved_root != abs_root and
          not _has_trusted_ancestors(resolved_root, euid, require_owner)):
        return False
      if not _are_subtree_components_trusted(
          abs_root, abs_target, euid, require_owner, allow_symlinks=True):
        return False
      return _are_subtree_components_trusted(
          resolved_root,
          resolved_target,
          euid,
          require_owner,
          allow_symlinks=False)

    if not _has_trusted_ancestors(abs_target, euid, require_owner):
      return False
    if (resolved_target != abs_target and
        not _has_trusted_ancestors(resolved_target, euid, require_owner)):
      return False
    if not _is_trusted_stat(
        os.lstat(abs_target), euid, require_owner, allow_symlink=True):
      return False
    return _is_trusted_stat(
        os.lstat(resolved_target), euid, require_owner, allow_symlink=False)
  except OSError:
    return False


def convert_simpleperf_to_gecko(simpleperf_scripts_dir, host_raw_trace_filename,
                                host_gecko_trace_filename, symbols):
  expanded_symbols = os.path.expanduser(symbols)
  expanded_simpleperf_scripts_dir = os.path.expanduser(simpleperf_scripts_dir)
  env = os.environ.copy()
  existing_pythonpath = env.get("PYTHONPATH")
  env["PYTHONPATH"] = (
      f"{existing_pythonpath}{os.pathsep}{expanded_simpleperf_scripts_dir}"
      if existing_pythonpath else expanded_simpleperf_scripts_dir)
  print("Building binary cache, please wait. If no samples were recorded,"
        " the trace will be empty.")
  run_subprocess([
      os.path.join(expanded_simpleperf_scripts_dir, "binary_cache_builder.py"),
      "-i",
      host_raw_trace_filename,
      "-lib",
      expanded_symbols,
  ],
                 env=env)
  with open(host_gecko_trace_filename, "wb") as gecko_file:
    run_subprocess([
        os.path.join(expanded_simpleperf_scripts_dir,
                     "gecko_profile_generator.py"),
        "-i",
        host_raw_trace_filename,
    ],
                   stdout=gecko_file,
                   env=env)
  if not path_exists(host_gecko_trace_filename):
    raise Exception("Gecko file was not created.")


def wait_for_process_or_ctrl_c(process):

  def signal_handler(sig, frame):
    print("Exiting...")
    process.kill()
    sys.exit()

  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)

  process.wait()
  print("Process was killed.")


def wait_for_output(pattern, process, timeout):
  start_time = time.time()
  while time.time() - start_time < timeout:
    line = process.stdout.readline()
    if pattern in line.decode():
      process.stderr = None
      return False
  return True  # Timed out


def set_default_subparser(self, name):
  """
  A hack to add a default subparser to an argparse.ArgumentParser
  class. This will add the default subparser after all the global
  options in sys.argv.

  NOTE: Only works properly if all the global options have the
        'nargs' argument set to an integer.
  """
  subparser_found = False
  insertion_idx = 1
  is_non_global_option_found = False

  # Get all global options
  global_opts = {}
  for action in self._actions:
    for opt in action.option_strings:
      global_opts[opt] = action.nargs

  idx = 1
  while idx < len(sys.argv):
    arg = sys.argv[idx]
    if arg in global_opts:
      if is_non_global_option_found:
        # Because help is a global and non-global option, don't throw
        # when it is passed.
        if arg in ["-h", "--help"]:
          idx += global_opts[arg] + 1
          continue
        return ValidationError(
            ("Global options like %s must come before subcommand arguments." %
             arg), "Place global options at the beginning of the command.")
      # Current index + number of arguments + 1 gives the insertion index.
      insertion_idx = idx + global_opts[arg] + 1
      idx += global_opts[arg]
    else:
      is_non_global_option_found = True
    idx += 1

  for action in self._subparsers._actions:
    if not isinstance(action, argparse._SubParsersAction):
      continue
    if (insertion_idx < len(sys.argv) and
        sys.argv[insertion_idx] in action._name_parser_map.keys()):
      subparser_found = True
      break
  if not subparser_found:
    # insert default subparser
    sys.argv.insert(insertion_idx, name)

  return None


def is_bazel():
  return any("bazel-bin/torq.runfiles" in path for path in sys.path)


def run_subprocess(args,
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
  """
  Function to check for errors when calling subprocess.run. Will throw on all
  non-zero return codes except those included in ignore_returncodes. Check is
  always set to False because check_returncode() is manually called.
  """
  output = subprocess.run(
      args,
      shell=shell,
      capture_output=capture_output,
      stdin=stdin,
      input=input,
      stdout=stdout,
      stderr=stderr,
      cwd=cwd,
      timeout=timeout,
      check=False,
      encoding=encoding,
      errors=errors,
      text=text,
      env=env,
      universal_newlines=universal_newlines)
  if output.returncode and output.returncode not in ignore_returncodes:
    output.check_returncode()
  if capture_output:
    return output
  return None


class UniqueStore(argparse.Action):
  """
  Ensure a flag is specified no more than once.
  """

  def __call__(self, parser, namespace, values, option_string):
    if getattr(namespace, self.dest, self.default) is not self.default:
      parser.error(option_string + " can only be specified once")
    setattr(namespace, self.dest, values)
