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
import os
from unittest import mock
from src.config import create_config_command
from src.profiler import (DEFAULT_DUR_MS, DEFAULT_OUT_DIR,
                          DEFAULT_TRIGGER_DUR_MS, DEFAULT_TRIGGER_MODE,
                          DEFAULT_TRIGGER_STOP_DELAY_MS, MIN_STOP_DELAY_MS,
                          MIN_DURATION_MS)
from src.torq import create_parser, verify_args
from tests.test_utils import create_parser_from_cli, parse_cli, parameterized_config_builder

TEST_USER_ID = 10
TEST_PACKAGE = "com.android.contacts"
TEST_FILE = "file.pbtxt"
SYMBOLS_PATH = "/folder/symbols"
TEST_TRIGGER_NAMES = [
    "team.package.test-trigger-name", "team2.package2.test-trigger-name2"
]
TEST_TRIGGER_DUR_MS = 10000
TEST_TRIGGER_STOP_DELAY_MS = 1000
TEST_TRIGGER_MODE = "stop"


class TorqUnitTest(unittest.TestCase):

  # TODO(b/285191111): Parameterize the test functions.
  def test_create_parser_default_values(self):
    args = parse_cli("torq")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.event, "custom")
    self.assertEqual(args.profiler, "perfetto")
    self.assertEqual(args.out_dir, DEFAULT_OUT_DIR)
    self.assertEqual(args.runs, 1)
    self.assertEqual(args.perfetto_config, "default")
    self.assertEqual(args.dur_ms, None)
    self.assertEqual(args.between_dur_ms, DEFAULT_DUR_MS)

  def test_create_parser_valid_event_names(self):
    args = parse_cli("torq -e custom")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.event, "custom")

    args = parse_cli("torq -e boot")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.event, "boot")

    args = parse_cli("torq -e user-switch --to-user %s" % str(TEST_USER_ID))

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.event, "user-switch")

    args = parse_cli("torq -e app-startup --app %s" % TEST_PACKAGE)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.event, "app-startup")

  def test_create_parser_invalid_event_names(self):
    parser, error = create_parser_from_cli("torq -e fake-event")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_create_parser_valid_profiler_names(self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli("torq -p perfetto")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.profiler, "perfetto")

    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.profiler, "simpleperf")

  def test_create_parser_invalid_profiler_names(self):
    parser, error = create_parser_from_cli("torq -p fake-profiler")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_valid_out_dir_path(self, mock_is_dir):
    mock_is_dir.return_value = True
    args = parse_cli("torq -o mock-directory")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.out_dir, "mock-directory")

  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_invalid_out_dir_paths(self, mock_is_dir):
    mock_is_dir.return_value = False
    args = parse_cli("torq -o mock-file")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --out-dir is not a valid"
                                     " directory path: mock-file."))
    self.assertEqual(error.suggestion, None)

  def test_create_parser_valid_ui(self):
    args = parse_cli("torq --ui")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.ui, True)

    args = parse_cli("torq --no-ui")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.ui, False)

  def test_verify_args_valid_dur_ms_values(self):
    args = parse_cli("torq -d 100000")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.dur_ms, 100000)

  def test_verify_args_ui_and_runs_valid_dependency(self):
    args = parse_cli("torq -r 2 --no-ui")

    args, error = verify_args(args)

    self.assertEqual(error, None)

  def test_verify_args_ui_and_runs_invalid_dependency(self):
    args = parse_cli("torq -r 2 --ui")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --ui cannot be"
                                     " passed if --runs is set to a value"
                                     " greater than 1."))
    self.assertEqual(error.suggestion, ("Set torq -r 2 --no-ui to perform 2"
                                        " runs."))

  def test_verify_args_ui_bool_true_and_runs_default_dependencies(self):
    args = parse_cli("torq")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.ui, True)

    args = parse_cli("torq -r 1")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.ui, True)

  # UI is false by default when multiple runs are specified.
  def test_verify_args_ui_bool_false_and_runs_default_dependency(self):
    args = parse_cli("torq -r 2")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.ui, False)

  def test_verify_args_invalid_dur_ms_values(self):
    args = parse_cli("torq -d -200")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --dur-ms cannot be set to a value"
                                     " smaller than 3000."))
    self.assertEqual(error.suggestion, ("Set --dur-ms 3000 to capture a"
                                        " trace for 3 seconds."))

    args = parse_cli("torq -d 0")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --dur-ms cannot be set to a value"
                                     " smaller than 3000."))
    self.assertEqual(error.suggestion, ("Set --dur-ms 3000 to capture a"
                                        " trace for 3 seconds."))

    args = parse_cli("torq -d 20")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --dur-ms cannot be set to a value"
                                     " smaller than 3000."))
    self.assertEqual(error.suggestion, ("Set --dur-ms 3000 to capture a"
                                        " trace for 3 seconds."))

  def test_verify_args_valid_between_dur_ms_values(self):
    args = parse_cli("torq -r 2 --between-dur-ms 10000")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.between_dur_ms, 10000)

  def test_verify_args_invalid_between_dur_ms_values(self):
    args = parse_cli("torq -r 2 --between-dur-ms -200")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --between-dur-ms cannot be set to"
                                     " a smaller value than 3000."))
    self.assertEqual(error.suggestion, ("Set --between-dur-ms 3000 to wait"
                                        " 3 seconds between each run."))

    args = parse_cli("torq -r 2 --between-dur-ms 0")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --between-dur-ms cannot be set to a"
                                     " smaller value than 3000."))
    self.assertEqual(error.suggestion, ("Set --between-dur-ms 3000 to wait"
                                        " 3 seconds between each run."))

    args = parse_cli("torq -r 2 --between-dur-ms 20")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --between-dur-ms cannot be set to a"
                                     " smaller value than 3000."))
    self.assertEqual(error.suggestion, ("Set --between-dur-ms 3000 to wait"
                                        " 3 seconds between each run."))

  def test_verify_args_valid_runs_values(self):
    args = parse_cli("torq -r 4")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.runs, 4)

  def test_verify_args_invalid_runs_values(self):
    args = parse_cli("torq -r -2")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --runs"
                                     " cannot be set to a value smaller"
                                     " than 1."))
    self.assertEqual(error.suggestion, None)

    args = parse_cli("torq -r 0")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --runs"
                                     " cannot be set to a value smaller"
                                     " than 1."))
    self.assertEqual(error.suggestion, None)

  @mock.patch.object(os.path, "isfile", autospec=True)
  def test_verify_args_valid_perfetto_config_path(self, mock_is_file):
    mock_is_file.return_value = True
    args = parse_cli("torq --perfetto-config mock-file")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.perfetto_config, "mock-file")

    args = parse_cli("torq --perfetto-config default")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.perfetto_config, "default")

    args = parse_cli("torq --perfetto-config lightweight")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.perfetto_config, "lightweight")

    args = parse_cli("torq --perfetto-config memory")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.perfetto_config, "memory")

  @mock.patch.object(os.path, "isfile", autospec=True)
  def test_verify_args_invalid_perfetto_config_path(self, mock_is_file):
    mock_is_file.return_value = False
    args = parse_cli("torq --perfetto-config unexisting-file")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --perfetto-config is not a"
                                     " valid file path: unexisting-file"))
    self.assertEqual(error.suggestion, ("Predefined perfetto configs can be"
                                        " used:\n"
                                        "\t torq --perfetto-config default\n"
                                        "\t torq --perfetto-config"
                                        " lightweight\n"
                                        "\t torq --perfetto-config memory\n"
                                        "\t A filepath with a config can also"
                                        " be used:\n"
                                        "\t torq --perfetto-config"
                                        " <config-filepath>"))

    args = parse_cli("torq --perfetto-config mock-directory")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --perfetto-config is not a"
                                     " valid file path: mock-directory"))
    self.assertEqual(error.suggestion, ("Predefined perfetto configs can be"
                                        " used:\n"
                                        "\t torq --perfetto-config default\n"
                                        "\t torq --perfetto-config"
                                        " lightweight\n"
                                        "\t torq --perfetto-config memory\n"
                                        "\t A filepath with a config can also"
                                        " be used:\n"
                                        "\t torq --perfetto-config"
                                        " <config-filepath>"))

  def test_verify_args_from_user_and_event_valid_dependency(self):
    args = parse_cli(("torq -e user-switch --from-user 0"
                      " --to-user %s") % str(TEST_USER_ID))

    args, error = verify_args(args)

    self.assertEqual(error, None)

  def test_verify_args_from_user_and_event_invalid_dependency(self):
    args = parse_cli("torq --from-user %s" % str(TEST_USER_ID))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --from-user"
                                     " is passed, but --event is not set to"
                                     " user-switch."))
    self.assertEqual(error.suggestion,
                     ("Set --event user-switch --from-user %s"
                      " to perform a user-switch from user"
                      " %s." % (str(TEST_USER_ID), str(TEST_USER_ID))))

  def test_verify_args_to_user_and_event_valid_dependency(self):
    args = parse_cli("torq -e user-switch --to-user %s" % str(TEST_USER_ID))

    args, error = verify_args(args)

    self.assertEqual(error, None)

  def test_verify_args_to_user_not_passed_and_event_invalid_dependency(self):
    args = parse_cli("torq -e user-switch")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --to-user is"
                                     " not passed."))
    self.assertEqual(error.suggestion, ("Set --event user-switch --to-user"
                                        " <user-id> to perform a user-switch."))

  def test_verify_args_to_user_and_user_switch_not_set_invalid_dependency(self):
    args = parse_cli("torq --to-user %s" % str(TEST_USER_ID))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --to-user"
                                     " is passed, but --event is not set to"
                                     " user-switch."))
    self.assertEqual(error.suggestion,
                     ("Set --event user-switch --to-user %s"
                      " to perform a user-switch to user"
                      " %s." % (str(TEST_USER_ID), str(TEST_USER_ID))))

  def test_verify_args_app_and_event_valid_dependency(self):
    args = parse_cli("torq -e app-startup -a %s" % TEST_PACKAGE)

    args, error = verify_args(args)

    self.assertEqual(error, None)

  def test_verify_args_app_not_passed_and_event_invalid_dependency(self):
    args = parse_cli("torq -e app-startup")

    args, error = verify_args(args)

    self.assertEqual(error.message,
                     "Command is invalid because --app is not passed.")
    self.assertEqual(error.suggestion, ("Set --event app-startup --app "
                                        "<package> to perform an app-startup."))

  def test_verify_args_app_and_app_startup_not_set_invalid_dependency(self):
    args = parse_cli("torq -a %s" % TEST_PACKAGE)

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --app is"
                                     " passed and --event is not set to"
                                     " app-startup."))
    self.assertEqual(error.suggestion, ("To profile an app startup run:"
                                        " torq --event app-startup --app"
                                        " <package-name>"))

  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_profiler_and_simpleperf_event_valid_dependencies(
      self, mock_isdir, mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli("torq -p simpleperf --symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(len(args.simpleperf_event), 1)
    self.assertEqual(args.simpleperf_event[0], "cpu-cycles")

    args = parse_cli("torq -p simpleperf -s cpu-cycles "
                     "--symbols %s" % SYMBOLS_PATH)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(len(args.simpleperf_event), 1)
    self.assertEqual(args.simpleperf_event[0], "cpu-cycles")

  def test_verify_args_profiler_and_simpleperf_event_invalid_dependencies(self):
    args = parse_cli("torq -s cpu-cycles")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --simpleperf-event cannot be passed if"
                                     " --profiler is not set to simpleperf."))
    self.assertEqual(error.suggestion, ("To capture the simpleperf event run:"
                                        " torq --profiler simpleperf"
                                        " --simpleperf-event cpu-cycles"))

  def test_profiler_and_perfetto_config_valid_dependency(self):
    args = parse_cli(("torq -p perfetto --perfetto-config"
                      " lightweight"))

    args, error = verify_args(args)

    self.assertEqual(error, None)

  def test_verify_args_profiler_and_perfetto_config_invalid_dependency(self):
    args = parse_cli("torq -p simpleperf --perfetto-config"
                     " lightweight")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --perfetto-config cannot be passed if"
                                     " --profiler is not set to perfetto."))
    self.assertEqual(error.suggestion, ("Set --profiler perfetto to choose a"
                                        " perfetto-config to use."))

  def test_verify_args_runs_and_between_dur_ms_valid_dependency(self):
    args = parse_cli("torq -r 2 --between-dur-ms 5000")

    args, error = verify_args(args)

    self.assertEqual(error, None)

  def test_verify_args_runs_and_between_dur_ms_invalid_dependency(self):
    args = parse_cli("torq --between-dur-ms 5000")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --between-dur-ms cannot be passed"
                                     " if --runs is not a value greater"
                                     " than 1."))
    self.assertEqual(error.suggestion, "Set --runs 2 to run 2 tests.")

    args = parse_cli("torq -r 1 --between-dur-ms 5000")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --between-dur-ms cannot be passed"
                                     " if --runs is not a value greater"
                                     " than 1."))
    self.assertEqual(error.suggestion, "Set --runs 2 to run 2 tests.")

  def test_verify_args_profiler_and_ftrace_events_valid_dependencies(self):
    args = parse_cli(("torq --excluded-ftrace-events"
                      " syscall-enter"))

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.excluded_ftrace_events, ["syscall-enter"])

    args = parse_cli(("torq -p perfetto --excluded-ftrace-events"
                      " syscall-enter"))

    args, error = verify_args(args)

    self.assertEqual(args.excluded_ftrace_events, ["syscall-enter"])
    self.assertEqual(error, None)

    args = parse_cli(("torq -p perfetto --included-ftrace-events"
                      " syscall-enter"))

    args, error = verify_args(args)

    self.assertEqual(args.included_ftrace_events, ["syscall-enter"])
    self.assertEqual(error, None)

  def test_verify_args_profiler_and_ftrace_events_invalid_dependencies(self):
    args = parse_cli(("torq -p simpleperf"
                      " --excluded-ftrace-events syscall-enter"))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --excluded-ftrace-events cannot be"
                                     " passed if --profiler is not set to"
                                     " perfetto."))
    self.assertEqual(error.suggestion, ("Set --profiler perfetto to exclude an"
                                        " ftrace event from perfetto config."))

    args = parse_cli(("torq -p simpleperf"
                      " --included-ftrace-events syscall-enter"))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --included-ftrace-events cannot be"
                                     " passed if --profiler is not set to"
                                     " perfetto."))
    self.assertEqual(error.suggestion, ("Set --profiler perfetto to include"
                                        " an ftrace event in perfetto config."))

  def test_verify_args_multiple_valid_excluded_ftrace_events(self):
    args = parse_cli(("torq --excluded-ftrace-events"
                      " power/cpu_idle --excluded-ftrace-events"
                      " ion/ion_stat"))

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.excluded_ftrace_events,
                     ["power/cpu_idle", "ion/ion_stat"])

  def test_verify_args_multiple_invalid_excluded_ftrace_events(self):
    args = parse_cli(("torq --excluded-ftrace-events"
                      " power/cpu_idle --excluded-ftrace-events"
                      " power/cpu_idle"))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because duplicate"
                                     " ftrace events cannot be"
                                     " included in --excluded-ftrace-events."))
    self.assertEqual(error.suggestion, ("--excluded-ftrace-events should only"
                                        " include one instance of an ftrace"
                                        " event."))

  def test_verify_args_multiple_valid_included_ftrace_events(self):
    args = parse_cli(("torq --included-ftrace-events"
                      " power/cpu_idle --included-ftrace-events"
                      " ion/ion_stat"))

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.included_ftrace_events,
                     ["power/cpu_idle", "ion/ion_stat"])

  def test_verify_args_multiple_invalid_included_ftrace_events(self):
    args = parse_cli(("torq --included-ftrace-events"
                      " power/cpu_idle --included-ftrace-events"
                      " power/cpu_idle"))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because duplicate"
                                     " ftrace events cannot be"
                                     " included in --included-ftrace-events."))
    self.assertEqual(error.suggestion, ("--included-ftrace-events should only"
                                        " include one instance of an ftrace"
                                        " event."))

  def test_verify_args_invalid_overlap_ftrace_events(self):
    args = parse_cli(("torq --excluded-ftrace-events"
                      " ion/ion_stat --excluded-ftrace-events"
                      " power/cpu_idle --excluded-ftrace-events"
                      " power/gpu_frequency --included-ftrace-events"
                      " ion/ion_stat --included-ftrace-events"
                      " power/cpu_idle --included-ftrace-events"
                      " ftrace/print"))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because ftrace"
                                     " event(s): ion/ion_stat, power/cpu_idle"
                                     " cannot be both included and excluded."))
    self.assertEqual(error.suggestion, ("Only set --excluded-ftrace-events"
                                        " ion/ion_stat if you want to"
                                        " exclude ion/ion_stat from the"
                                        " config or --included-ftrace-events"
                                        " ion/ion_stat if you want to"
                                        " include ion/ion_stat in the"
                                        " config.\n\t"
                                        " Only set --excluded-ftrace-events"
                                        " power/cpu_idle if you want to"
                                        " exclude power/cpu_idle from the"
                                        " config or --included-ftrace-events"
                                        " power/cpu_idle if you want to"
                                        " include power/cpu_idle in the"
                                        " config."))

  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_multiple_valid_simpleperf_events(self, mock_isdir,
                                                        mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli(("torq -p simpleperf -s cpu-cycles"
                      " -s instructions --symbols %s" % SYMBOLS_PATH))

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.simpleperf_event, ["cpu-cycles", "instructions"])

  def test_verify_args_multiple_invalid_simpleperf_events(self):
    args = parse_cli(("torq -p simpleperf -s cpu-cycles"
                      " -s cpu-cycles"))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because redundant"
                                     " calls to --simpleperf-event cannot"
                                     " be made."))
    self.assertEqual(error.suggestion, ("Only set --simpleperf-event cpu-cycles"
                                        " once if you want to collect"
                                        " cpu-cycles."))

  def test_verify_args_trigger_names(self):
    args = parse_cli("torq --trigger-names %s" % " ".join(TEST_TRIGGER_NAMES))

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.trigger_names, TEST_TRIGGER_NAMES)
    self.assertEqual(args.trigger_timeout_ms, DEFAULT_TRIGGER_DUR_MS)
    self.assertEqual(args.trigger_stop_delay_ms, DEFAULT_TRIGGER_STOP_DELAY_MS)

  @mock.patch.object(os.path, "exists", autospec=True)
  @mock.patch.object(os.path, "isdir", autospec=True)
  def test_verify_args_trigger_names_invalid_profiler(self, mock_isdir,
                                                      mock_exists):
    mock_isdir.return_value = True
    mock_exists.return_value = True
    args = parse_cli("torq -p simpleperf --symbols %s --trigger-names %s" %
                     (SYMBOLS_PATH, " ".join(TEST_TRIGGER_NAMES)))

    args, error = verify_args(args)

    self.assertEqual(
        error.message,
        ("Command is invalid because --trigger-names cannot be passed"
         " if --profiler is not set to perfetto."))
    self.assertEqual(error.suggestion, "Set -p perfetto to use trigger-names.")

  def test_verify_args_trigger_names_with_dur_ms(self):
    args = parse_cli("torq --dur-ms 3000 --trigger-names %s" %
                     " ".join(TEST_TRIGGER_NAMES))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --dur-ms"
                                     " cannot be passed if a perfetto trigger"
                                     " is being set."))
    self.assertEqual(error.suggestion, ("Run command with a"
                                        " --trigger-timeout-ms option instead"
                                        " of --dur-ms."))

  def test_verify_args_trigger_names_with_multiple_runs(self):
    args = parse_cli("torq -r 2 --trigger-names %s" %
                     " ".join(TEST_TRIGGER_NAMES))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because the number of"
                                     " runs cannot be more than 1 when"
                                     " including trigger configs."))
    self.assertEqual(error.suggestion, ("Run command without the -r"
                                        " option."))

  def test_verify_args_trigger_timeout_ms_no_trigger_names(self):
    args = parse_cli("torq --trigger-timeout-ms %s" % TEST_TRIGGER_DUR_MS)

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --trigger-timeout-ms cannot be set"
                                     " without --trigger-names."))
    self.assertEqual(error.suggestion, ("Set --trigger-names or remove"
                                        " --trigger-timeout-ms."))

  def test_verify_args_trigger_stop_delay_ms_no_trigger_names(self):
    args = parse_cli("torq --trigger-stop-delay-ms %s" %
                     TEST_TRIGGER_STOP_DELAY_MS)

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --trigger-stop-delay-ms cannot be set"
                                     " without --trigger-names."))
    self.assertEqual(error.suggestion, ("Set --trigger-names or remove"
                                        " --trigger-stop-delay-ms."))

  def test_verify_args_trigger_mode_no_trigger_names(self):
    args = parse_cli("torq --trigger-mode %s" % TEST_TRIGGER_MODE)

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --trigger-mode cannot be set"
                                     " without --trigger-names."))
    self.assertEqual(error.suggestion, ("Set --trigger-names or remove"
                                        " --trigger-mode."))

  def test_verify_args_too_many_trigger_stop_delay_ms(self):
    args = parse_cli("torq --trigger-names %s --trigger-stop-delay-ms %s %s" %
                     (TEST_TRIGGER_NAMES[0], TEST_TRIGGER_STOP_DELAY_MS,
                      TEST_TRIGGER_STOP_DELAY_MS))

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because number of"
                                     " trigger names passed is not equal to"
                                     " number of stop-delay-ms values passed."))
    self.assertEqual(error.suggestion, ("Pass only one stop-delay-ms value to"
                                        " use for all triggers, pass none to"
                                        " use the default value for all"
                                        " triggers, or pass an equal number of"
                                        " trigger names and stop-delay-ms"
                                        " values."))

  def test_verify_args_invalid_trigger_stop_delay_ms(self):
    args = parse_cli("torq --trigger-names %s --trigger-stop-delay-ms %d" %
                     (TEST_TRIGGER_NAMES[0], MIN_STOP_DELAY_MS - 1))

    args, error = verify_args(args)

    self.assertEqual(
        error.message,
        ("Command is invalid because --trigger-stop-delay-ms cannot be set to a"
         " value smaller than %d." % MIN_STOP_DELAY_MS))
    self.assertEqual(
        error.suggestion,
        ("Set --trigger-stop-delay-ms %d to keep tracing after a trigger for %d"
         " seconds." % (MIN_STOP_DELAY_MS, (MIN_STOP_DELAY_MS / 1000))))

  def test_verify_args_invalid_trigger_timeout_ms(self):
    args = parse_cli("torq --trigger-names %s --trigger-timeout-ms %d" %
                     (TEST_TRIGGER_NAMES[0], MIN_DURATION_MS - 1))

    args, error = verify_args(args)

    self.assertEqual(
        error.message,
        ("Command is invalid because --trigger-timeout-ms cannot be set to a"
         " value smaller than %d." % MIN_DURATION_MS))
    self.assertEqual(
        error.suggestion,
        ("Set --trigger-timeout-ms %d to timeout after %d seconds." %
         (MIN_DURATION_MS, (MIN_DURATION_MS / 1000))))

  def test_create_parser_invalid_perfetto_config_command(self):
    parser, error = create_parser_from_cli("torq --perfetto-config")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_verify_args_invalid_mixing_of_profiler_and_config_subcommand(self):
    parser, error = create_parser_from_cli(
        "torq -d 20000 config pull lightweight")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_get_command_profiler(self):
    args = parse_cli("torq -d 20000")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.subcommands, "profiler")

  def test_create_parser_valid_config_show_values(self):
    args = parse_cli("torq config show default")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.config_name, "default")

    args = parse_cli("torq config show lightweight")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.config_name, "lightweight")

    args = parse_cli("torq config show memory")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.config_name, "memory")

  def test_create_parser_invalid_config_show_values(self):
    parser, error = create_parser_from_cli("torq config show fake-config")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_create_parser_valid_config_pull_values(self):
    args = parse_cli("torq config pull default")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.config_name, "default")

    args = parse_cli("torq config pull lightweight")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.config_name, "lightweight")

    args = parse_cli("torq config pull memory")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.config_name, "memory")

  def test_create_parser_invalid_config_pull_values(self):
    parser, error = create_parser_from_cli("torq config pull fake-config")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_verify_args_invalid_config_subcommands(self):
    args = parse_cli("torq config")

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because torq config"
                                     " cannot be called without a"
                                     " subcommand."))
    self.assertEqual(error.suggestion, ("Use one of the following"
                                        " subcommands:\n"
                                        "\t torq config list\n"
                                        "\t torq config show\n"
                                        "\t torq config pull\n"))

  def test_create_parser_invalid_config_subcommands(self):
    parser, error = create_parser_from_cli("torq config get")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  def test_verify_args_default_config_pull_filepath(self):
    args = parse_cli("torq config pull default")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.file_path, "./default.pbtxt")

    args = parse_cli("torq config pull lightweight")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.file_path, "./lightweight.pbtxt")

    args = parse_cli("torq config pull memory")

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.file_path, "./memory.pbtxt")

  @mock.patch.object(os.path, "isfile", autospec=True)
  def test_verify_args_default_config_pull_invalid_filepath(self, mock_is_file):
    mock_invalid_file_path = "mock-invalid-file-path"
    mock_is_file.return_value = False
    args = parse_cli(("torq config pull default %s" % mock_invalid_file_path))

    args, error = verify_args(args)

    self.assertEqual(error.message,
                     ("Command is invalid because %s is not a valid filepath." %
                      mock_invalid_file_path))
    self.assertEqual(
        error.suggestion,
        ("A default filepath can be used if you do not specify a file-path:\n\t"
         " torq pull default to copy to ./default.pbtxt\n\t"
         " torq pull lightweight to copy to ./lightweight.pbtxt\n\t "
         "torq pull memory to copy to ./memory.pbtxt"))

  def test_get_command_config_list(self):
    args = parse_cli("torq config list")

    args, error = verify_args(args)
    command = create_config_command(args)

    self.assertEqual(error, None)
    self.assertEqual(command.get_type(), "config list")

  def test_get_command_config_show(self):
    args = parse_cli("torq config show default")

    args, error = verify_args(args)
    command = create_config_command(args)

    self.assertEqual(error, None)
    self.assertEqual(command.get_type(), "config show")

  def test_get_command_config_pull(self):
    args = parse_cli("torq config pull default")

    args, error = verify_args(args)
    command = create_config_command(args)

    self.assertEqual(error, None)
    self.assertEqual(command.get_type(), "config pull")

  @parameterized_config_builder()
  def test_verify_args_config_trigger_names(self, config_subcommand):
    args = parse_cli(f'torq config {config_subcommand} default --trigger-names'
                     f' {" ".join(TEST_TRIGGER_NAMES)}')

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.trigger_names, TEST_TRIGGER_NAMES)
    self.assertEqual(args.trigger_timeout_ms, DEFAULT_TRIGGER_DUR_MS)
    self.assertEqual(args.trigger_stop_delay_ms, DEFAULT_TRIGGER_STOP_DELAY_MS)
    self.assertEqual(args.trigger_mode, DEFAULT_TRIGGER_MODE)
    self.assertEqual(args.profiler, "perfetto")
    self.assertEqual(args.runs, 1)

  @parameterized_config_builder()
  def test_verify_args_config_trigger_names_with_dur_ms(self,
                                                        config_subcommand):
    args = parse_cli(
        f'torq config {config_subcommand} default --dur-ms 3000 --trigger-names'
        f' {" ".join(TEST_TRIGGER_NAMES)}')

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because --dur-ms"
                                     " cannot be passed if a perfetto trigger"
                                     " is being set."))
    self.assertEqual(error.suggestion, ("Run command with a"
                                        " --trigger-timeout-ms option instead"
                                        " of --dur-ms."))

  @parameterized_config_builder()
  def test_verify_args_config_trigger_timeout_ms_no_trigger_names(
      self, config_subcommand):
    args = parse_cli(
        f'torq config {config_subcommand} default --trigger-timeout-ms'
        f' {TEST_TRIGGER_DUR_MS}')

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --trigger-timeout-ms cannot be set"
                                     " without --trigger-names."))
    self.assertEqual(error.suggestion, ("Set --trigger-names or remove"
                                        " --trigger-timeout-ms."))

  @parameterized_config_builder()
  def test_verify_args_config_trigger_stop_delay_ms_no_trigger_names(
      self, config_subcommand):
    args = parse_cli(
        f'torq config {config_subcommand} default --trigger-stop-delay-ms'
        f' {TEST_TRIGGER_STOP_DELAY_MS}')

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --trigger-stop-delay-ms cannot be set"
                                     " without --trigger-names."))
    self.assertEqual(error.suggestion, ("Set --trigger-names or remove"
                                        " --trigger-stop-delay-ms."))

  @parameterized_config_builder()
  def test_verify_args_config_trigger_mode_no_trigger_names(
      self, config_subcommand):
    args = parse_cli(f'torq config {config_subcommand} default --trigger-mode'
                     f' {TEST_TRIGGER_MODE}')

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because"
                                     " --trigger-mode cannot be set"
                                     " without --trigger-names."))
    self.assertEqual(error.suggestion, ("Set --trigger-names or remove"
                                        " --trigger-mode."))

  @parameterized_config_builder()
  def test_verify_args_config_too_many_trigger_stop_delay_ms(
      self, config_subcommand):
    args = parse_cli(
        f'torq config {config_subcommand} default --trigger-names'
        f' {TEST_TRIGGER_NAMES[0]} --trigger-stop-delay-ms'
        f' {TEST_TRIGGER_STOP_DELAY_MS} {TEST_TRIGGER_STOP_DELAY_MS}')

    args, error = verify_args(args)

    self.assertEqual(error.message, ("Command is invalid because number of"
                                     " trigger names passed is not equal to"
                                     " number of stop-delay-ms values passed."))
    self.assertEqual(error.suggestion, ("Pass only one stop-delay-ms value to"
                                        " use for all triggers, pass none to"
                                        " use the default value for all"
                                        " triggers, or pass an equal number of"
                                        " trigger names and stop-delay-ms"
                                        " values."))

  @parameterized_config_builder()
  def test_verify_args_config_multiple_trigger_names_and_multiple_trigger_stop_delay_ms(
      self, config_subcommand):
    args = parse_cli(
        f'torq config {config_subcommand} default --trigger-names'
        f' {" ".join(TEST_TRIGGER_NAMES)} --trigger-stop-delay-ms'
        f' {TEST_TRIGGER_STOP_DELAY_MS} {TEST_TRIGGER_STOP_DELAY_MS}')

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.trigger_names, TEST_TRIGGER_NAMES)
    self.assertEqual(args.trigger_timeout_ms, DEFAULT_TRIGGER_DUR_MS)
    self.assertEqual(args.trigger_stop_delay_ms,
                     [TEST_TRIGGER_STOP_DELAY_MS, TEST_TRIGGER_STOP_DELAY_MS])
    self.assertEqual(args.trigger_mode, DEFAULT_TRIGGER_MODE)
    self.assertEqual(args.profiler, "perfetto")
    self.assertEqual(args.runs, 1)

  @parameterized_config_builder()
  def test_verify_args_config_invalid_trigger_stop_delay_ms(
      self, config_subcommand):
    args = parse_cli(f'torq config {config_subcommand} default --trigger-names'
                     f' {TEST_TRIGGER_NAMES[0]} --trigger-stop-delay-ms'
                     f' {MIN_STOP_DELAY_MS - 1}')

    args, error = verify_args(args)

    self.assertEqual(
        error.message,
        ("Command is invalid because --trigger-stop-delay-ms cannot be set to a"
         " value smaller than %d." % MIN_STOP_DELAY_MS))
    self.assertEqual(
        error.suggestion,
        ("Set --trigger-stop-delay-ms %d to keep tracing after a trigger for %d"
         " seconds." % (MIN_STOP_DELAY_MS, (MIN_STOP_DELAY_MS / 1000))))

  @parameterized_config_builder()
  def test_verify_args_config_invalid_trigger_timeout_ms(
      self, config_subcommand):
    args = parse_cli(
        f'torq config {config_subcommand} default --trigger-names'
        f' {TEST_TRIGGER_NAMES[0]} --trigger-timeout-ms {MIN_DURATION_MS - 1}')

    args, error = verify_args(args)

    self.assertEqual(
        error.message,
        ("Command is invalid because --trigger-timeout-ms cannot be set to a"
         " value smaller than %d." % MIN_DURATION_MS))
    self.assertEqual(
        error.suggestion,
        ("Set --trigger-timeout-ms %d to timeout after %d seconds." %
         (MIN_DURATION_MS, (MIN_DURATION_MS / 1000))))

  @mock.patch.object(os.path, "exists", autospec=True)
  def test_create_parser_valid_open_subcommand(self, mock_exists):
    mock_exists.return_value = True
    args = parse_cli("torq open %s" % TEST_FILE)

    args, error = verify_args(args)

    self.assertEqual(error, None)
    self.assertEqual(args.file_path, TEST_FILE)

  def test_create_parser_open_subcommand_no_file(self):
    parser, error = create_parser_from_cli("torq open")

    self.assertEqual(error, None)
    with self.assertRaises(SystemExit):
      parser.parse_args()

  @mock.patch.object(os.path, "exists", autospec=True)
  def test_create_parser_open_subcommand_invalid_file(self, mock_exists):
    mock_exists.return_value = False
    args = parse_cli("torq open %s" % TEST_FILE)

    args, error = verify_args(args)

    self.assertEqual(
        error.message, "Command is invalid because %s is an "
        "invalid file path." % TEST_FILE)
    self.assertEqual(error.suggestion, "Make sure your file exists.")


if __name__ == '__main__':
  unittest.main()
