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
import io
from io import BytesIO
import socketserver
import unittest
import subprocess
import sys
import os
import webbrowser
from contextlib import redirect_stdout
from unittest import mock
from src.open_ui_utils import download_trace_processor, open_trace
from src.pinned_files import (PinnedDownloadError, TRACE_PROCESSOR_BASE_URL,
                              TRACE_PROCESSOR_FILES)
from tests.test_utils import generate_mock_completed_process, run_cli

ANDROID_BUILD_TOP = "/main"
TEST_FILE = "file.txtpb"
TEST_FILE_WITH_SHELL_METACHARACTERS = "/tmp/trace;touch injected;.perfetto-trace"
TEST_CACHE_DIR = "/home/user/.cache/torq/trace_processor/test-commit"
PERFETTO_BINARY = "/trace_processor"
CACHED_TRACE_PROCESSOR = TEST_CACHE_DIR + PERFETTO_BINARY
TEST_ERROR_MSG = "test-error"
ANDROID_PERFETTO_TOOLS_DIR = "/external/perfetto/tools"
ANDROID_TRACE_PROCESSOR = ANDROID_PERFETTO_TOOLS_DIR + PERFETTO_BINARY
LARGE_FILE_SIZE = 1024 * 1024 * 1024 * 4  # 4 GiB
WEB_UI_ADDRESS = "https://ui.perfetto.dev"


