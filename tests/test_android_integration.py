#
# Copyright (C) 2026 The Android Open Source Project
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

import io
import unittest
import os
import sys
import shutil
import time
import subprocess

from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from src.shell import AdbShell
from tests.test_utils import run_cli
from perfetto.batch_trace_processor.api import BatchTraceProcessor
from unittest.mock import patch

BTP_QUERY = {
    "trace_duration":
        "SELECT (end_ts - start_ts) / 1e9 AS duration_sec FROM trace_bounds",
    "app_startup":
        "INCLUDE PERFETTO MODULE android.startup.startups;\n"
        "SELECT startup_id FROM android_startups\n"
        "WHERE package = '{package}'",
    "user_switch_event":
        "INCLUDE PERFETTO MODULE android.auto.multiuser;\n"
        "SELECT event_start_user_id, event_end_name "
        "FROM android_auto_multiuser_timing "
        "WHERE event_end_name LIKE 'finishUserStopped%'",
    "boot_events":
        "SELECT count(*) as count FROM android_logs\n"
        "WHERE msg LIKE '%sys.boot_completed=1%'",
    "unified_trace_machines":
        "SELECT COUNT(*) as m_count FROM machine;"
}

DUR_TOLERANCE = 0.1


class TorqIntegrationTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    if not AdbShell.adb_exists():
      raise RuntimeError(
          "Missing required executable: adb. Ensure it is in your PATH.")

    base_path = Path(os.environ.get('TEST_TMPDIR', '/tmp'))
    cls.parent_tmp_dir = base_path / f"torq-integration-test-{time.time_ns()}"
    cls.parent_tmp_dir.mkdir(parents=True, exist_ok=True)

    cls.serial = None
    cls.serial2 = None
    cls.primary_cid = None
    for arg in sys.argv:
      if arg.startswith("--serial="):
        cls.serial = arg.split("=")[1]
      elif arg.startswith("--serial2="):
        cls.serial2 = arg.split("=")[1]
      elif arg.startswith("--primary_cid="):
        cls.primary_cid = arg.split("=")[1]

    cls.assertNotEqual(cls.serial, cls.serial2,
                       "Both provided serials shouldn't be the same")

    cls.serials = AdbShell.get_adb_devices()
    if not cls.serials:
      raise RuntimeError("No active adb devices found via 'adb devices'.")

    if not cls.serial:
      print("INFO: No --serial provided. Auto-detecting via 'adb devices'...")
      cls.serial = cls.serials[0]
    elif cls.serial not in cls.serials:
      raise RuntimeError("Provided serial not found via 'adb devices'.")

    if cls.serial2 and cls.serial2 not in cls.serials:
      raise RuntimeError("Provided serial2 not found via 'adb devices'.")

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.parent_tmp_dir)

  def setUp(self):
    self.test_run_dir = self.parent_tmp_dir / self._testMethodName
    self.test_run_dir.mkdir(parents=True, exist_ok=True)

  def get_glob_files(self, pattern):
    return [str(f) for f in self.test_run_dir.glob(pattern)]

  def run_torq(self, command):
    output_io = io.StringIO()
    output_text = ""

    try:
      with redirect_stdout(output_io), redirect_stderr(output_io):
        run_cli(command)
    except SystemExit as e:
      if e.code != 0:
        self.fail(f"Torq exited with error code {e.code}."
                  f"Logs:\n{output_io.getvalue()}")
    except Exception as e:
      self.fail(f"Torq crashed with an unexpected exception: {e}")
    finally:
      output_text = output_io.getvalue()

    return output_text

  def validate_torq_output(self, output_text):
    error_keywords = ["Error:", "Exception:", "Failed to", "adb: error:"]
    for error in error_keywords:
      self.assertNotIn(
          error, output_text, f"Found '{error}' in output.\n"
          f"Full Logs: {output_text}")

    self.assertIn("Performing run ", output_text)

  def validate_trace_metadata(self, trace_files, num_traces=1):
    self.assertEqual(
        len(trace_files), num_traces,
        f"Expected {num_traces} .perfetto-trace file(s) in "
        f"{self.test_run_dir}, found {len(trace_files)}")

    for trace_file in trace_files:
      trace = Path(trace_file)
      self.assertGreater(trace.stat().st_size, 0,
                         f"Trace file {trace.name} is empty.")

  def validate_perfetto_output(self, output_text, num_traces=1):
    self.validate_torq_output(output_text)
    trace_files = self.get_glob_files("*.perfetto-trace")
    self.validate_trace_metadata(trace_files, num_traces)

    return trace_files

  def validate_trace_duration(self, btp, dur_sec):
    results = btp.query(BTP_QUERY["trace_duration"])
    self.assertIsNotNone(results[0]['duration_sec'].iloc[0])
    actual_duration = results[0]['duration_sec'].iloc[0]
    self.assertAlmostEqual(
        actual_duration,
        dur_sec,
        delta=DUR_TOLERANCE * dur_sec,
        msg=f"Trace should be ~{dur_sec} sec")

  def test_torq_basic_perfetto(self):
    dur_sec = 3
    torq_output = self.run_torq(f"torq --serial {self.serial} --no-ui -d "
                                f"{dur_sec * 1000} -o {self.test_run_dir}")

    trace_files = self.validate_perfetto_output(torq_output)
    with BatchTraceProcessor(trace_files) as btp:
      self.validate_trace_duration(btp, dur_sec)

  def test_torq_multiple_app_startup_events(self):
    num_runs = 3
    dur_sec = 3
    package = "com.android.car.settings"
    subprocess.run(
        ["adb", "-s", self.serial, "shell", "am", "force-stop", package])
    torq_output = self.run_torq(f"torq --serial {self.serial} -e app-startup "
                                f"-a {package} -d {dur_sec * 1000} --no-ui -o "
                                f"{self.test_run_dir} -r {num_runs}")
    trace_files = self.validate_perfetto_output(
        torq_output, num_traces=num_runs)

    with BatchTraceProcessor(trace_files) as btp:
      self.validate_trace_duration(btp, dur_sec)
      results = btp.query(BTP_QUERY["app_startup"].format(package=package))

      self.assertEqual(
          len(results), num_runs,
          f"Expected {num_runs} traces, got {len(results)}")

      for i, df in enumerate(results):
        self.assertGreater(
            len(df), 0,
            f"No valid startup_id for {package} in trace index {i}.")

        self.assertIsNotNone(df['startup_id'].iloc[0],
                             f"Startup ID should not be null in trace {i}")

  def test_torq_basic_simpleperf(self):
    dur_sec = 3

    if not os.environ.get('ANDROID_PRODUCT_OUT'):
      self.fail(f"ANDROID_PRODUCT_OUT missing in environment variables!")

    with patch('builtins.input', return_value='y'):
      torq_output = self.run_torq(
          f"torq --serial {self.serial} -p simpleperf -s cpu-clock --no-ui "
          f"-d {dur_sec * 1000} -o {self.test_run_dir}")

      self.validate_torq_output(torq_output)
      trace_files = self.get_glob_files("perf*.data*")
      self.validate_trace_metadata(trace_files)

    with BatchTraceProcessor(trace_files) as btp:
      self.validate_trace_duration(btp, dur_sec)

  def test_torq_user_switch(self):
    dur_sec = 15
    expected_from_user = subprocess.check_output(
        ["adb", "-s", self.serial, "shell", "am", "get-current-user"],
        text=True).strip()

    user_output = subprocess.check_output(
        ["adb", "-s", self.serial, "shell", "pm", "create-user", "TestUser"],
        text=True)
    expected_to_user = user_output.strip().split()[-1]

    torq_output = self.run_torq(
        f"torq --serial {self.serial} -e user-switch --to-user {expected_to_user} "
        f"--from-user {expected_from_user} -d {dur_sec * 1000} --no-ui "
        f"-o {self.test_run_dir}")

    trace_files = self.validate_perfetto_output(torq_output)
    with BatchTraceProcessor(trace_files) as btp:
      self.validate_trace_duration(btp, dur_sec)

      results = btp.query(BTP_QUERY["user_switch_event"])
      self.assertGreater(
          len(results[0]), 0, "No user-switch events found in trace.")

      event = results[0].iloc[0]
      actual_to_user = str(event['event_start_user_id'])
      event_name = event['event_end_name']

      actual_from_user = event_name.split('-')[1]

      self.assertEqual(
          actual_from_user, expected_from_user,
          f"The trace shows user {actual_from_user} was stopped, "
          f"but expected user {expected_from_user}")

      self.assertEqual(
          actual_to_user, expected_to_user,
          f"The trace shows user was switched to {actual_to_user}, "
          f"but we expected {expected_to_user}")

      current_user = subprocess.check_output(
          ["adb", "-s", self.serial, "shell", "am", "get-current-user"],
          text=True).strip()
      self.assertEqual(
          expected_from_user, current_user,
          f"The trace shows current user as {current_user}, "
          f"but expected {expected_from_user}")

      # Cleanup created user
      subprocess.run([
          "adb", "-s", self.serial, "shell", "pm", "remove-user",
          expected_to_user
      ])

  def test_torq_boot_event(self):
    dur_sec = 60

    self.run_torq(f"torq --serial {self.serial} -e boot --no-ui -d "
                  f"{dur_sec * 1000} -o {self.test_run_dir}")

    trace_files = self.get_glob_files("*.perfetto-trace")
    with BatchTraceProcessor(trace_files) as btp:
      self.validate_trace_duration(btp, dur_sec)
      boot_complete_logs = btp.query(
          BTP_QUERY["boot_events"])[0]['count'].iloc[0]

      self.assertGreater(boot_complete_logs, 0,
                         "Boot completion log not found.")

  def test_torq_vm_unified_tracing(self):
    dur_sec = 10

    if self.serial2 is None or self.primary_cid is None:
      self.skipTest(
          "serial2 and primary_cid must both be provided for VM unified tracing test. Skipping test"
      )

    subprocess.run(["adb", "-s", self.serial, "shell", "setenforce", "0"])
    subprocess.run(["adb", "-s", self.serial2, "shell", "setenforce", "0"])

    self.run_torq(
        f"torq --serial {self.serial} vm configure --primary android_primary="
        f"{self.serial} --primary-cid {self.primary_cid} --secondary "
        f"android_secondary={self.serial2}")

    time.sleep(2)

    self.run_torq(f"torq --serial {self.serial} --perfetto-config android-qnx "
                  f"-d {dur_sec * 1000} --no-ui -o {self.test_run_dir}")

    trace_files = self.get_glob_files("*.perfetto-trace")
    with BatchTraceProcessor(trace_files) as btp:
      trace_machines = btp.query(
          BTP_QUERY["unified_trace_machines"])[0]['m_count'].iloc[0]

      self.assertEqual(trace_machines, 2,
                       "Unified trace did not aggregate data from both VMs.")

    # Cleanup traced and traced-relay from devices setup during configure
    self.run_torq(f"torq --serial {self.serial} vm relay-producer disable")
    self.run_torq(f"torq --serial {self.serial2} vm traced-relay disable")


if __name__ == "__main__":
  test_args = [sys.argv[0]]
  for arg in sys.argv[1:]:
    if not (arg.startswith("--serial=") or arg.startswith("--serial2=") or
            arg.startswith("--primary_cid=")):
      test_args.append(arg)

  unittest.main(argv=test_args)
