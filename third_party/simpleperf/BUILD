# Copyright (C) 2026 The Android Open Source Project
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

# simpleperf host scripts (Apache-2.0, from AOSP platform/system/extras) that
# torq runs to convert simpleperf traces. The files are fetched from a pinned
# commit and verified by sha256 at build time (see MODULE.bazel), then decoded
# from Gitiles' base64 '?format=TEXT' encoding into the directory layout that
# the scripts expect (scripts/ and scripts/bin/<os>/x86_64/).

package(default_visibility = ["//visibility:public"])

genrule(
    name = "simpleperf_binary_cache_builder",
    srcs = ["@simpleperf_binary_cache_builder//file"],
    outs = ["scripts/binary_cache_builder.py"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_gecko_profile_generator",
    srcs = ["@simpleperf_gecko_profile_generator//file"],
    outs = ["scripts/gecko_profile_generator.py"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_simpleperf_utils",
    srcs = ["@simpleperf_simpleperf_utils//file"],
    outs = ["scripts/simpleperf_utils.py"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_simpleperf_report_lib",
    srcs = ["@simpleperf_simpleperf_report_lib//file"],
    outs = ["scripts/simpleperf_report_lib.py"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_etm_types",
    srcs = ["@simpleperf_etm_types//file"],
    outs = ["scripts/etm_types.py"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_report_sample_pb2",
    srcs = ["@simpleperf_report_sample_pb2//file"],
    outs = ["scripts/report_sample_pb2.py"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_libsimpleperf_report_linux",
    srcs = ["@simpleperf_libsimpleperf_report_linux//file"],
    outs = ["scripts/bin/linux/x86_64/libsimpleperf_report.so"],
    cmd = "base64 --decode < $< > $@",
)

genrule(
    name = "simpleperf_libsimpleperf_report_darwin",
    srcs = ["@simpleperf_libsimpleperf_report_darwin//file"],
    outs = ["scripts/bin/darwin/x86_64/libsimpleperf_report.dylib"],
    cmd = "base64 --decode < $< > $@",
)

filegroup(
    name = "simpleperf_scripts",
    srcs = [
        ":simpleperf_binary_cache_builder",
        ":simpleperf_etm_types",
        ":simpleperf_gecko_profile_generator",
        ":simpleperf_report_sample_pb2",
        ":simpleperf_simpleperf_report_lib",
        ":simpleperf_simpleperf_utils",
    ] + select({
        "@platforms//os:linux": [":simpleperf_libsimpleperf_report_linux"],
        "@platforms//os:macos": [":simpleperf_libsimpleperf_report_darwin"],
        "//conditions:default": [],
    }),
)
