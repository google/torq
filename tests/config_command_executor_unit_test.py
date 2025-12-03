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

import unittest
import subprocess
import sys
import io
from unittest import mock
from src.base import ANDROID_SDK_VERSION_S, ANDROID_SDK_VERSION_T, PERFETTO_VERSION_WITH_MULTI_VM_SUPPORT, ValidationError
from src.config import ConfigCommand, execute_config_command, PREDEFINED_PERFETTO_CONFIGS
from src.device import AdbDevice
from tests.test_utils import generate_mock_completed_process, parse_cli

TEST_ERROR_MSG = "test-error"
TEST_VALIDATION_ERROR = ValidationError(TEST_ERROR_MSG, None)
TEST_SERIAL = "test-serial"

TEST_DEFAULT_EXTRA_CONFIGS = f'''\
write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 100000000000
flush_period_ms: 5000
trace_all_machines: true
incremental_state_config {{
  clear_period_ms: 5000
}}
'''

TEST_DEFAULT_EXTRA_CONFIGS_OLD_PERFETTO = f'''\
write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 100000000000
flush_period_ms: 5000
incremental_state_config {{
  clear_period_ms: 5000
}}
'''

TEST_DEFAULT_CONFIG_TEMPLATE = f'''\
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
'''

TEST_DEFAULT_CONFIG = f'''\
{TEST_DEFAULT_CONFIG_TEMPLATE}
{TEST_DEFAULT_EXTRA_CONFIGS}
'''

TEST_DEFAULT_CONFIG_OLD_PERFETTO = f'''\
{TEST_DEFAULT_CONFIG_TEMPLATE}
{TEST_DEFAULT_EXTRA_CONFIGS_OLD_PERFETTO}
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

{TEST_DEFAULT_EXTRA_CONFIGS}
'''


class ConfigCommandExecutorUnitTest(unittest.TestCase):

  def setUp(self):
    self.maxDiff = None
    self.mock_device = mock.create_autospec(
        AdbDevice, instance=True, serial=TEST_SERIAL)
    self.mock_device.check_device_connection.return_value = None
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_T)
    self.mock_device.get_perfetto_version.return_value = PERFETTO_VERSION_WITH_MULTI_VM_SUPPORT

  def test_config_list(self):
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    args = parse_cli("torq config list")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(
        terminal_output.getvalue(),
        ("%s\n" % "\n".join(list(PREDEFINED_PERFETTO_CONFIGS.keys()))))

  def test_config_show(self):
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    args = parse_cli("torq config show default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(terminal_output.getvalue(), TEST_DEFAULT_CONFIG)

  def test_config_show_no_device_connection(self):
    self.mock_device.check_device_connection.return_value = (
        TEST_VALIDATION_ERROR)

    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    args = parse_cli("torq config show default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(terminal_output.getvalue(), TEST_DEFAULT_CONFIG)

  def test_config_show_old_android_version(self):
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_S)
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    args = parse_cli("torq config show default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(terminal_output.getvalue(),
                     TEST_DEFAULT_CONFIG_OLD_ANDROID)

  def test_config_show_old_perfetto_version(self):
    self.mock_device.get_perfetto_version.return_value = 53
    terminal_output = io.StringIO()
    sys.stdout = terminal_output

    args = parse_cli("torq config show default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)
    self.assertEqual(terminal_output.getvalue(),
                     TEST_DEFAULT_CONFIG_OLD_PERFETTO)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull(self, mock_subprocess_run):
    mock_subprocess_run.return_value = generate_mock_completed_process()

    args = parse_cli("torq config pull default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_no_device_connection(self, mock_subprocess_run):
    self.mock_device.check_device_connection.return_value = (
        TEST_VALIDATION_ERROR)
    mock_subprocess_run.return_value = generate_mock_completed_process()

    args = parse_cli("torq config pull default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_old_android_version(self, mock_subprocess_run):
    self.mock_device.get_android_sdk_version.return_value = (
        ANDROID_SDK_VERSION_S)
    mock_subprocess_run.return_value = generate_mock_completed_process()

    args = parse_cli("torq config pull default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)

  @mock.patch.object(subprocess, "run", autospec=True)
  def test_config_pull_old_perfetto_version(self, mock_subprocess_run):
    self.mock_device.get_perfetto_version.return_value = 53
    mock_subprocess_run.return_value = generate_mock_completed_process()

    args = parse_cli("torq config pull default")
    error = execute_config_command(args, self.mock_device)

    self.assertEqual(error, None)


if __name__ == '__main__':
  unittest.main()
