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

import builtins
import unittest
import os
import stat
import subprocess
from unittest import mock
from src.torq import verify_args
from tests.test_utils import generate_mock_completed_process, parse_cli

TORQ_TEMP_DIR = "/tmp/.torq"
ANDROID_BUILD_TOP = "/folder"
ANDROID_PRODUCT_OUT = "/folder/out/product/seahawk"
SYMBOLS_PATH = "/folder/symbols"
TRUSTED_DIR_STAT = os.stat_result(
    (stat.S_IFDIR | 0o755, 0, 0, 1, os.geteuid(), os.getgid(), 0, 0, 0, 0))


class ValidateSimpleperfUnitTest(unittest.TestCase):

  @mock.patch.object(os, "lstat", return_value=TRUSTED_DIR_STAT, autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.dict(
      os.environ, {
          "ANDROID_BUILD_TOP": ANDROID_BUILD_TOP,
          "ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT
      },
      clear=True)
  def test_create_parser_valid_symbols(self, mock_isdir, mock_exists,
                                       mock_lstat):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli("torq -p simpleperf "
                     "--symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.symbols, SYMBOLS_PATH)
    self.assertEqual(args.simpleperf_scripts_dir,
                     "%s/system/extras/simpleperf/scripts" % ANDROID_BUILD_TOP)

  @mock.patch.object(os, "lstat", return_value=TRUSTED_DIR_STAT, autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.dict(
      os.environ, {
          "ANDROID_BUILD_TOP": ANDROID_BUILD_TOP,
          "ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT
      },
      clear=True)
  def test_create_parser_valid_android_product_out_no_symbols(
      self, mock_isdir, mock_exists, mock_lstat):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.symbols, ANDROID_PRODUCT_OUT)
    self.assertEqual(args.simpleperf_scripts_dir,
                     "%s/system/extras/simpleperf/scripts" % ANDROID_BUILD_TOP)

  @mock.patch.dict(
      os.environ, {"ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_create_parser_invalid_android_product_no_symbols(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = False
    mock_exists.return_value = False
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(
        error.message,
        ("%s is not a valid $ANDROID_PRODUCT_OUT." % ANDROID_PRODUCT_OUT))
    self.assertEqual(
        error.suggestion, "Set --symbols to a valid symbols lib "
        "path or set $ANDROID_PRODUCT_OUT to "
        "your android product out directory "
        "(<ANDROID_BUILD_TOP>/out/target/product"
        "/<TARGET>).")

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_create_parser_invalid_symbols_no_android_product_out(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = False
    mock_exists.return_value = False
    args = parse_cli("torq -p simpleperf "
                     "--symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error.message, ("%s is not a valid path." % SYMBOLS_PATH))
    self.assertEqual(
        error.suggestion, "Set --symbols to a valid symbols lib "
        "path or set $ANDROID_PRODUCT_OUT to "
        "your android product out directory "
        "(<ANDROID_BUILD_TOP>/out/target/product"
        "/<TARGET>).")

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_create_parser_no_android_product_out_no_symbols(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = False
    mock_exists.return_value = False
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(error.message, "ANDROID_PRODUCT_OUT is not set.")
    self.assertEqual(
        error.suggestion, "Set --symbols to a valid symbols lib "
        "path or set $ANDROID_PRODUCT_OUT to "
        "your android product out directory "
        "(<ANDROID_BUILD_TOP>/out/target/"
        "product/<TARGET>).")

  @mock.patch.object(os, "lstat", return_value=TRUSTED_DIR_STAT, autospec=True)
  @mock.patch.dict(
      os.environ, {"ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_successfully_download_scripts(self, mock_input,
                                                       mock_subprocess_run,
                                                       mock_isdir, mock_exists,
                                                       mock_lstat):
    mock_isdir.return_value = True
    mock_input.return_value = "y"
    mock_exists.side_effect = [False, True, True, True, True]
    mock_subprocess_run.return_value = generate_mock_completed_process()
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.symbols, ANDROID_PRODUCT_OUT)
    self.assertEqual(args.simpleperf_scripts_dir, TORQ_TEMP_DIR)

  @mock.patch.object(os, "lstat", return_value=TRUSTED_DIR_STAT, autospec=True)
  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_failed_to_download_scripts(self, mock_input,
                                                    mock_subprocess_run,
                                                    mock_isdir, mock_exists,
                                                    mock_lstat):
    mock_isdir.return_value = True
    mock_input.return_value = "y"
    mock_exists.side_effect = [False, False, False]
    mock_subprocess_run.return_value = generate_mock_completed_process()
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    with self.assertRaises(Exception) as e:
      args, error = verify_args(args)

    self.assertEqual(
        str(e.exception), "Error while downloading simpleperf scripts. Try "
        "again or set $ANDROID_BUILD_TOP to your android root "
        "path and make sure you have $ANDROID_BUILD_TOP/system"
        "/extras/simpleperf/scripts downloaded.")

  @mock.patch.object(os, "lstat", return_value=TRUSTED_DIR_STAT, autospec=True)
  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_download_scripts_wrong_input(self, mock_input,
                                                      mock_isdir, mock_exists,
                                                      mock_lstat):
    mock_isdir.return_value = True
    mock_input.return_value = "bad-input"
    mock_exists.side_effect = [False, False]
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error.message, "Invalid inputs.")
    self.assertEqual(
        error.suggestion, "Set $ANDROID_BUILD_TOP to your android "
        "root path and make sure you have "
        "$ANDROID_BUILD_TOP/system/extras/"
        "simpleperf/scripts downloaded.")

  @mock.patch.object(os, "lstat", return_value=TRUSTED_DIR_STAT, autospec=True)
  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_download_scripts_refuse_download(
      self, mock_input, mock_isdir, mock_exists, mock_lstat):
    mock_isdir.return_value = True
    mock_input.return_value = "n"
    mock_exists.side_effect = [False, False]
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error.message, "Did not download simpleperf scripts.")
    self.assertEqual(
        error.suggestion, "Set $ANDROID_BUILD_TOP to your android "
        "root path and make sure you have "
        "$ANDROID_BUILD_TOP/system/extras/"
        "simpleperf/scripts downloaded.")

  @mock.patch.dict(
      os.environ, {
          "ANDROID_BUILD_TOP": ANDROID_BUILD_TOP,
          "ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT
      },
      clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_untrusted_android_build_top_world_writable_error(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    world_writable_stat = os.stat_result(
        (stat.S_IFDIR | 0o777, 0, 0, 1, os.geteuid(), os.getgid(), 0, 0, 0, 0))
    args = parse_cli("torq -p simpleperf")

    with mock.patch.object(os, "lstat", return_value=world_writable_stat):
      args, error = verify_args(args)

    self.assertEqual(args, None)
    self.assertEqual(
        error.message, "Refusing to use untrusted simpleperf scripts under "
        "$ANDROID_BUILD_TOP: %s/system/extras/simpleperf/scripts." %
        ANDROID_BUILD_TOP)

  @mock.patch.dict(
      os.environ, {
          "ANDROID_BUILD_TOP": ANDROID_BUILD_TOP,
          "ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT
      },
      clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_untrusted_android_build_top_wrong_owner_error(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    other_owner_stat = os.stat_result(
        (stat.S_IFDIR | 0o755, 0, 0, 1, os.geteuid() + 1, os.getgid(), 0, 0, 0,
         0))
    args = parse_cli("torq -p simpleperf")

    with mock.patch.object(os, "lstat", return_value=other_owner_stat):
      args, error = verify_args(args)

    self.assertEqual(args, None)
    self.assertEqual(
        error.message, "Refusing to use untrusted simpleperf scripts under "
        "$ANDROID_BUILD_TOP: %s/system/extras/simpleperf/scripts." %
        ANDROID_BUILD_TOP)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_untrusted_symbols_world_writable_error(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    world_writable_stat = os.stat_result(
        (stat.S_IFDIR | 0o777, 0, 0, 1, os.geteuid(), os.getgid(), 0, 0, 0, 0))
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    with mock.patch.object(os, "lstat", return_value=world_writable_stat):
      args, error = verify_args(args)

    self.assertEqual(args, None)
    self.assertEqual(
        error.message,
        "Refusing to use untrusted symbols path: %s." % SYMBOLS_PATH)

  @mock.patch.dict(
      os.environ, {"ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_untrusted_android_product_out_world_writable_error(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    world_writable_stat = os.stat_result(
        (stat.S_IFDIR | 0o777, 0, 0, 1, os.geteuid(), os.getgid(), 0, 0, 0, 0))
    args = parse_cli("torq -p simpleperf")

    with mock.patch.object(os, "lstat", return_value=world_writable_stat):
      args, error = verify_args(args)

    self.assertEqual(args, None)
    self.assertEqual(
        error.message, "Refusing to use untrusted $ANDROID_PRODUCT_OUT "
        "path: %s." % ANDROID_PRODUCT_OUT)


if __name__ == '__main__':
  unittest.main()
