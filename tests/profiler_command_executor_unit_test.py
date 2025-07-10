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

import os
import unittest
import signal
import subprocess
from unittest import mock
from src.command import ProfilerCommand
from src.device import AdbDevice
from src.validation_error import ValidationError
from src.torq import DEFAULT_DUR_MS, DEFAULT_OUT_DIR
from tests.test_utils import parameterized_profiler

PROFILER_COMMAND_TYPE = "profiler"
TEST_ERROR_MSG = "test-error"
TEST_EXCEPTION = Exception(TEST_ERROR_MSG)
TEST_VALIDATION_ERROR = ValidationError(TEST_ERROR_MSG, None)
TEST_SERIAL = "test-serial"
DEFAULT_PERFETTO_CONFIG = "default"
TEST_USER_ID_1 = 0
TEST_USER_ID_2 = 1
TEST_USER_ID_3 = 2
TEST_PACKAGE_1 = "test-package-1"
TEST_PACKAGE_2 = "test-package-2"
TEST_PACKAGE_3 = "test-package-3"
TEST_DURATION = 0
ANDROID_SDK_VERSION_S = 32
ANDROID_SDK_VERSION_T = 33


class ProfilerCommandExecutorUnitTest(unittest.TestCase):

  def setUpSubtest(self, profiler):
    self.command = ProfilerCommand(
        PROFILER_COMMAND_TYPE, "custom", profiler, DEFAULT_OUT_DIR,
        DEFAULT_DUR_MS, None, 1, None, DEFAULT_PERFETTO_CONFIG, None, False,
        None, None, None, None, None, None)
    if profiler == "simpleperf":
      self.command.symbols = "/"
      self.command.scripts_path = "/"
    self.mock_device = mock.create_autospec(AdbDevice, instance=True,
                                            serial=TEST_SERIAL)
    self.mock_device.check_device_connection.return_value = None
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)
    self.mock_device.create_directory.return_value = None

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_one_profiler_run_and_use_ui_success(self, profiler,
      mock_exists, mock_process, mock_run):
    with (mock.patch("src.command_executor.open_trace", autospec=True)
          as mock_open_trace):
      mock_open_trace.return_value = None
      self.command.use_ui = True
      if profiler == "perfetto":
        self.mock_device.start_perfetto_trace.side_effect = mock_process
      else:
        self.mock_device.start_simpleperf_trace.side_effect = mock_process
      mock_exists.return_value = True
      mock_run.return_value = None

      error = self.command.execute(self.mock_device)

      self.assertEqual(error, None)
      self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_one_profiler_run_no_dur_ms_success(self, profiler,
      mock_exists, mock_process, mock_run):
    def poll():
      # Send the SIGINT signal to the process to simulate a user pressing CTRL+C
      os.kill(os.getpid(), signal.SIGINT)
      return None

    with (mock.patch("src.command_executor.open_trace", autospec=True)
          as mock_open_trace):
      self.command.dur_ms = None
      mock_open_trace.return_value = None
      mock_process.poll = poll
      if profiler == "perfetto":
        self.mock_device.start_perfetto_trace.side_effect = mock_process
      else:
        self.mock_device.start_simpleperf_trace.side_effect = mock_process
      mock_exists.return_value = True
      mock_run.return_value = None

      error = self.command.execute(self.mock_device)

      self.assertEqual(error, None)
      self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_one_simpleperf_run_failure(self, mock_exists, mock_process,
      mock_run):
    self.setUpSubtest("simpleperf")
    with (mock.patch("src.command_executor.open_trace", autospec=True)
          as mock_open_trace):
      mock_open_trace.return_value = None
      self.mock_device.start_simpleperf_trace.return_value = mock_process
      mock_exists.return_value = False
      mock_run.return_value = None
      self.command.use_ui = True

      with self.assertRaises(Exception) as e:
        self.command.execute(self.mock_device)

      self.assertEqual(str(e.exception), "Gecko file was not created.")

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_one_profiler_run_no_ui_success(self, profiler, mock_exists,
      mock_process, mock_run):
    self.command.use_ui = False
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.side_effect = mock_process
    else:
      self.mock_device.start_simpleperf_trace.side_effect = mock_process
    mock_exists.return_value = True
    mock_run.return_value = None

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_check_device_connection_failure(self, profiler, mock_exists,
      mock_run):
    self.mock_device.check_device_connection.side_effect = TEST_EXCEPTION
    mock_exists.return_value = True
    mock_run.return_value = None

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_root_device_failure(self, profiler):
    self.mock_device.root_device.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_create_default_config_bad_excluded_ftrace_event_error(self,
      profiler):
    self.command.excluded_ftrace_events = ["mock-ftrace-event"]

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message,
                     ("Cannot remove ftrace event %s from config because it is"
                      " not one of the config's ftrace events."
                      % self.command.excluded_ftrace_events[0]))
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
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_create_default_config_bad_included_ftrace_event_error(self,
      profiler):
    self.command.included_ftrace_events = ["power/cpu_idle"]

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message,
                     ("Cannot add ftrace event %s to config because it is"
                      " already one of the config's ftrace events."
                      % self.command.included_ftrace_events[0]))
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
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_remove_file_failure(self, profiler):
    self.mock_device.remove_file.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_start_profiler_trace_failure(self, profiler):
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.side_effect = TEST_EXCEPTION
    else:
      self.mock_device.start_simpleperf_trace.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_process_poll_failure(self, profiler, mock_process):
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.side_effect = TEST_EXCEPTION
    else:
      self.mock_device.start_simpleperf_trace.side_effect = TEST_EXCEPTION
    mock_process.poll.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_pull_file_failure(self, profiler, mock_process):
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.side_effect = mock_process
    else:
      self.mock_device.start_simpleperf_trace.side_effect = mock_process
    self.mock_device.pull_file.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)


