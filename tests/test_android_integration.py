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
import re
import unittest
import os
import shutil
import time

from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from src.shell import AdbShell
from tests.test_utils import run_cli


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

  def test_torq_basic_perfetto(self):
    output_io = io.StringIO()

    try:
      with redirect_stdout(output_io), redirect_stderr(output_io):
        run_cli(f"torq --serial {self.serial} -d 3000 "
                f"--no-ui -o {self.test_run_dir}")
    except SystemExit as e:
      if e.code != 0:
        self.fail(f"Torq exited with error code {e.code}."
                  f"Logs:\n{output_io.getvalue()}")
    except Exception as e:
      self.fail(f"Torq crashed with an unexpected exception: {e}")
    finally:
      output_text = output_io.getvalue()

    error_keywords = ["Error:", "Exception:", "Failed to", "adb: error:"]
    for keyword in error_keywords:
      self.assertNotIn(
          keyword, output_text, f"Found '{keyword}' in output.\n"
          f"Full Logs: {output_text}")

    self.assertIn("Performing run ", output_text)

    duration_match = re.search(r"Run lasted for (\d+\.\d+) seconds\.",
                               output_text)
    self.assertIsNotNone(
        duration_match,
        f"Could not find duration summary in output.\nFull Logs: {output_text}")

    actual_duration = float(duration_match.group(1))
    self.assertGreaterEqual(
        actual_duration, 3.0,
        f"Torq reported a duration of {actual_duration}s (expected >= 3.0s).")

    trace_files = list(self.test_run_dir.glob("*.perfetto-trace"))
    self.assertEqual(
        len(trace_files), 1,
        f"Expected 1 .perfetto-trace file in {self.test_run_dir}, found {len(trace_files)}"
    )

    trace = trace_files[0]
    file_size = trace.stat().st_size
    self.assertGreater(file_size, 0, f"Trace file {trace.name} is empty.")


if __name__ == "__main__":
  unittest.main()
