# Copyright (C) 2025 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")

py_library(
    name = "torq_lib",
    srcs = glob(["src/**/*.py"]),
)

py_binary(
    name = "torq",
    srcs = ["main.py"],
    main = "main.py",
    deps = [":torq_lib"],
)

py_library(
    name = "torq_test_lib",
    srcs = ["tests/test_utils.py"],
)

py_test(
    name = "torq_unit_test",
    srcs = ["tests/torq_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "device_unit_test",
    srcs = ["tests/device_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "config_builder_unit_test",
    srcs = ["tests/config_builder_unit_test.py"],
    deps = [":torq_lib"],
)

py_test(
    name = "profiler_command_executor_unit_test",
    srcs = ["tests/profiler_command_executor_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "config_command_executor_unit_test",
    srcs = ["tests/config_command_executor_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "validate_simpleperf_unit_test",
    srcs = ["tests/validate_simpleperf_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "utils_unit_test",
    srcs = ["tests/utils_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "open_ui_unit_test",
    srcs = ["tests/open_ui_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "vm_unit_test",
    srcs = ["tests/vm_unit_test.py"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)