class UserSwitchCommandExecutorUnitTest(unittest.TestCase):

  def simulate_user_switch(self, user):
    self.current_user = user

  def setUpSubtest(self, profiler):
    self.command = ProfilerCommand(
        PROFILER_COMMAND_TYPE, "user-switch", profiler, DEFAULT_OUT_DIR,
        DEFAULT_DUR_MS, None, 1, None, DEFAULT_PERFETTO_CONFIG, None, False,
        None, None, None, None, None, None)
    self.current_user = TEST_USER_ID_3
    if profiler == "simpleperf":
      self.command.symbols = "/"
      self.command.scripts_path = "/"
    self.mock_device = mock.create_autospec(AdbDevice, instance=True,
                                            serial=TEST_SERIAL)
    self.mock_device.check_device_connection.return_value = None
    self.mock_device.user_exists.return_value = None
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)
    self.mock_device.get_current_user.side_effect = lambda: self.current_user
    self.mock_device.create_directory.return_value = None

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_all_users_different_success(self, profiler, mock_exists,
      mock_process, mock_run):
    self.command.from_user = TEST_USER_ID_1
    self.command.to_user = TEST_USER_ID_2
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.return_value = mock_process
    else:
      self.mock_device.start_simpleperf_trace.return_value = mock_process
    self.mock_device.perform_user_switch.side_effect = (
        lambda user: self.simulate_user_switch(user))
    mock_exists.return_value = True
    mock_run.return_value = None

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.current_user, TEST_USER_ID_3)
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 3)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  def test_execute_perform_user_switch_failure(self, profiler, mock_process):
    self.command.from_user = TEST_USER_ID_2
    self.command.to_user = TEST_USER_ID_1
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.return_value = mock_process
    else:
      self.mock_device.start_simpleperf_trace.return_value = mock_process
    self.mock_device.perform_user_switch.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_to_user_is_from_user_error(self, profiler):
    self.command.from_user = TEST_USER_ID_1
    self.command.to_user = TEST_USER_ID_1

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, ("Cannot perform user-switch to user %s"
                                     " because the current user on device"
                                     " %s is already %s."
                                     % (TEST_USER_ID_1, TEST_SERIAL,
                                        TEST_USER_ID_1)))
    self.assertEqual(error.suggestion, ("Choose a --to-user ID that is"
                                        " different than the --from-user ID."))
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_from_user_empty_success(self, profiler, mock_exists,
      mock_process, mock_run):
    self.command.from_user = None
    self.command.to_user = TEST_USER_ID_2
    self.mock_device.start_perfetto_trace.return_value = mock_process
    self.mock_device.perform_user_switch.side_effect = (
        lambda user: self.simulate_user_switch(user))
    mock_exists.return_value = True
    mock_run.return_value = None

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.current_user, TEST_USER_ID_3)
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 2)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_execute_to_user_is_current_user_and_from_user_empty_error(self,
      profiler):
    self.command.from_user = None
    self.command.to_user = self.current_user

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, ("Cannot perform user-switch to user %s"
                                     " because the current user on device"
                                     " %s is already %s."
                                     % (self.current_user, TEST_SERIAL,
                                        self.current_user)))
    self.assertEqual(error.suggestion, ("Choose a --to-user ID that is"
                                        " different than the --from-user ID."))
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_from_user_is_current_user_success(self, profiler,
      mock_exists, mock_process, mock_run):
    self.command.from_user = self.current_user
    self.command.to_user = TEST_USER_ID_2
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.return_value = mock_process
    else:
      self.mock_device.start_simpleperf_trace.return_value = mock_process
    self.mock_device.perform_user_switch.side_effect = (
        lambda user: self.simulate_user_switch(user))
    mock_exists.return_value = True
    mock_run.return_value = None

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.current_user, TEST_USER_ID_3)
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 2)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(subprocess, "Popen", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_execute_to_user_is_current_user_success(self, profiler,
      mock_exists, mock_process, mock_run):
    self.command.from_user = TEST_USER_ID_1
    self.command.to_user = self.current_user
    if profiler == "perfetto":
      self.mock_device.start_perfetto_trace.return_value = mock_process
    else:
      self.mock_device.start_simpleperf_trace.return_value = mock_process
    self.mock_device.perform_user_switch.side_effect = (
        lambda user: self.simulate_user_switch(user))
    mock_exists.return_value = True
    mock_run.return_value = None

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.current_user, TEST_USER_ID_3)
    self.assertEqual(self.mock_device.perform_user_switch.call_count, 2)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)


