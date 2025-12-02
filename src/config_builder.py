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

import argparse
import textwrap
from .base import ANDROID_SDK_VERSION_T, ValidationError


def create_ftrace_events_string(predefined_ftrace_events,
                                excluded_ftrace_events, included_ftrace_events):
  if excluded_ftrace_events is not None:
    for event in excluded_ftrace_events:
      if event in predefined_ftrace_events:
        predefined_ftrace_events.remove(event)
      else:
        return None, ValidationError(
            ("Cannot remove ftrace event %s from"
             " config because it is not one"
             " of the config's ftrace events." % event),
            ("Please specify one of the following"
             " possible ftrace events:\n\t %s" %
             "\n\t ".join(predefined_ftrace_events)))

  if included_ftrace_events is not None:
    for event in included_ftrace_events:
      if event not in predefined_ftrace_events:
        predefined_ftrace_events.append(event)
      else:
        return None, ValidationError(("Cannot add ftrace event %s to config"
                                      " because it is already one of the"
                                      " config's ftrace events." % event),
                                     ("Please do not specify any of the"
                                      " following ftrace events that are"
                                      " already included:\n\t %s" %
                                      "\n\t ".join(predefined_ftrace_events)))

  ftrace_events_string = ("ftrace_events: \"%s\"" % ("""\"
          ftrace_events: \"""".join(predefined_ftrace_events)))
  return ftrace_events_string, None


def create_common_config_parser():
  common_config_args = argparse.ArgumentParser(add_help=False)
  common_config_args.add_argument(
      '-d',
      '--dur-ms',
      type=int,
      help=('The duration (ms) of the event. Determines when'
            ' to stop collecting performance data.'))
  common_config_args.add_argument(
      '--excluded-ftrace-events',
      action='append',
      help=('Excludes specified ftrace event from the perfetto'
            ' config events.'))
  common_config_args.add_argument(
      '--included-ftrace-events',
      action='append',
      help=('Includes specified ftrace event in the perfetto'
            ' config events.'))
  common_config_args.add_argument(
      '--trigger-names',
      action='extend',
      default=[],
      nargs="+",
      help='Specifies the names of triggers for perfetto'
      ' background tracing.')
  common_config_args.add_argument(
      '--trigger-timeout-ms',
      type=int,
      help='Specifies the time in milliseconds for Perfetto to'
      ' wait for a trigger before ending.')
  common_config_args.add_argument(
      '--trigger-stop-delay-ms',
      type=int,
      action='extend',
      default=[],
      nargs="+",
      help='Specifies the time in milliseconds to extend trace'
      ' collection past a trigger event. If you have'
      ' multiple triggers, you can include a different'
      ' stop-delay-ms for each or include one to use for'
      ' them all.')
  common_config_args.add_argument(
      '--trigger-mode',
      choices=[
          'stop', 'start', 'clone', 'STOP_TRACING', 'START_TRACING',
          'CLONE_SNAPSHOT'
      ],
      help='Specifies the trigger config mode. stop'
      ' will stop tracing when a trigger is'
      ' received. start will start tracing when a'
      ' trigger is received until stop-delay-ms.'
      ' clone will return tracing data when a'
      ' trigger is received and continue tracing'
      ' until the timeout.')

  return common_config_args


def create_trigger_config(trigger_names, trigger_mode, trigger_timeout_ms,
                          trigger_stop_delay_ms):
  config_trigger_mode = trigger_mode
  use_clone_snapshot_if_available = "false"

  if config_trigger_mode == "CLONE_SNAPSHOT":
    # The use_clone_snapshot_if_available flag will default to STOP_TRACING
    # on Android versions without CLONE_SNAPSHOT, and will default to
    # CLONE_SNAPSHOT on Android versions that do have it. When using this
    # flag, the tracing mode must be STOP_TRACING.
    config_trigger_mode = "STOP_TRACING"
    use_clone_snapshot_if_available = "true"

  trigger_config = f'''
  trigger_config: {{
      trigger_mode: {config_trigger_mode}

      trigger_timeout_ms: {trigger_timeout_ms}

      use_clone_snapshot_if_available: {use_clone_snapshot_if_available}'''

  for i, name in enumerate(trigger_names):
    trigger_config += f'''
      triggers {{
          name: "{name}"

          stop_delay_ms: {trigger_stop_delay_ms[i % len(trigger_stop_delay_ms)]}
      }}'''

  trigger_config += f'''
    }}'''
  return trigger_config


