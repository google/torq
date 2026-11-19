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
from unittest import mock
from src.pinned_files import (PinnedDownloadError, SIMPLEPERF_BASE_URL,
                              SIMPLEPERF_EXECUTABLES, get_simpleperf_files)
from src.torq import verify_args
from src.validate_simpleperf import BUNDLED_SIMPLEPERF_SCRIPTS_DIR
from tests.test_utils import parse_cli

TEST_CACHE_DIR = "/home/user/.cache/torq/simpleperf/test-commit"
TEST_ERROR_MSG = "test-error"
ANDROID_BUILD_TOP = "/folder"
ANDROID_PRODUCT_OUT = "/folder/out/product/seahawk"
SYMBOLS_PATH = "/folder/symbols"


class ValidateSimpleperfUnitTest(unittest.TestCase):

  def setUp(self):
    # Never touch the real cache directory or the network in unit tests.
    patches = {
        "bundled_simpleperf_scripts_exist": False,
        "cached_simpleperf_scripts_exist": False,
        "get_simpleperf_cache_dir": TEST_CACHE_DIR,
        "ensure_private_dir": None,
        "download_pinned_files": None,
    }
    self.mocks = {}
    for name, return_value in patches.items():
      patcher = mock.patch("src.validate_simpleperf." + name, autospec=True)
      self.mocks[name] = patcher.start()
      self.mocks[name].return_value = return_value
      self.addCleanup(patcher.stop)
    self.mock_bundled_exist = self.mocks["bundled_simpleperf_scripts_exist"]
    self.mock_cached_exist = self.mocks["cached_simpleperf_scripts_exist"]
    self.mock_ensure_private_dir = self.mocks["ensure_private_dir"]
    self.mock_download = self.mocks["download_pinned_files"]

  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.dict(
      os.environ, {
          "ANDROID_BUILD_TOP": ANDROID_BUILD_TOP,
          "ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT
      },
      clear=True)
  def test_create_parser_valid_symbols(self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli("torq -p simpleperf "
                     "--symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.symbols, SYMBOLS_PATH)
    self.assertEqual(args.simpleperf_scripts_dir,
                     "%s/system/extras/simpleperf/scripts" % ANDROID_BUILD_TOP)

  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.dict(
      os.environ, {
          "ANDROID_BUILD_TOP": ANDROID_BUILD_TOP,
          "ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT
      },
      clear=True)
  def test_create_parser_valid_android_product_out_no_symbols(
      self, mock_isdir, mock_exists):
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

  @mock.patch.dict(
      os.environ, {"ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_create_parser_uses_bundled_scripts(self, mock_isdir):
    mock_isdir.return_value = True
    self.mock_bundled_exist.return_value = True
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.simpleperf_scripts_dir,
                     BUNDLED_SIMPLEPERF_SCRIPTS_DIR)
    self.mock_download.assert_not_called()

  @mock.patch.dict(
      os.environ, {"ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_uses_verified_cached_scripts(self, mock_input,
                                                      mock_isdir):
    mock_isdir.return_value = True
    self.mock_cached_exist.return_value = True
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.simpleperf_scripts_dir, TEST_CACHE_DIR)
    mock_input.assert_not_called()
    self.mock_download.assert_not_called()

  @mock.patch.dict(
      os.environ, {"ANDROID_PRODUCT_OUT": ANDROID_PRODUCT_OUT}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_successfully_download_scripts(self, mock_input,
                                                       mock_isdir):
    mock_isdir.return_value = True
    mock_input.return_value = "y"
    args = parse_cli("torq -p simpleperf")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.symbols, ANDROID_PRODUCT_OUT)
    self.assertEqual(args.simpleperf_scripts_dir, TEST_CACHE_DIR)
    self.mock_download.assert_called_once_with(
        SIMPLEPERF_BASE_URL,
        get_simpleperf_files(),
        TEST_CACHE_DIR,
        executables=SIMPLEPERF_EXECUTABLES)

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_failed_to_download_scripts(self, mock_input,
                                                    mock_isdir):
    mock_isdir.return_value = True
    mock_input.return_value = "y"
    self.mock_download.side_effect = PinnedDownloadError(TEST_ERROR_MSG)
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(args, None)
    self.assertEqual(
        error.message,
        "Error while downloading simpleperf scripts: %s" % TEST_ERROR_MSG)
    self.assertEqual(
        error.suggestion, "Try again or set $ANDROID_BUILD_TOP to your "
        "android root path and make sure you have $ANDROID_BUILD_TOP/system"
        "/extras/simpleperf/scripts downloaded.")

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_create_parser_cache_dir_not_private_error(self, mock_isdir):
    mock_isdir.return_value = True
    self.mock_ensure_private_dir.side_effect = PinnedDownloadError(
        TEST_ERROR_MSG)
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(args, None)
    self.assertEqual(error.message,
                     "Cannot use the torq cache directory: %s" % TEST_ERROR_MSG)
    self.mock_download.assert_not_called()

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_download_scripts_wrong_input(self, mock_input,
                                                      mock_isdir):
    mock_isdir.return_value = True
    mock_input.return_value = "bad-input"
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error.message, "Invalid inputs.")
    self.assertEqual(
        error.suggestion, "Set $ANDROID_BUILD_TOP to your android "
        "root path and make sure you have "
        "$ANDROID_BUILD_TOP/system/extras/"
        "simpleperf/scripts downloaded.")
    self.mock_download.assert_not_called()

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_create_parser_download_scripts_refuse_download(
      self, mock_input, mock_isdir):
    mock_isdir.return_value = True
    mock_input.return_value = "n"
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error.message, "Did not download simpleperf scripts.")
    self.assertEqual(
        error.suggestion, "Set $ANDROID_BUILD_TOP to your android "
        "root path and make sure you have "
        "$ANDROID_BUILD_TOP/system/extras/"
        "simpleperf/scripts downloaded.")
    self.mock_download.assert_not_called()


if __name__ == '__main__':
  unittest.main()