class BootCommandExecutorUnitTest(unittest.TestCase):

  def setUp(self):
    self.command = ProfilerCommand(
        PROFILER_COMMAND_TYPE, "boot", "perfetto", DEFAULT_OUT_DIR,
        TEST_DURATION, None, 1, None, DEFAULT_PERFETTO_CONFIG, TEST_DURATION,
        False, None, None, None, None, None, None)
    self.mock_device = mock.create_autospec(AdbDevice, instance=True,
                                            serial=TEST_SERIAL)
    self.mock_device.check_device_connection.return_value = None
    self.mock_device.is_package_running.return_value = False
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)

  def test_execute_reboot_success(self):
    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.mock_device.reboot.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)

  def test_execute_reboot_multiple_runs_success(self):
    self.command.runs = 5

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.mock_device.reboot.call_count, 5)
    self.assertEqual(self.mock_device.pull_file.call_count, 5)

  def test_execute_reboot_failure(self):
    self.mock_device.reboot.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_get_prop_and_old_android_version_failure(self):
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_S)

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, (
        "Cannot perform trace on boot because only devices with version "
        "Android 13 (T) or newer can be configured to automatically start "
        "recording traces on boot."))
    self.assertEqual(error.suggestion, (
        "Update your device or use a different device with Android 13 (T) or"
        " newer."))
    self.assertEqual(self.mock_device.reboot.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_write_to_file_failure(self):
    self.mock_device.write_to_file.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_remove_file_failure(self):
    self.mock_device.remove_file.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_set_prop_failure(self):
    self.mock_device.set_prop.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_wait_for_device_failure(self):
    self.mock_device.wait_for_device.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_second_root_device_failure(self):
    self.mock_device.root_device.side_effect = [None, TEST_EXCEPTION]

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  def test_execute_wait_for_boot_to_complete_failure(self):
    self.mock_device.wait_for_boot_to_complete.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.reboot.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)


