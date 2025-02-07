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
from unittest import mock
from src.command import OpenCommand
from src.open_ui import download_trace_processor, open_trace

ANDROID_BUILD_TOP = "/main"
TEST_FILE = "file.pbtxt"
TORQ_TEMP_DIR = "/tmp/.torq"
PERFETTO_BINARY = "/trace_processor"
TORQ_TEMP_TRACE_PROCESSOR = TORQ_TEMP_DIR + PERFETTO_BINARY
ANDROID_PERFETTO_TOOLS_DIR = "/external/perfetto/tools"
ANDROID_TRACE_PROCESSOR = ANDROID_PERFETTO_TOOLS_DIR + PERFETTO_BINARY
LARGE_FILE_SIZE = 1024 * 1024 * 512  # 512 MB
WEB_UI_ADDRESS = "https://ui.perfetto.dev"


class OpenUiUnitTest(unittest.TestCase):
  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_successfully(self, mock_input,
      mock_subprocess_run, mock_getsize, mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "y"
    mock_exists.side_effect = [False, False, True]
    mock_subprocess_run.return_value = None
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, TORQ_TEMP_TRACE_PROCESSOR)
    self.assertEqual(terminal_output.getvalue(), "")

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_failed(self, mock_input,
      mock_subprocess_run, mock_getsize, mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "y"
    mock_exists.side_effect = [False, False, False]
    mock_subprocess_run.return_value = None
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, None)
    self.assertEqual(terminal_output.getvalue(),
                     "Could not download perfetto scripts. Continuing.\n")

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_download_trace_processor_wrong_input(self, mock_input,
      mock_getsize, mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_input.return_value = "bad-input"
    mock_exists.side_effect = [False, False]
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    error = download_trace_processor(TEST_FILE)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, "Invalid inputs.")
    self.assertEqual(error.suggestion, "Please accept or reject the download.")
    self.assertEqual(terminal_output.getvalue(),
                     "Invalid input. Please try again.\n"
                     "Invalid input. Please try again.\n"
                     "Invalid input. Please try again.\n")

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
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

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(os.path, "abspath", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "expanduser", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_open_trace_scripts_large_file(self, mock_popen, mock_expanduser,
      mock_exists, mock_subprocess_run, mock_open_new_tab, mock_abspath,
      mock_getsize):
    mock_expanduser.return_value = ""
    mock_subprocess_run.return_value = None
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
    self.assertEqual(terminal_output.getvalue(),
                     "\033[93m##### Loading trace. #####\n##### "
                     "Follow the directions in the Perfetto UI. Do not exit "
                     "out of torq until you are done viewing the trace. Press "
                     "CTRL+C to exit torq and close the trace_processor. "
                     "#####\033[0m\nProcess was killed.\n")

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_open_trace_scripts_large_file_use_trace_processor_enabled(self,
      mock_popen, mock_subprocess_run, mock_open_new_tab, mock_getsize,
      mock_exists):
    mock_subprocess_run.return_value = None
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
    self.assertEqual(terminal_output.getvalue(),
                     "\033[93m##### Loading trace. #####\n##### "
                     "Follow the directions in the Perfetto UI. Do not exit "
                     "out of torq until you are done viewing the trace. Press "
                     "CTRL+C to exit torq and close the trace_processor. "
                     "#####\033[0m\nProcess was killed.\n")

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

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  @mock.patch.object(webbrowser, "open_new_tab", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_download_trace_processor_small_file_use_trace_processor_enabled(self,
      mock_popen, mock_subprocess_run, mock_open_new_tab, mock_getsize,
      mock_exists):
    mock_subprocess_run.return_value = None
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
    self.assertEqual(terminal_output.getvalue(),
                     "\033[93m##### Loading trace. #####\n##### "
                     "Follow the directions in the Perfetto UI. Do not exit "
                     "out of torq until you are done viewing the trace. Press "
                     "CTRL+C to exit torq and close the trace_processor. "
                     "#####\033[0m\nProcess was killed.\n")

  @mock.patch.dict(os.environ, {"ANDROID_BUILD_TOP": ANDROID_BUILD_TOP},
                   clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  def test_download_trace_processor_android_scripts_exist(self, mock_getsize,
      mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, "%s%s"
                     % (ANDROID_BUILD_TOP, ANDROID_TRACE_PROCESSOR))
    self.assertEqual(terminal_output.getvalue(), "")

  @mock.patch.dict(os.environ, {}, clear=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "getsize", autospec=True)
  def test_download_trace_processor_temp_scripts_exist(self, mock_getsize,
      mock_exists):
    mock_getsize.return_value = LARGE_FILE_SIZE
    mock_exists.return_value = True
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    trace_processor_path = download_trace_processor(TEST_FILE)

    self.assertEqual(trace_processor_path, TORQ_TEMP_TRACE_PROCESSOR)
    self.assertEqual(terminal_output.getvalue(), "")

if __name__ == '__main__':
  unittest.main()
