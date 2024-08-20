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
import sys
from unittest import mock
from io import StringIO
from command import ProfilerCommand
from command_executor import ProfilerCommandExecutor
from device import AdbDevice
from torq import DEFAULT_DUR_MS, DEFAULT_OUT_DIR

MOCK_ERROR = "mock-error"
MOCK_CONFIG = "mock-config"
MOCK_EXCEPTION = Exception(MOCK_ERROR)
FIRST_RUN_TERMINAL_OUTPUT = "Performing run 1"
DEFAULT_PERFETTO_CONFIG = "default"


class ProfilerCommandExecutorUnitTest(unittest.TestCase):

  def setUp(self):
    self.mock_command = mock.create_autospec(
        ProfilerCommand, instance=True, out_dir=DEFAULT_OUT_DIR,
        perfetto_config=DEFAULT_PERFETTO_CONFIG)
    self.mock_device = mock.create_autospec(AdbDevice, instance=True)
    self.command_executor = ProfilerCommandExecutor()

  @mock.patch.object(sys, "stdout", new_callable=StringIO)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_command_one_run_and_use_ui_success(self, mock_process,
      mock_terminal_output):
    with mock.patch("command_executor.open_trace", autospec=True):
      self.mock_command.runs = 1
      self.mock_command.use_ui = True
      self.mock_command.dur_ms = DEFAULT_DUR_MS
      self.mock_command.excluded_ftrace_events = []
      self.mock_command.included_ftrace_events = []
      self.mock_device.start_perfetto_trace.return_value = mock_process

      error = self.command_executor.execute_command(self.mock_command,
                                                    self.mock_device)

      self.assertEqual(error, None)
      self.assertEqual(mock_terminal_output.getvalue().strip(),
                       FIRST_RUN_TERMINAL_OUTPUT)

  @mock.patch.object(sys, "stdout", new_callable=StringIO)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_command_one_run_no_ui_success(self, mock_process,
      mock_terminal_output):
    self.mock_command.runs = 1
    self.mock_command.use_ui = False
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = []
    self.mock_device.start_perfetto_trace.return_value = mock_process

    error = self.command_executor.execute_command(self.mock_command,
                                                  self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(mock_terminal_output.getvalue().strip(),
                     FIRST_RUN_TERMINAL_OUTPUT)

  def test_execute_command_create_config_no_dur_ms_error(self):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = None

    with self.assertRaises(ValueError) as e:
      self.command_executor.execute_command(self.mock_command, self.mock_device)

    self.assertEqual(str(e.exception),
                     "Cannot create config because a valid dur_ms was not set.")

  def test_execute_command_create_config_bad_excluded_ftrace_event_error(self):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = ["mock-ftrace-event"]
    self.mock_command.included_ftrace_events = []

    error = self.command_executor.execute_command(self.mock_command,
                                                  self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message,
                     ("Cannot remove ftrace event %s from config because it is"
                      " not one of the config's ftrace events."
                      % self.mock_command.excluded_ftrace_events[0]))
    self.assertEqual(error.suggestion, ("Please specify one of the following"
                                        " possible ftrace events:\n\t"
                                        " dmabuf_heap/dma_heap_stat\n\t"
                                        " ftrace/print\n\t"
                                        " gpu_mem/gpu_mem_total\n\t"
                                        " ion/ion_stat\n\t"
                                        " kmem/ion_heap_grow\n\t"
                                        " kmem/ion_heap_shrink\n\t"
                                        " kmem/rss_stat\n\t"
                                        " lowmemorykiller/lowmemory_kill\n\t"
                                        " mm_event/mm_event_record\n\t"
                                        " oom/mark_victim\n\t"
                                        " oom/oom_score_adj_update\n\t"
                                        " power/cpu_frequency\n\t"
                                        " power/cpu_idle\n\t"
                                        " power/gpu_frequency\n\t"
                                        " power/suspend_resume\n\t"
                                        " power/wakeup_source_activate\n\t"
                                        " power/wakeup_source_deactivate\n\t"
                                        " sched/sched_blocked_reason\n\t"
                                        " sched/sched_process_exit\n\t"
                                        " sched/sched_process_free\n\t"
                                        " sched/sched_switch\n\t"
                                        " sched/sched_wakeup\n\t"
                                        " sched/sched_wakeup_new\n\t"
                                        " sched/sched_waking\n\t"
                                        " task/task_newtask\n\t"
                                        " task/task_rename\n\t"
                                        " vmscan/*\n\t"
                                        " workqueue/*"))

  def test_execute_command_create_config_bad_included_ftrace_event_error(self):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = ["power/cpu_idle"]

    error = self.command_executor.execute_command(self.mock_command,
                                                  self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message,
                     ("Cannot add ftrace event %s to config because it is"
                      " already one of the config's ftrace events."
                      % self.mock_command.included_ftrace_events[0]))
    self.assertEqual(error.suggestion, ("Please do not specify any of the"
                                        " following ftrace events that are"
                                        " already included:\n\t"
                                        " dmabuf_heap/dma_heap_stat\n\t"
                                        " ftrace/print\n\t"
                                        " gpu_mem/gpu_mem_total\n\t"
                                        " ion/ion_stat\n\t"
                                        " kmem/ion_heap_grow\n\t"
                                        " kmem/ion_heap_shrink\n\t"
                                        " kmem/rss_stat\n\t"
                                        " lowmemorykiller/lowmemory_kill\n\t"
                                        " mm_event/mm_event_record\n\t"
                                        " oom/mark_victim\n\t"
                                        " oom/oom_score_adj_update\n\t"
                                        " power/cpu_frequency\n\t"
                                        " power/cpu_idle\n\t"
                                        " power/gpu_frequency\n\t"
                                        " power/suspend_resume\n\t"
                                        " power/wakeup_source_activate\n\t"
                                        " power/wakeup_source_deactivate\n\t"
                                        " sched/sched_blocked_reason\n\t"
                                        " sched/sched_process_exit\n\t"
                                        " sched/sched_process_free\n\t"
                                        " sched/sched_switch\n\t"
                                        " sched/sched_wakeup\n\t"
                                        " sched/sched_wakeup_new\n\t"
                                        " sched/sched_waking\n\t"
                                        " task/task_newtask\n\t"
                                        " task/task_rename\n\t"
                                        " vmscan/*\n\t"
                                        " workqueue/*"))

  def test_execute_command_prepare_device_for_run_root_failure(self):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = []
    self.mock_device.root_device.side_effect = MOCK_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command_executor.execute_command(self.mock_command, self.mock_device)

    self.assertEqual(str(e.exception), MOCK_ERROR)

  def test_execute_command_prepare_device_for_run_remove_file_failure(self):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = []
    self.mock_device.remove_file.side_effect = MOCK_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command_executor.execute_command(self.mock_command, self.mock_device)

    self.assertEqual(str(e.exception), MOCK_ERROR)

  def test_execute_command_execute_run_start_perfetto_trace_failure(self):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = []
    self.mock_device.start_perfetto_trace.side_effect = MOCK_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command_executor.execute_command(self.mock_command, self.mock_device)

    self.assertEqual(str(e.exception), MOCK_ERROR)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_command_execute_run_start_process_wait_failure(self,
      mock_process):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = []
    self.mock_device.start_perfetto_trace.return_value = mock_process
    mock_process.wait.side_effect = MOCK_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command_executor.execute_command(self.mock_command, self.mock_device)

    self.assertEqual(str(e.exception), MOCK_ERROR)

  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_command_retrieve_perf_data_pull_file_failure(self,
      mock_process):
    self.mock_command.runs = 1
    self.mock_command.dur_ms = DEFAULT_DUR_MS
    self.mock_command.excluded_ftrace_events = []
    self.mock_command.included_ftrace_events = []
    self.mock_device.start_perfetto_trace.return_value = mock_process
    self.mock_device.pull_file.side_effect = MOCK_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command_executor.execute_command(self.mock_command, self.mock_device)

    self.assertEqual(str(e.exception), MOCK_ERROR)


if __name__ == '__main__':
  unittest.main()
