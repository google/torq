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

import os
import stat
import subprocess
import tempfile
import unittest

from unittest import mock
from src.utils import convert_simpleperf_to_gecko, is_trusted_path
from tests.test_utils import create_parser_from_cli, generate_mock_completed_process


class UtilsUnitTest(unittest.TestCase):

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_success(self, mock_exists,
                                               mock_subprocess_run):
    mock_exists.return_value = True
    mock_subprocess_run.return_value = generate_mock_completed_process()

    with tempfile.TemporaryDirectory() as tmpdir:
      gecko_path = os.path.join(tmpdir, "file.json")
      convert_simpleperf_to_gecko("/scripts", "/path/file.data", gecko_path,
                                  "/symbols")

    self.assertEqual(mock_subprocess_run.call_count, 2)
    first_call, second_call = mock_subprocess_run.call_args_list
    self.assertEqual(first_call.args[0], [
        "/scripts/binary_cache_builder.py", "-i", "/path/file.data", "-lib",
        "/symbols"
    ])
    self.assertFalse(first_call.kwargs["shell"])
    self.assertEqual(first_call.kwargs["env"]["PYTHONPATH"], "/scripts")
    self.assertEqual(
        second_call.args[0],
        ["/scripts/gecko_profile_generator.py", "-i", "/path/file.data"])
    self.assertFalse(second_call.kwargs["shell"])
    self.assertEqual(second_call.kwargs["env"]["PYTHONPATH"], "/scripts")
    self.assertIsNotNone(second_call.kwargs["stdout"])

  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_failure(self, mock_exists,
                                               mock_subprocess_run):
    mock_exists.return_value = False
    mock_subprocess_run.return_value = generate_mock_completed_process()

    with tempfile.TemporaryDirectory() as tmpdir:
      gecko_path = os.path.join(tmpdir, "file.json")
      with self.assertRaises(Exception) as e:
        convert_simpleperf_to_gecko("/scripts", "/path/file.data", gecko_path,
                                    "/symbols")

      self.assertEqual(str(e.exception), "Gecko file was not created.")

  @mock.patch.dict(
      os.environ, {"PYTHONPATH": "/existing/pythonpath"}, clear=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_appends_pythonpath_and_preserves_metacharacters(
      self, mock_exists, mock_subprocess_run):
    mock_exists.return_value = True
    mock_subprocess_run.return_value = generate_mock_completed_process()
    malicious_symbols = "/tmp/symbols;touch /tmp/injected"
    malicious_trace = "/tmp/raw $(touch /tmp/injected).data"

    with tempfile.TemporaryDirectory() as tmpdir:
      gecko_path = os.path.join(tmpdir, "out;injected.json")
      convert_simpleperf_to_gecko("/scripts", malicious_trace, gecko_path,
                                  malicious_symbols)

    first_call, second_call = mock_subprocess_run.call_args_list
    self.assertEqual(first_call.args[0], [
        "/scripts/binary_cache_builder.py", "-i", malicious_trace, "-lib",
        malicious_symbols
    ])
    self.assertFalse(first_call.kwargs["shell"])
    self.assertEqual(first_call.kwargs["env"]["PYTHONPATH"],
                     f"/existing/pythonpath{os.pathsep}/scripts")
    self.assertEqual(
        second_call.args[0],
        ["/scripts/gecko_profile_generator.py", "-i", malicious_trace])
    self.assertFalse(second_call.kwargs["shell"])

  def test_is_trusted_path_valid_tree(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      os.chmod(tmpdir, 0o755)
      tools_dir = tmpdir
      for subdir in ("external", "perfetto", "tools"):
        tools_dir = os.path.join(tools_dir, subdir)
        os.mkdir(tools_dir, mode=0o755)
        os.chmod(tools_dir, 0o755)
      tp = os.path.join(tools_dir, "trace_processor")
      with open(tp, "w") as f:
        f.write("")
      os.chmod(tp, 0o755)

      self.assertTrue(is_trusted_path(tp, root_dir=tmpdir))

  def test_is_trusted_path_world_writable_file_and_dir_rejected(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      os.chmod(tmpdir, 0o755)
      tp = os.path.join(tmpdir, "trace_processor")
      with open(tp, "w") as f:
        f.write("")
      os.chmod(tp, 0o777)

      self.assertFalse(is_trusted_path(tp, root_dir=tmpdir))

      os.chmod(tp, 0o755)
      os.chmod(tmpdir, 0o777)
      self.assertFalse(is_trusted_path(tp, root_dir=tmpdir))

  def test_is_trusted_path_symlink_escape_rejected_and_internal_allowed(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      os.chmod(tmpdir, 0o755)
      with tempfile.TemporaryDirectory() as outside_dir:
        os.chmod(outside_dir, 0o755)
        outside_file = os.path.join(outside_dir, "evil")
        with open(outside_file, "w") as f:
          f.write("")
        os.chmod(outside_file, 0o755)
        escaping_link = os.path.join(tmpdir, "escape_tp")
        os.symlink(outside_file, escaping_link)

        self.assertFalse(is_trusted_path(escaping_link, root_dir=tmpdir))

      internal_target = os.path.join(tmpdir, "real_tp")
      with open(internal_target, "w") as f:
        f.write("")
      os.chmod(internal_target, 0o755)
      internal_link = os.path.join(tmpdir, "internal_tp")
      os.symlink(internal_target, internal_link)

      self.assertTrue(is_trusted_path(internal_link, root_dir=tmpdir))

  def test_is_trusted_path_symlink_ancestor_allowed(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      os.chmod(tmpdir, 0o755)
      real_parent = os.path.join(tmpdir, "real")
      os.mkdir(real_parent, mode=0o755)
      os.chmod(real_parent, 0o755)
      aosp = os.path.join(real_parent, "aosp")
      os.mkdir(aosp, mode=0o755)
      os.chmod(aosp, 0o755)
      tp = os.path.join(aosp, "trace_processor")
      with open(tp, "w") as f:
        f.write("")
      os.chmod(tp, 0o755)
      link_parent = os.path.join(tmpdir, "link")
      os.symlink(real_parent, link_parent)

      self.assertTrue(
          is_trusted_path(
              os.path.join(link_parent, "aosp", "trace_processor"),
              root_dir=os.path.join(link_parent, "aosp")))

  def test_is_trusted_path_wrong_owner_rejected(self):
    other_uid_stat = os.stat_result((stat.S_IFDIR | 0o755, 0, 0, 1,
                                     os.geteuid() + 1, os.getgid(), 0, 0, 0, 0))
    with mock.patch.object(os, "lstat", return_value=other_uid_stat):
      self.assertFalse(
          is_trusted_path(
              "/other/aosp/trace_processor", root_dir="/other/aosp"))

  def test_is_trusted_path_non_sticky_world_writable_ancestor_rejected(self):
    euid = os.geteuid()
    gid = os.getgid()
    own_dir_stat = os.stat_result(
        (stat.S_IFDIR | 0o755, 0, 0, 1, euid, gid, 0, 0, 0, 0))
    world_writable_parent_stat = os.stat_result(
        (stat.S_IFDIR | 0o777, 0, 0, 1, 0, gid, 0, 0, 0, 0))

    def fake_lstat(path):
      if path == "/shared":
        return world_writable_parent_stat
      return own_dir_stat

    with mock.patch.object(os, "lstat", side_effect=fake_lstat):
      self.assertFalse(
          is_trusted_path(
              "/shared/aosp/trace_processor", root_dir="/shared/aosp"))

  def test_is_trusted_path_wrong_owner_ancestor_rejected(self):
    euid = os.geteuid()
    gid = os.getgid()
    own_dir_stat = os.stat_result(
        (stat.S_IFDIR | 0o755, 0, 0, 1, euid, gid, 0, 0, 0, 0))
    other_owner_parent_stat = os.stat_result(
        (stat.S_IFDIR | 0o755, 0, 0, 1, euid + 1, gid, 0, 0, 0, 0))

    def fake_lstat(path):
      if path == "/shared":
        return other_owner_parent_stat
      return own_dir_stat

    with mock.patch.object(os, "lstat", side_effect=fake_lstat):
      self.assertFalse(
          is_trusted_path(
              "/shared/aosp/trace_processor", root_dir="/shared/aosp"))

  def test_is_trusted_path_require_owner_false_checks_world_writable(self):
    other_uid_stat = os.stat_result((stat.S_IFDIR | 0o755, 0, 0, 1,
                                     os.geteuid() + 1, os.getgid(), 0, 0, 0, 0))
    with mock.patch.object(os, "lstat", return_value=other_uid_stat):
      self.assertTrue(
          is_trusted_path("/shared/readonly/symbols", require_owner=False))

    with tempfile.TemporaryDirectory() as tmpdir:
      os.chmod(tmpdir, 0o755)
      self.assertTrue(is_trusted_path(tmpdir, require_owner=False))
      os.chmod(tmpdir, 0o1777)
      self.assertFalse(is_trusted_path(tmpdir, require_owner=False))
      os.chmod(tmpdir, 0o777)
      self.assertFalse(is_trusted_path(tmpdir, require_owner=False))

  def test_set_default_subparser(self):
    parser, error = create_parser_from_cli("torq --serial 0.0.0.0 -d 3000")

    self.assertNotEqual(parser, None)
    self.assertEqual(error, None)

    parser_args = vars(parser.parse_args())

    self.assertEqual(parser_args["serial"], ["0.0.0.0"])
    self.assertEqual(parser_args["subcommands"], "profiler")
    self.assertEqual(parser_args["dur_ms"], 3000)

  def test_set_default_subparser_with_global_option_after_non_global_option(
      self):
    parser, error = create_parser_from_cli("torq -d 3000 --serial 0.0.0.0")

    self.assertEqual(parser, None)
    self.assertNotEqual(error, None)
    self.assertEqual(
        error.message,
        ("Global options like --serial must come before subcommand arguments."))
    self.assertEqual(error.suggestion,
                     ("Place global options at the beginning of the command."))

  def test_set_default_subparser_with_help_after_non_global_option(self):
    parser, error = create_parser_from_cli("torq profiler -d 3000 --help")

    self.assertNotEqual(parser, None)
    self.assertEqual(error, None)

    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_set_non_default_subparser_with_help_after_non_global_option(self):
    parser, error = create_parser_from_cli("torq vm --help")

    self.assertNotEqual(parser, None)
    self.assertEqual(error, None)

    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_global_help(self):
    parser, error = create_parser_from_cli("torq --help")

    self.assertNotEqual(parser, None)
    self.assertEqual(error, None)

    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_set_default_subparser_with_subcommand_help(self):
    parser, error = create_parser_from_cli("torq profiler --help")

    self.assertNotEqual(parser, None)
    self.assertEqual(error, None)

    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_set_default_subparser_with_subcommand_as_argument(self):
    parser, error = create_parser_from_cli(
        "torq --included-ftrace-events trigger")

    self.assertNotEqual(parser, None)
    self.assertEqual(error, None)

    parser_args = vars(parser.parse_args())

    self.assertEqual(parser_args["subcommands"], "profiler")
    self.assertEqual(parser_args["included_ftrace_events"], ["trigger"])


if __name__ == '__main__':
  unittest.main()