def build_predefined_config(command,
                            android_sdk_version,
                            predefined_ftrace_events=None,
                            sys_stats_events=None,
                            predefined_atrace_events=None,
                            log_priority="PRIO_VERBOSE",
                            buffers=None,
                            linux_process_stats=None,
                            android_logs=None,
                            android_packages=None,
                            sys_stats=None,
                            surface_flinger=None,
                            ftrace=None,
                            metatrace=None,
                            miscellaneous_options=None,
                            incremental_state=None,
                            extra_configs=""):
  if predefined_ftrace_events is None:
    predefined_ftrace_events = [
        "dmabuf_heap/dma_heap_stat",
        "ftrace/print",
        "gpu_mem/gpu_mem_total",
        "ion/ion_stat",
        "kmem/ion_heap_grow",
        "kmem/ion_heap_shrink",
        "kmem/rss_stat",
        "lowmemorykiller/lowmemory_kill",
        "mm_event/mm_event_record",
        "oom/mark_victim",
        "oom/oom_score_adj_update",
        "power/cpu_frequency",
        "power/cpu_idle",
        "power/gpu_frequency",
        "power/suspend_resume",
        "power/wakeup_source_activate",
        "power/wakeup_source_deactivate",
        "sched/sched_blocked_reason",
        "sched/sched_process_exit",
        "sched/sched_process_free",
        "sched/sched_switch",
        "sched/sched_wakeup",
        "sched/sched_wakeup_new",
        "sched/sched_waking",
        "task/task_newtask",
        "task/task_rename",
        "vmscan/*",
        "workqueue/*",
    ]

  if sys_stats_events is None:
    sys_stats_events = \
    f'''stat_period_ms: 500
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
          vmstat_counters: VMSTAT_WORKINGSET_REFAULT'''

  if predefined_atrace_events is None:
    predefined_atrace_events = \
    f'''atrace_categories: "aidl"
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
          atrace_apps: "*"'''

  ftrace_events_string, error = create_ftrace_events_string(
      predefined_ftrace_events, command.excluded_ftrace_events,
      command.included_ftrace_events)
  if error is not None:
    return None, error

  cpufreq_period_string = "cpufreq_period_ms: 500"
  if android_sdk_version < ANDROID_SDK_VERSION_T:
    cpufreq_period_string = ""

  trigger_config = ""
  if command.trigger_names:
    trigger_config = create_trigger_config(command.trigger_names,
                                           command.trigger_mode,
                                           command.trigger_timeout_ms,
                                           command.trigger_stop_delay_ms)

  write_into_file = "true" if trigger_config == "" else "false"

  duration_string = ""
  if command.dur_ms is not None:
    duration_string = f'''
    duration_ms: {command.dur_ms}'''

  if buffers is None:
    buffers = f'''
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
    }}'''

  if linux_process_stats is None:
    linux_process_stats = f'''
    data_sources: {{
      config {{
        name: "linux.process_stats"
        process_stats_config {{
          scan_all_processes_on_start: true
        }}
      }}
    }}'''

  if android_logs is None:
    android_logs = f'''
    data_sources: {{
      config {{
        name: "android.log"
        android_log_config {{
          min_prio: {log_priority}
        }}
      }}
    }}'''

  if android_packages is None:
    android_packages = f'''
    data_sources {{
      config {{
        name: "android.packages_list"
      }}
    }}'''

  if sys_stats is None:
    sys_stats = f'''
    data_sources: {{
      config {{
        name: "linux.sys_stats"
        target_buffer: 1
        sys_stats_config {{
          {sys_stats_events}
          {cpufreq_period_string}
        }}
      }}
    }}'''

  if surface_flinger is None:
    surface_flinger = f'''
    data_sources: {{
      config {{
        name: "android.surfaceflinger.frametimeline"
        target_buffer: 2
      }}
    }}'''

  if ftrace is None:
    ftrace = f'''
    data_sources: {{
      config {{
        name: "linux.ftrace"
        target_buffer: 2
        ftrace_config {{
          {ftrace_events_string}
          {predefined_atrace_events}
          buffer_size_kb: 16384
          drain_period_ms: 150
          symbolize_ksyms: true
        }}
      }}
    }}'''

  if metatrace is None:
    metatrace = f'''
    data_sources {{
      config {{
        name: "perfetto.metatrace"
        target_buffer: 2
      }}
      producer_name_filter: "perfetto.traced_probes"
    }}'''

  if miscellaneous_options is None:
    miscellaneous_options = f'''
    write_into_file: {write_into_file}
    file_write_period_ms: 5000
    max_file_size_bytes: 100000000000
    flush_period_ms: 5000
    trace_all_machines: true'''

  if incremental_state is None:
    incremental_state = f'''
    incremental_state_config {{
      clear_period_ms: 5000
    }}'''

  config = f'''\
    <<EOF
    {buffers}
    {linux_process_stats.lstrip()}
    {android_logs.lstrip()}
    {android_packages.lstrip()}
    {sys_stats.lstrip()}
    {surface_flinger.lstrip()}
    {ftrace.lstrip()}
    {extra_configs.lstrip()}
    {metatrace.lstrip()}
    {duration_string.lstrip()}
    {miscellaneous_options.lstrip()}
    {incremental_state.lstrip()}
    {trigger_config.lstrip()}

    EOF'''
  return textwrap.dedent(config), None


