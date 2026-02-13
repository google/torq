#
# Copyright (C) 2025 The Android Open Source Project
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
import subprocess
import sys
import io
from pathlib import Path
from unittest import mock
from src.device import AdbDevice, get_device
from src.base import ValidationError
from src.config import PREDEFINED_PERFETTO_CONFIGS
from tests.test_utils import generate_adb_devices_result, generate_mock_completed_process, run_cli

TEST_ERROR_MSG = "test-error"
TEST_VALIDATION_ERROR = ValidationError(TEST_ERROR_MSG, None)
TEST_SERIAL = "test-serial"
ANDROID_SDK_VERSION_S = 32
ANDROID_SDK_VERSION_T = 33

TEST_DEFAULT_CONFIG = f'''\
buffers: {{
  size_kb: 4096
  fill_policy: RING_BUFFER
}}
buffers {{
  size_kb: 4096
  fill_policy: RING_BUFFER
}}
buffers: {{
  size_kb: 260096
  fill_policy: RING_BUFFER
}}
data_sources: {{
  config {{
    name: "linux.process_stats"
    process_stats_config {{
      scan_all_processes_on_start: true
    }}
  }}
}}
data_sources: {{
  config {{
    name: "android.log"
    android_log_config {{
      min_prio: PRIO_VERBOSE
    }}
  }}
}}
data_sources {{
  config {{
    name: "android.packages_list"
  }}
}}
data_sources: {{
  config {{
    name: "linux.sys_stats"
    target_buffer: 1
    sys_stats_config {{
      stat_period_ms: 500
      stat_counters: STAT_CPU_TIMES
      stat_counters: STAT_FORK_COUNT
      meminfo_period_ms: 1000
      meminfo_counters: MEMINFO_ACTIVE_ANON
      meminfo_counters: MEMINFO_ACTIVE_FILE
      meminfo_counters: MEMINFO_INACTIVE_ANON
      meminfo_counters: MEMINFO_INACTIVE_FILE
      meminfo_counters: MEMINFO_KERNEL_STACK
      meminfo_counters: MEMINFO_MLOCKED
      meminfo_counters: MEMINFO_SHMEM
      meminfo_counters: MEMINFO_SLAB
      meminfo_counters: MEMINFO_SLAB_UNRECLAIMABLE
      meminfo_counters: MEMINFO_VMALLOC_USED
      meminfo_counters: MEMINFO_MEM_FREE
      meminfo_counters: MEMINFO_SWAP_FREE
      vmstat_period_ms: 1000
      vmstat_counters: VMSTAT_PGFAULT
      vmstat_counters: VMSTAT_PGMAJFAULT
      vmstat_counters: VMSTAT_PGFREE
      vmstat_counters: VMSTAT_PGPGIN
      vmstat_counters: VMSTAT_PGPGOUT
      vmstat_counters: VMSTAT_PSWPIN
      vmstat_counters: VMSTAT_PSWPOUT
      vmstat_counters: VMSTAT_PGSCAN_DIRECT
      vmstat_counters: VMSTAT_PGSTEAL_DIRECT
      vmstat_counters: VMSTAT_PGSCAN_KSWAPD
      vmstat_counters: VMSTAT_PGSTEAL_KSWAPD
      vmstat_counters: VMSTAT_WORKINGSET_REFAULT
      cpufreq_period_ms: 500
    }}
  }}
}}
data_sources: {{
  config {{
    name: "android.surfaceflinger.frametimeline"
    target_buffer: 2
  }}
}}
data_sources: {{
  config {{
    name: "linux.ftrace"
    target_buffer: 2
    ftrace_config {{
      ftrace_events: "dmabuf_heap/dma_heap_stat"
      ftrace_events: "ftrace/print"
      ftrace_events: "gpu_mem/gpu_mem_total"
      ftrace_events: "ion/ion_stat"
      ftrace_events: "kmem/ion_heap_grow"
      ftrace_events: "kmem/ion_heap_shrink"
      ftrace_events: "kmem/rss_stat"
      ftrace_events: "lowmemorykiller/lowmemory_kill"
      ftrace_events: "mm_event/mm_event_record"
      ftrace_events: "oom/mark_victim"
      ftrace_events: "oom/oom_score_adj_update"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/gpu_frequency"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "sched/sched_process_exit"
      ftrace_events: "sched/sched_process_free"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_wakeup_new"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "task/task_newtask"
      ftrace_events: "task/task_rename"
      ftrace_events: "vmscan/*"
      ftrace_events: "workqueue/*"
      atrace_categories: "aidl"
      atrace_categories: "am"
      atrace_categories: "dalvik"
      atrace_categories: "binder_lock"
      atrace_categories: "binder_driver"
      atrace_categories: "bionic"
      atrace_categories: "camera"
      atrace_categories: "disk"
      atrace_categories: "freq"
      atrace_categories: "idle"
      atrace_categories: "gfx"
      atrace_categories: "hal"
      atrace_categories: "input"
      atrace_categories: "pm"
      atrace_categories: "power"
      atrace_categories: "res"
      atrace_categories: "rro"
      atrace_categories: "sched"
      atrace_categories: "sm"
      atrace_categories: "ss"
      atrace_categories: "thermal"
      atrace_categories: "video"
      atrace_categories: "view"
      atrace_categories: "wm"
      atrace_apps: "*"
      buffer_size_kb: 16384
      drain_period_ms: 150
      symbolize_ksyms: true
    }}
  }}
}}

data_sources {{
  config {{
    name: "perfetto.metatrace"
    target_buffer: 2
  }}
  producer_name_filter: "perfetto.traced_probes"
}}

write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 100000000000
flush_period_ms: 5000
incremental_state_config {{
  clear_period_ms: 5000
}}

'''