class OpenUiUnitTest(unittest.TestCase):

  def setUp(self):
    # Never touch the real cache directory or the network in unit tests.
    patches = {
        "cached_trace_processor_exists": False,
        "get_trace_processor_cache_dir": TEST_CACHE_DIR,
        "download_pinned_files": None,
    }
    self.mocks = {}
    for name, return_value in patches.items():
      patcher = mock.patch("src.open_ui_utils." + name, autospec=True)
      self.mocks[name] = patcher.start()
      self.mocks[name].return_value = return_value
      self.addCleanup(patcher.stop)
    self.mock_cached_exists = self.mocks["cached_trace_processor_exists"]
    self.mock_download = self.mocks["download_pinned_files"]

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_successfully(self, mock_input, mock_getsize,
                                                 mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "y"
    mock_exists.return_value = False
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, CACHED_TRACE_PROCESSOR)
    self.assertEqual(terminal_output.getvalue(), "")
    self.mock_download.assert_called_once_with(
        TRACE_PROCESSOR_BASE_URL,
        TRACE_PROCESSOR_FILES,
        TEST_CACHE_DIR,
        executables=TRACE_PROCESSOR_FILES.keys())

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_failed(self, mock_input, mock_getsize,
                                           mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "y"
    mock_exists.return_value = False
    self.mock_download.side_effect = PinnedDownloadError(TEST_ERROR_MSG)
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, None)
    self.assertEqual(
        terminal_output.getvalue(),
        "Could not download perfetto scripts (%s). Continuing.\n" %
        TEST_ERROR_MSG)

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_wrong_input(self, mock_input, mock_getsize,
                                                mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "bad-input"
    mock_exists.side_effect = [False, False]
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    error = download_trace_processor(TEST_FILE)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, "Invalid inputs.")
    self.assertEqual(error.suggestion, "Please accept or reject the download.")
    self.assertEqual(
        terminal_output.getvalue(), "Invalid input. Please try again.\n"
        "Invalid input. Please try again.\n")

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_refused(self, mock_input, mock_getsize,
                                            mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "n"
    mock_exists.side_effect = [False, False]
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, None)
    self.assertEqual(terminal_output.getvalue(),
                     "Will continue without downloading perfetto scripts.\n")

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(os.path, "abspath", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "expanduser", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_open_trace_scripts_large_file(self, mock_popen, mock_expanduser,
                                         mock_exists, mock_subprocess_run,
                                         mock_open_new_tab, mock_abspath,
                                         mock_getsize):
    mock_expanduser.return_value = ""
    mock_subprocess_run.return_value = generate_mock_completed_process()
    mock_open_new_tab.return_value = None
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_abspath.return_value = TEST_FILE
    mock_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output
    mock_process = mock_popen.return_value
    mock_process.stdout = BytesIO(b'Trace loaded')

    error = open_trace(TEST_FILE, WEB_UI_ADDRESS, False)

    mock_open_new_tab.assert_called()
    self.assertEqual(error, None)
    self.assertEqual(
        terminal_output.getvalue(), "\033[93m##### Loading trace. #####\n##### "
        "Follow the directions in the Perfetto UI. Do not exit "
        "out of torq until you are done viewing the trace. Press "
        "CTRL+C to exit torq and close the trace_processor. "
        "#####\033[0m\nProcess was killed.\n")

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_open_trace_scripts_large_file_use_trace_processor_enabled(
      self, mock_popen, mock_subprocess_run, mock_open_new_tab, mock_getsize,
      mock_exists):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    mock_open_new_tab.return_value = None
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output
    mock_process = mock_popen.return_value
    mock_process.stdout = BytesIO(b'Trace loaded')

    error = open_trace(TEST_FILE, WEB_UI_ADDRESS, True)

    mock_open_new_tab.assert_called()
    self.assertEqual(error, None)
    self.assertEqual(
        terminal_output.getvalue(), "\033[93m##### Loading trace. #####\n##### "
        "Follow the directions in the Perfetto UI. Do not exit "
        "out of torq until you are done viewing the trace. Press "
        "CTRL+C to exit torq and close the trace_processor. "
        "#####\033[0m\nProcess was killed.\n")

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch('src.torq.get_device', autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_open_trace_use_trace_processor_path_with_shell_metacharacters(
      self, mock_popen, mock_open_new_tab, mock_getsize, mock_exists,
      mock_get_device):
    mock_get_device.return_value = (None, None)
    mock_open_new_tab.return_value = None
    mock_getsize.return_value = 0
    mock_exists.return_value = True
    mock_popen.return_value.stdout = BytesIO(b'Trace loaded')

    with redirect_stdout(io.StringIO()):
      run_cli(f"torq open '{TEST_FILE_WITH_SHELL_METACHARACTERS}'"
              " --use_trace_processor")

    # The trace path must be passed as a single argument, without a shell.
    expected_args = [
        ANDROID_BUILD_TOP + ANDROID_TRACE_PROCESSOR, "--httpd",
        TEST_FILE_WITH_SHELL_METACHARACTERS
    ]
    mock_popen.assert_called_once_with(
        expected_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(socketserver, "TCPServer", autospec=True)
  def test_open_trace_scripts_small_file(self, mock_tcpserver,
                                         mock_open_new_tab, mock_getsize):

    def handle_request():
      mock_process.fname_get_completed = 0
      return

    mock_process = type('', (), {})()
    mock_process.handle_request = handle_request
    mock_tcpserver.return_value.__enter__.return_value = mock_process
    mock_open_new_tab.return_value = None
    mock_getsize.return_value = 0
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    error = open_trace(TEST_FILE, WEB_UI_ADDRESS, False)

    mock_open_new_tab.assert_called()
    self.assertEqual(error, None)
    self.assertEqual(terminal_output.getvalue(), "")

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_download_trace_processor_small_file_use_trace_processor_enabled(
      self, mock_popen, mock_subprocess_run, mock_open_new_tab, mock_getsize,
      mock_exists):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    mock_open_new_tab.return_value = None
    mock_getsize.return_value = 0
    mock_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output
    mock_process = mock_popen.return_value
    mock_process.stdout = BytesIO(b'Trace loaded')

    error = open_trace(TEST_FILE, WEB_UI_ADDRESS, True)

    mock_open_new_tab.assert_called()
    self.assertEqual(error, None)
    self.assertEqual(
        terminal_output.getvalue(), "\033[93m##### Loading trace. #####\n##### "
        "Follow the directions in the Perfetto UI. Do not exit "
        "out of torq until you are done viewing the trace. Press "
        "CTRL+C to exit torq and close the trace_processor. "
        "#####\033[0m\nProcess was killed.\n")

  @mock.patch.dict(
      os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  def test_download_trace_processor_android_scripts_exist(
      self, mock_getsize, mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path,
                     "%s%s" % (ANDROID_BUILD_TOP, ANDROID_TRACE_PROCESSOR))
    self.assertEqual(terminal_output.getvalue(), "")

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  def test_download_trace_processor_verified_cached_copy_exists(
      self, mock_getsize, mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_exists.return_value = True
    self.mock_cached_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, CACHED_TRACE_PROCESSOR)
    self.assertEqual(terminal_output.getvalue(), "")
    self.mock_download.assert_not_called()


if __name__ == '__main__':
  unittest.main()
