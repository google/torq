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

import unittest
import shutil
import subprocess
import sys
import os

from unittest import mock
from src.utils import convert_simpleperf_to_gecko, get_python_interpreter
from tests.test_utils import create_parser_from_cli, generate_mock_completed_process

TEST_SCRIPTS_DIR = "/scripts"
TEST_RAW_TRACE = "/path/trace;touch injected;.data"
TEST_GECKO_TRACE = "/path/trace $(touch injected).json"
TEST_SYMBOLS = "/symbols"


class UtilsUnitTest(unittest.TestCase):

  @mock.patch("src.utils.open", new_callable=mock.mock_open, create=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_success(self, mock_exists,
                                               mock_subprocess_run, mock_open):
    mock_exists.return_value = True
    mock_subprocess_run.return_value = generate_mock_completed_process()

    convert_simpleperf_to_gecko(TEST_SCRIPTS_DIR, TEST_RAW_TRACE,
                                TEST_GECKO_TRACE, TEST_SYMBOLS)

    # The scripts run without a shell, with only the scripts directory on
    # PYTHONPATH, and paths are passed as single arguments.
    python = get_python_interpreter()
    builder_call, generator_call = mock_subprocess_run.call_args_list
    self.assertEqual(builder_call.args[0], [
        python, TEST_SCRIPTS_DIR + "/binary_cache_builder.py", "-i",
        TEST_RAW_TRACE, "-lib", TEST_SYMBOLS
    ])
    self.assertEqual(generator_call.args[0], [
        python, TEST_SCRIPTS_DIR + "/gecko_profile_generator.py", "-i",
        TEST_RAW_TRACE
    ])
    for call in (builder_call, generator_call):
      self.assertFalse(call.kwargs["shell"])
      self.assertEqual(call.kwargs["env"]["PYTHONPATH"], TEST_SCRIPTS_DIR)
    mock_open.assert_called_once_with(TEST_GECKO_TRACE, "w")
    self.assertEqual(generator_call.kwargs["stdout"], mock_open.return_value)

  @mock.patch("src.utils.open", new_callable=mock.mock_open, create=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_failure(self, mock_exists,
                                               mock_subprocess_run, mock_open):
    mock_exists.return_value = False
    mock_subprocess_run.return_value = generate_mock_completed_process()

    with self.assertRaises(Exception) as e:
      convert_simpleperf_to_gecko(TEST_SCRIPTS_DIR, TEST_RAW_TRACE,
                                  TEST_GECKO_TRACE, TEST_SYMBOLS)

    self.assertEqual(str(e.exception), "Gecko file was not created.")

  @mock.patch.object(sys, "frozen", True, create=True)
  @mock.patch.object(shutil, "which", autospec=True)
  def test_get_python_interpreter_frozen_executable(self, mock_which):
    mock_which.return_value = "/usr/bin/python3"

    self.assertEqual(get_python_interpreter(), "/usr/bin/python3")

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
