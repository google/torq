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
import shutil
import time
import subprocess

from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from src.shell import AdbShell
from tests.test_utils import run_cli
from perfetto.batch_trace_processor.api import BatchTraceProcessor

BTP_QUERY = {
    "trace_duration":
        "SELECT (end_ts - start_ts) / 1e9 AS duration_sec FROM trace_bounds",
    "app_startup":
        "INCLUDE PERFETTO MODULE android.startup.startups;\n"
        "SELECT startup_id FROM android_startups\n"
        "WHERE package = '{package}'"
}

DUR_TOLERANCE = 0.05


class TorqIntegrationTest(unittest.TestCase):

  @classmethod
  def _get_adb_device(cls):
    devices = AdbShell.get_adb_devices()

    if not devices:
      return None

    selected_device = devices[0]
    print(f"INFO: Found {len(devices)} device(s). Targeting: {selected_device}")
    return selected_device

  @classmethod
  def setUpClass(cls):
    if not AdbShell.adb_exists():
      raise RuntimeError(
          "Missing required executable: adb. Ensure it is in your PATH.")

    cls.serial = cls._get_adb_device()
    if not cls.serial:
      raise RuntimeError("No active adb devices found via 'adb devices'.")

    base_path = Path(os.environ.get('TEST_TMPDIR', '/tmp'))
    cls.parent_tmp_dir = base_path / f"torq-integration-test-{time.time_ns()}"
    cls.parent_tmp_dir.mkdir(parents=True, exist_ok=True)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.parent_tmp_dir)

  def setUp(self):
    self.test_run_dir = self.parent_tmp_dir / self._testMethodName
    self.test_run_dir.mkdir(parents=True, exist_ok=True)

  def get_trace_files(self):
    return [str(f) for f in self.test_run_dir.glob("*.perfetto-trace")]

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

  def validate_perfetto_output(self, output_text, num_traces=1):
    error_keywords = ["Error:", "Exception:", "Failed to", "adb: error:"]
    for error in error_keywords:
      self.assertNotIn(
          error, output_text, f"Found '{error}' in output.\n"
          f"Full Logs: {output_text}")

    self.assertIn("Performing run ", output_text)

    trace_files = list(self.test_run_dir.glob("*.perfetto-trace"))

    self.assertEqual(
        len(trace_files), num_traces,
        f"Expected {num_traces} .perfetto-trace file(s) in "
        f"{self.test_run_dir}, found {len(trace_files)}")

    for trace in trace_files:
      self.assertGreater(trace.stat().st_size, 0,
                         f"Trace file {trace.name} is empty.")

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

    self.validate_perfetto_output(torq_output)
    with BatchTraceProcessor(self.get_trace_files()) as btp:
      self.validate_trace_duration(btp, dur_sec)

  def test_torq_multiple_app_startup_events(self):
    num_runs = 3
    dur_sec = 3
    package = "com.android.car.radio"
    subprocess.run(
        ["adb", "-s", self.serial, "shell", "am", "force-stop", package])
    torq_output = self.run_torq(f"torq --serial {self.serial} -e app-startup "
                                f"-a {package} -d {dur_sec * 1000} --no-ui -o "
                                f"{self.test_run_dir} -r {num_runs}")
    self.validate_perfetto_output(torq_output, num_traces=num_runs)

    with BatchTraceProcessor(self.get_trace_files()) as btp:
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


if __name__ == "__main__":
  unittest.main()