class AppStartupExecutorUnitTest(unittest.TestCase):

  def setUpSubtest(self, profiler):
    self.command = ProfilerCommand(
        PROFILER_COMMAND_TYPE, "app-startup", profiler, DEFAULT_OUT_DIR,
        DEFAULT_DUR_MS, TEST_PACKAGE_1, 1, None, DEFAULT_PERFETTO_CONFIG, None,
        False, None, None, None, None, None, None)
    if profiler == "simpleperf":
      self.command.symbols = "/"
      self.command.scripts_path = "/"
    self.mock_device = mock.create_autospec(AdbDevice, instance=True,
                                            serial=TEST_SERIAL)
    self.mock_device.check_device_connection.return_value = None
    self.mock_device.get_packages.return_value = [TEST_PACKAGE_1,
                                                  TEST_PACKAGE_2]
    self.mock_device.is_package_running.return_value = False
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)
    self.mock_device.create_directory.return_value = None

  @parameterized_profiler(setup_func=setUpSubtest)
  @mock.patch.object(subprocess, "run", autospec=True)
  @mock.patch.object(os.path, "exists", autospec=True)
  def test_app_startup_command_success(self, profiler, mock_exists, mock_run):
    mock_exists.return_value = True
    mock_run.return_value = None
    self.mock_device.start_package.return_value = None

    error = self.command.execute(self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(self.mock_device.start_package.call_count, 1)
    self.assertEqual(self.mock_device.force_stop_package.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 1)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_start_package_failure(self, profiler):
    self.mock_device.start_package.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.start_package.call_count, 1)
    self.assertEqual(self.mock_device.force_stop_package.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_get_packages_failure(self, profiler):
    self.mock_device.get_packages.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.start_package.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_package_does_not_exist_failure(self, profiler):
    self.mock_device.get_packages.return_value = [TEST_PACKAGE_2,
                                                  TEST_PACKAGE_3]

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, (
        "Package %s does not exist on device with serial %s."
        % (TEST_PACKAGE_1, self.mock_device.serial)))
    self.assertEqual(error.suggestion, (
        "Select from one of the following packages on device with serial %s:"
        " \n\t %s,\n\t %s" % (self.mock_device.serial, TEST_PACKAGE_2,
                              TEST_PACKAGE_3)))
    self.assertEqual(self.mock_device.start_package.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_package_is_running_failure(self, profiler):
    self.mock_device.is_package_running.return_value = True

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, (
        "Package %s is already running on device with serial %s."
        % (TEST_PACKAGE_1, self.mock_device.serial)))
    self.assertEqual(error.suggestion, (
        "Run 'adb -s %s shell am force-stop %s' to close the package %s before"
        " trying to start it."
        % (self.mock_device.serial, TEST_PACKAGE_1, TEST_PACKAGE_1)))
    self.assertEqual(self.mock_device.start_package.call_count, 0)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_force_stop_package_failure(self, profiler):
    self.mock_device.start_package.return_value = None
    self.mock_device.force_stop_package.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.start_package.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_kill_process_success(self, profiler):
    self.mock_device.start_package.return_value = TEST_VALIDATION_ERROR

    error = self.command.execute(self.mock_device)

    self.assertNotEqual(error, None)
    self.assertEqual(error.message, TEST_ERROR_MSG)
    self.assertEqual(error.suggestion, None)
    self.assertEqual(self.mock_device.start_package.call_count, 1)
    if profiler == "perfetto":
      self.assertEqual(self.mock_device.kill_process.call_count, 1)
    else:
      self.assertEqual(self.mock_device.send_signal.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)

  @parameterized_profiler(setup_func=setUpSubtest)
  def test_kill_process_failure(self, profiler):
    self.mock_device.start_package.return_value = TEST_VALIDATION_ERROR
    if profiler == "perfetto":
      self.mock_device.kill_process.side_effect = TEST_EXCEPTION
    else:
      self.mock_device.send_signal.side_effect = TEST_EXCEPTION

    with self.assertRaises(Exception) as e:
      self.command.execute(self.mock_device)

    self.assertEqual(str(e.exception), TEST_ERROR_MSG)
    self.assertEqual(self.mock_device.start_package.call_count, 1)
    if profiler == "perfetto":
      self.assertEqual(self.mock_device.kill_process.call_count, 1)
    else:
      self.assertEqual(self.mock_device.send_signal.call_count, 1)
    self.assertEqual(self.mock_device.pull_file.call_count, 0)


if __name__ == '__main__':
  unittest.main()