def build_default_config(command, android_sdk_version):
  return build_predefined_config(command, android_sdk_version)


def build_lightweight_config(command, android_sdk_version):
  predefined_ftrace_events = [
      "power/cpu_idle",
      "sched/sched_blocked_reason",
      "sched/sched_switch",
      "sched/sched_wakeup",
      "sched/sched_wakeup_new",
      "sched/sched_waking",
  ]
  sys_stats_config = f'''stat_period_ms: 500
          stat_counters: STAT_CPU_TIMES
          meminfo_period_ms: 1000
          meminfo_counters: MEMINFO_MEM_FREE'''
  atrace_events = f'''atrace_categories: "aidl"
          atrace_categories: "am"
          atrace_categories: "binder_lock"
          atrace_categories: "binder_driver"
          atrace_categories: "dalvik"
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
          atrace_categories: "view"
          atrace_categories: "wm"
          atrace_apps: "lmkd"
          atrace_apps: "system_server"
          atrace_apps: "com.android.car"
          atrace_apps: "com.android.systemui"
          atrace_apps: "com.google.android.gms"
          atrace_apps: "com.google.android.gms.persistent"
          atrace_apps: "android:ui"'''
  return build_predefined_config(
      command,
      android_sdk_version,
      predefined_ftrace_events,
      sys_stats_config,
      atrace_events,
      "PRIO_ERROR",
      surface_flinger="")


def build_memory_config(command, android_sdk_version):
  predefined_ftrace_events = [
      "dmabuf_heap/dma_heap_stat",
      "ftrace/print",
      "gpu_mem/gpu_mem_total",
      "ion/ion_stat",
      "kmem/ion_heap_grow",
      "kmem/ion_heap_shrink",
      "kmem/rss_stat",
      "lowmemorykiller/lowmemory_kill",
      "mm_event/mm_event_record",
      "oom/mark_victim",
      "oom/oom_score_adj_update",
      "sched/sched_blocked_reason",
      "sched/sched_switch",
      "sched/sched_wakeup",
      "sched/sched_wakeup_new",
      "sched/sched_waking",
  ]
  sys_stats_config = f'''stat_period_ms: 500
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
          meminfo_counters: MEMINFO_MEM_AVAILABLE
          meminfo_counters: MEMINFO_MEM_TOTAL
          vmstat_period_ms: 1000
          vmstat_counters: VMSTAT_NR_FREE_PAGES
          vmstat_counters: VMSTAT_NR_ALLOC_BATCH
          vmstat_counters: VMSTAT_NR_INACTIVE_ANON
          vmstat_counters: VMSTAT_NR_ACTIVE_ANON
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
          vmstat_counters: VMSTAT_WORKINGSET_REFAULT'''
  atrace_events = f'''atrace_categories: "aidl"
          atrace_categories: "am"
          atrace_categories: "binder_lock"
          atrace_categories: "binder_driver"
          atrace_categories: "dalvik"
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
          atrace_categories: "view"
          atrace_categories: "wm"
          atrace_apps: "*"'''
  extra_configs = f'''
    data_sources {{
      config {{
        name: "android.java_hprof"
        target_buffer: 2
        java_hprof_config {{
          process_cmdline: "system_server"
        }}
      }}
    }}'''
  return build_predefined_config(
      command,
      android_sdk_version,
      predefined_ftrace_events,
      sys_stats_config,
      atrace_events,
      "PRIO_ERROR",
      surface_flinger="",
      extra_configs=extra_configs)


PREDEFINED_PERFETTO_CONFIGS = {
    'default': build_default_config,
    'lightweight': build_lightweight_config,
    'memory': build_memory_config
}


def build_custom_config(command):
  file_content = ""
  duration_prefix = "duration_ms:"
  appended_duration = ""
  if command.dur_ms is not None:
    appended_duration = duration_prefix + " " + str(command.dur_ms)
  try:
    with open(command.perfetto_config, "r") as file:
      for line in file:
        stripped_line = line.strip()
        if stripped_line.startswith(duration_prefix):
          duration = stripped_line[len(duration_prefix):].strip()
          appended_duration = ""
          command.dur_ms = int(duration)
        file_content += line
  except ValueError:
    return None, ValidationError(
        ("Failed to parse custom perfetto-config on"
         " local file path: %s. Invalid duration_ms"
         " field in config." % command.perfetto_config),
        ("Make sure the perfetto config passed via"
         " arguments has a valid duration_ms value."))
  except Exception as e:
    return None, ValidationError(
        ("Failed to parse custom perfetto-config on"
         " local file path: %s. %s" % (command.perfetto_config, str(e))), None)
  config_string = f"<<EOF\n\n{file_content}\n{appended_duration}\n\nEOF"
  return config_string, None
