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
import subprocess
import os

from unittest import mock
from src.utils import convert_simpleperf_to_gecko
from tests.test_utils import create_parser_from_cli, generate_mock_completed_process


class UtilsUnitTest(unittest.TestCase):

  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_success(self, mock_exists,
                                               mock_subprocess_run):
    mock_exists.return_value = True
    mock_subprocess_run.return_value = generate_mock_completed_process()

    # No exception is expected to be thrown
    convert_simpleperf_to_gecko("/scripts", "/path/file.data",
                                "/path/file.json", "/symbols")

  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_convert_simpleperf_to_gecko_failure(self, mock_exists,
                                               mock_subprocess_run):
    mock_exists.return_value = False
    mock_subprocess_run.return_value = generate_mock_completed_process()

    with self.assertRaises(Exception) as e:
      convert_simpleperf_to_gecko("/scripts", "/path/file.data",
                                  "/path/file.json", "/symbols")

      self.assertEqual(str(e.exception), "Gecko file was not created.")

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

  def test_set_default_subparser_with_global_help(self):
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


if __name__ == '__main__':
  unittest.main()