TEST_DEFAULT_CONFIG_OLD_ANDROID = f'''\
buffers: {{
  size_kb: 4096
  fill_policy: RING_BUFFER
}}
buffers {{
  size_kb: 4096
  fill_policy: RING_BUFFER
}}
buffers: {{
  size_kb: 260096
  fill_policy: RING_BUFFER
}}
data_sources: {{
  config {{
    name: "linux.process_stats"
    process_stats_config {{
      scan_all_processes_on_start: true
    }}
  }}
}}
data_sources: {{
  config {{
    name: "android.log"
    android_log_config {{
      min_prio: PRIO_VERBOSE
    }}
  }}
}}
data_sources {{
  config {{
    name: "android.packages_list"
  }}
}}
data_sources: {{
  config {{
    name: "linux.sys_stats"
    target_buffer: 1
    sys_stats_config {{
      stat_period_ms: 500
      stat_counters: STAT_CPU_TIMES
      stat_counters: STAT_FORK_COUNT
      meminfo_period_ms: 1000
      meminfo_counters: MEMINFO_ACTIVE_ANON
      meminfo_counters: MEMINFO_ACTIVE_FILE
      meminfo_counters: MEMINFO_INACTIVE_ANON
      meminfo_counters: MEMINFO_INACTIVE_FILE
      meminfo_counters: MEMINFO_KERNEL_STACK
      meminfo_counters: MEMINFO_MLOCKED
      meminfo_counters: MEMINFO_SHMEM
      meminfo_counters: MEMINFO_SLAB
      meminfo_counters: MEMINFO_SLAB_UNRECLAIMABLE
      meminfo_counters: MEMINFO_VMALLOC_USED
      meminfo_counters: MEMINFO_MEM_FREE
      meminfo_counters: MEMINFO_SWAP_FREE
      vmstat_period_ms: 1000
      vmstat_counters: VMSTAT_PGFAULT
      vmstat_counters: VMSTAT_PGMAJFAULT
      vmstat_counters: VMSTAT_PGFREE
      vmstat_counters: VMSTAT_PGPGIN
      vmstat_counters: VMSTAT_PGPGOUT
      vmstat_counters: VMSTAT_PSWPIN
      vmstat_counters: VMSTAT_PSWPOUT
      vmstat_counters: VMSTAT_PGSCAN_DIRECT
      vmstat_counters: VMSTAT_PGSTEAL_DIRECT
      vmstat_counters: VMSTAT_PGSCAN_KSWAPD
      vmstat_counters: VMSTAT_PGSTEAL_KSWAPD
      vmstat_counters: VMSTAT_WORKINGSET_REFAULT

    }}
  }}
}}
data_sources: {{
  config {{
    name: "android.surfaceflinger.frametimeline"
    target_buffer: 2
  }}
}}
data_sources: {{
  config {{
    name: "linux.ftrace"
    target_buffer: 2
    ftrace_config {{
      ftrace_events: "dmabuf_heap/dma_heap_stat"
      ftrace_events: "ftrace/print"
      ftrace_events: "gpu_mem/gpu_mem_total"
      ftrace_events: "ion/ion_stat"
      ftrace_events: "kmem/ion_heap_grow"
      ftrace_events: "kmem/ion_heap_shrink"
      ftrace_events: "kmem/rss_stat"
      ftrace_events: "lowmemorykiller/lowmemory_kill"
      ftrace_events: "mm_event/mm_event_record"
      ftrace_events: "oom/mark_victim"
      ftrace_events: "oom/oom_score_adj_update"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/gpu_frequency"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "sched/sched_process_exit"
      ftrace_events: "sched/sched_process_free"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_wakeup_new"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "task/task_newtask"
      ftrace_events: "task/task_rename"
      ftrace_events: "vmscan/*"
      ftrace_events: "workqueue/*"
      atrace_categories: "aidl"
      atrace_categories: "am"
      atrace_categories: "dalvik"
      atrace_categories: "binder_lock"
      atrace_categories: "binder_driver"
      atrace_categories: "bionic"
      atrace_categories: "camera"
      atrace_categories: "disk"
      atrace_categories: "freq"
      atrace_categories: "idle"
      atrace_categories: "gfx"
      atrace_categories: "hal"
      atrace_categories: "input"
      atrace_categories: "pm"
      atrace_categories: "power"
      atrace_categories: "res"
      atrace_categories: "rro"
      atrace_categories: "sched"
      atrace_categories: "sm"
      atrace_categories: "ss"
      atrace_categories: "thermal"
      atrace_categories: "video"
      atrace_categories: "view"
      atrace_categories: "wm"
      atrace_apps: "*"
      buffer_size_kb: 16384
      drain_period_ms: 150
      symbolize_ksyms: true
    }}
  }}
}}

data_sources {{
  config {{
    name: "perfetto.metatrace"
    target_buffer: 2
  }}
  producer_name_filter: "perfetto.traced_probes"
}}

write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 100000000000
flush_period_ms: 5000
incremental_state_config {{
  clear_period_ms: 5000
}}

'''


