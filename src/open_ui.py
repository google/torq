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
# Implementation taken from external/perfetto/tools/record_android_trace.
#

import webbrowser
import socketserver
import http.server
import os
import subprocess
from .handle_input import HandleInput
from .utils import path_exists, wait_for_process_or_ctrl_c, wait_for_output
from .validation_error import ValidationError

TORQ_TEMP_DIR = "/tmp/.torq"
TRACE_PROCESSOR_BINARY = "/trace_processor"
TORQ_TEMP_TRACE_PROCESSOR = TORQ_TEMP_DIR + TRACE_PROCESSOR_BINARY
ANDROID_PERFETTO_TOOLS_DIR = "/external/perfetto/tools"
ANDROID_TRACE_PROCESSOR = ANDROID_PERFETTO_TOOLS_DIR + TRACE_PROCESSOR_BINARY
LARGE_FILE_SIZE = 1024 * 1024 * 512  # 512 MB
WAIT_FOR_TRACE_PROCESSOR_MS = 3000


class HttpHandler(http.server.SimpleHTTPRequestHandler):

  def end_headers(self):
    self.send_header("Access-Control-Allow-Origin", self.server.allow_origin)
    self.send_header("Cache-Control", "no-cache")
    super().end_headers()

  def do_GET(self):
    if self.path != "/" + self.server.expected_fname:
      self.send_error(404, "File not found")
      return
    self.server.fname_get_completed = True
    super().do_GET()

  def do_POST(self):
    self.send_error(404, "File not found")

  def log_message(self, format, *args):
    pass

def download_trace_processor(path):
  if (("ANDROID_BUILD_TOP" in os.environ and
       path_exists(os.environ["ANDROID_BUILD_TOP"] + ANDROID_TRACE_PROCESSOR))):
    return os.environ["ANDROID_BUILD_TOP"] + ANDROID_TRACE_PROCESSOR
  if path_exists(TORQ_TEMP_TRACE_PROCESSOR):
    return TORQ_TEMP_TRACE_PROCESSOR

  def download_accepted_callback():
    subprocess.run(("mkdir -p %s && wget -P %s "
                    "https://get.perfetto.dev/trace_processor && chmod +x "
                    "%s/trace_processor"
                    % (TORQ_TEMP_DIR, TORQ_TEMP_DIR, TORQ_TEMP_DIR)),
                   shell=True)

    if not path_exists(TORQ_TEMP_TRACE_PROCESSOR):
      print("Could not download perfetto scripts. Continuing.")
      return None

    return TORQ_TEMP_TRACE_PROCESSOR

  def rejected_callback():
    print("Will continue without downloading perfetto scripts.")
    return None

  input_handler = HandleInput("You do not have $ANDROID_BUILD_TOP configured "
                              "with the $ANDROID_BUILD_TOP%s directory.\nYour "
                              "perfetto trace is larger than 512MB, so "
                              "attempting to load the trace in the perfetto UI "
                              "without the perfetto scripts might not work.\n"
                              "torq can download the perfetto scripts to '%s'. "
                              "Are you ok with this download? [Y/N]: "
                              % (ANDROID_PERFETTO_TOOLS_DIR, TORQ_TEMP_DIR),
                              "Please accept or reject the download.",
                              download_accepted_callback, rejected_callback)

  return input_handler.handle_input()

def open_trace(path, origin, use_trace_processor):
  PORT = 9001
  path = os.path.abspath(path)
  if os.path.getsize(path) >= LARGE_FILE_SIZE or use_trace_processor:
    trace_processor_path = download_trace_processor(path)
    if isinstance(trace_processor_path, ValidationError):
      return trace_processor_path
    if trace_processor_path is not None:
      process = subprocess.Popen("%s --httpd %s" % (trace_processor_path, path),
                                 shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
      print("\033[93m##### Loading trace. #####")
      if wait_for_output("Trace loaded", process,
                         WAIT_FOR_TRACE_PROCESSOR_MS):
        process.kill()
        return ValidationError("Trace took too long to load.",
                               "Please try again.")
      webbrowser.open_new_tab(origin)
      print("##### Follow the directions in the Perfetto UI. Do not "
            "exit out of torq until you are done viewing the trace. Press "
            "CTRL+C to exit torq and close the trace_processor. #####\033[0m")
      wait_for_process_or_ctrl_c(process)

  else: # Open trace directly in UI
    os.chdir(os.path.dirname(path))
    fname = os.path.basename(path)
    socketserver.TCPServer.allow_reuse_address = True
    with (socketserver.TCPServer(("127.0.0.1", PORT), HttpHandler)
          as httpd):
      address = (f"{origin}/#!/?url=http://127.0.0.1:"
                 f"{PORT}/{fname}&referrer=open_trace_in_ui")
      webbrowser.open_new_tab(address)
      httpd.expected_fname = fname
      httpd.fname_get_completed = None
      httpd.allow_origin = origin
      while httpd.fname_get_completed is None:
        httpd.handle_request()
  return None
