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
load("@pypi//:requirements.bzl", "requirement")
load("@python_versions//3.11:defs.bzl", compile_pip_requirements_3_11 = "compile_pip_requirements")

# This stanza calls a rule that generates targets for managing pip dependencies
# with pip-compile.
compile_pip_requirements_3_11(
    name = "requirements_3_11",
    extra_args = ["--allow-unsafe"],
    requirements_in = "requirements.in",
    requirements_txt = "requirements_lock_3_11.txt",
)

py_library(
    name = "torq_lib",
    srcs = glob(["src/**/*.py"]),
    deps = [
        requirement("pandas"),
        requirement("perfetto"),
    ],
)

py_binary(
    name = "torq",
    srcs = ["main.py"],
    main = "main.py",
    deps = [":torq_lib"],
)

py_binary(
    name = "torq-serial",
    srcs = ["serial/serial.py"],
    main = "serial/serial.py",
)

py_library(
    name = "torq_test_lib",
    srcs = ["tests/test_utils.py"],
)

py_test(
    name = "torq_unit_test",
    srcs = ["tests/torq_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "device_unit_test",
    srcs = ["tests/device_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "config_builder_unit_test",
    srcs = ["tests/config_builder_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "profiler_command_executor_unit_test",
    srcs = ["tests/profiler_command_executor_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "config_command_executor_unit_test",
    srcs = ["tests/config_command_executor_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "validate_simpleperf_unit_test",
    srcs = ["tests/validate_simpleperf_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "utils_unit_test",
    srcs = ["tests/utils_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "open_ui_unit_test",
    srcs = ["tests/open_ui_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "vm_unit_test",
    srcs = ["tests/vm_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "trigger_unit_test",
    srcs = ["tests/trigger_unit_test.py"],
    tags = ["unit"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_binary(
    name = "build_prebuilt",
    srcs = ["tools/build_prebuilt.py"],
    main = "tools/build_prebuilt.py",
    deps = [":torq_lib"],
)

py_test(
    name = "prebuilt_unit_test",
    srcs = ["tests/prebuilt_unit_test.py"],
    tags = ["unit"],
    data = [
        "main.py",
        "tools/build_prebuilt.py",
    ] + glob(["src/**/*.py"]),
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
)

py_test(
    name = "test_android_integration",
    srcs = ["tests/test_android_integration.py"],
    data = [":torq"],
    deps = [
        ":torq_lib",
        ":torq_test_lib",
    ],
    # external tag forces test run execution without relying on cached results
    tags = ["integration", "external"],
    # local flag allows test run on local environment without bazel sandboxing
    local = True,
)