class ConfigCommandExecutorUnitTest(unittest.TestCase):

  def setUp(self):
    self.maxDiff = None
    self.mock_get_device_patcher = mock.patch("src.torq.get_device")
    self.mock_get_device = self.mock_get_device_patcher.start()
    self.mock_device = mock.create_autospec(AdbDevice, instance=True)
    self.mock_get_device.return_value = (self.mock_device, None)
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)

    self.stdout_output = io.StringIO()
    self.stderr_output = io.StringIO()
    sys.stdout = self.stdout_output
    sys.stderr = self.stderr_output

  def tearDown(self):
    self.mock_get_device_patcher.stop()

  def test_config_list(self):
    run_cli("torq config list")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(
        self.stdout_output.getvalue(),
        ("%s\n" % "\n".join(list(PREDEFINED_PERFETTO_CONFIGS.keys()))))

  def test_config_show(self):
    run_cli("torq config show default")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(), TEST_DEFAULT_CONFIG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_show_no_device_connected(self, mock_subprocess_run):
    self.mock_get_device.return_value = (None, None)

    run_cli("torq config show default")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(), TEST_DEFAULT_CONFIG)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_show_old_android_version(self, mock_subprocess_run):
    mock_subprocess_run.return_value = (
        generate_adb_devices_result(["test-serial"]))

    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_S)

    run_cli("torq config show default")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     TEST_DEFAULT_CONFIG_OLD_ANDROID)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()

    run_cli("torq config pull default")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     "The config has been saved to 'default.txtpb'.\n")

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_no_device_connected(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    self.mock_get_device.return_value = (None, None)

    run_cli("torq config pull default")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     "The config has been saved to 'default.txtpb'.\n")

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_old_android_version(self, mock_subprocess_run):
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_S)
    mock_subprocess_run.return_value = generate_mock_completed_process()

    run_cli("torq config pull default")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     "The config has been saved to 'default.txtpb'.\n")

  @mock.patch.object(Path, "exists", autospec=True)
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_nonexistent_filepath(self, mock_subprocess_run,
                                            mock_exists):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    mock_exists.return_value = False

    run_cli("torq config pull default new_config.txtpb")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     "The config has been saved to 'new_config.txtpb'.\n")

  @mock.patch.object(Path, "exists", autospec=True)
  @mock.patch.object(builtins, "input")
  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_overwriting_existing_filepath(self, mock_subprocess_run,
                                                     mock_input, mock_exists):
    mock_subprocess_run.return_value = generate_mock_completed_process()
    mock_input.return_value = "y"
    mock_exists.return_value = True

    run_cli("torq config pull default config.txtpb")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     "The config has been saved to 'config.txtpb'.\n")

  @mock.patch.object(Path, "exists", autospec=True)
  @mock.patch.object(builtins, "input")
  def test_config_pull_not_overwriting_existing_filepath(
      self, mock_input, mock_exists):
    mock_input.return_value = "n"
    mock_exists.return_value = True

    run_cli("torq config pull default config.txtpb")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(), "Operation cancelled.\n")

  @mock.patch.object(Path, "exists", autospec=True)
  @mock.patch.object(Path, "is_dir", autospec=True)
  def test_config_pull_existing_filepath_is_dir(self, mock_is_dir, mock_exists):
    mock_is_dir.return_value = True
    mock_exists.return_value = True

    run_cli("torq config pull default config.txtpb")

    self.assertEqual(
        self.stderr_output.getvalue(),
        "File path 'config.txtpb' is a directory.\nSuggestion:\n\tProvide a path to a file.\n"
    )

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_custom_filepath_with_no_suffix(self,
                                                      mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()

    run_cli("torq config pull default config")

    self.assertEqual(self.stderr_output.getvalue(), "")
    self.assertEqual(self.stdout_output.getvalue(),
                     "The config has been saved to 'config.txtpb'.\n")

  def test_config_pull_invalid_custom_filepath_suffix(self):
    run_cli("torq config pull default config.badsuffix")

    self.assertEqual(
        self.stderr_output.getvalue(),
        "File 'config.badsuffix' has invalid file extension: '.badsuffix'.\nSuggestion:"
        "\n\tProvide a filename with one of the supported file extensions: "
        "[.txtpb, .textproto, .textpb, .pbtxt].\n")


if __name__ == '__main__':
  unittest.main()
