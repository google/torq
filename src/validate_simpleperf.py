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
import subprocess
from .base import ValidationError
from .handle_input import HandleInput
from .utils import path_exists, dir_exists, is_bazel, run_subprocess

TORQ_TEMP_DIR = "/tmp/.torq"
SIMPLEPERF_SCRIPTS_DIR = "/system/extras/simpleperf/scripts"
BUILDER_SCRIPT = SIMPLEPERF_SCRIPTS_DIR + "/binary_cache_builder.py"


def verify_simpleperf_args(args):
  args.scripts_path = TORQ_TEMP_DIR
  if not is_bazel() and ("ANDROID_BUILD_TOP" in os.environ and
                         path_exists(os.environ["ANDROID_BUILD_TOP"] +
                                     BUILDER_SCRIPT)):
    args.scripts_path = (
        os.environ["ANDROID_BUILD_TOP"] + SIMPLEPERF_SCRIPTS_DIR)

  if args.symbols is None or not dir_exists(args.symbols):
    if args.symbols is not None:
      return None, ValidationError(
          ("%s is not a valid path." % args.symbols),
          "Set --symbols to a valid symbols lib path or set "
          "$ANDROID_PRODUCT_OUT to your android product out directory "
          "(<ANDROID_BUILD_TOP>/out/target/product/<TARGET>).")
    if "ANDROID_PRODUCT_OUT" not in os.environ:
      return None, ValidationError(
          "ANDROID_PRODUCT_OUT is not set.",
          "Set --symbols to a valid symbols lib path or set "
          "$ANDROID_PRODUCT_OUT to your android product out directory "
          "(<ANDROID_BUILD_TOP>/out/target/product/<TARGET>).")
    if not dir_exists(os.environ["ANDROID_PRODUCT_OUT"]):
      return None, ValidationError(
          ("%s is not a valid $ANDROID_PRODUCT_OUT." %
           (os.environ["ANDROID_PRODUCT_OUT"])),
          "Set --symbols to a valid symbols lib path or set "
          "$ANDROID_PRODUCT_OUT to your android product out directory "
          "(<ANDROID_BUILD_TOP>/out/target/product/<TARGET>).")
    args.symbols = os.environ["ANDROID_PRODUCT_OUT"]

  if args.scripts_path != TORQ_TEMP_DIR or temp_simpleperf_scripts_exist():
    return args, None

  error = download_simpleperf_scripts()

  if error is not None:
    return None, error

  return args, None


def download_simpleperf_scripts():
  fail_suggestion = ("Set $ANDROID_BUILD_TOP to your android root "
                     "path and make sure you have $ANDROID_BUILD_TOP"
                     "/system/extras/simpleperf/scripts "
                     "downloaded.")

  def download_accepted_callback():
    run_subprocess(
        ("mkdir -p %s && wget -P %s "
         "https://android.googlesource.com/platform/system/extras"
         "/+archive/refs/heads/main/simpleperf/scripts.tar.gz "
         "&& tar -xvzf %s/scripts.tar.gz -C %s" %
         (TORQ_TEMP_DIR, TORQ_TEMP_DIR, TORQ_TEMP_DIR, TORQ_TEMP_DIR)),
        shell=True)

    if not temp_simpleperf_scripts_exist():
      raise Exception("Error while downloading simpleperf scripts. Try again "
                      "or set $ANDROID_BUILD_TOP to your android root path and "
                      "make sure you have $ANDROID_BUILD_TOP/system/extras/"
                      "simpleperf/scripts downloaded.")
    return None

  def rejected_callback():
    return ValidationError("Did not download simpleperf scripts.",
                           fail_suggestion)

  return (HandleInput(("You do not have an Android Root configured "
                       "with the simpleperf directory. To use "
                       "simpleperf, torq will download simpleperf "
                       "scripts to '%s'. Are you ok with this download?"
                       " [Y/N]: " % TORQ_TEMP_DIR), fail_suggestion, {
                           "y": download_accepted_callback,
                           "n": rejected_callback
                       }).handle_input())


def temp_simpleperf_scripts_exist():
  return path_exists(
      TORQ_TEMP_DIR + "/binary_cache_builder.py") and path_exists(
          TORQ_TEMP_DIR + "/gecko_profile_generator.py") and path_exists(
              TORQ_TEMP_DIR + "/simpleperf_utils.py") and path_exists(
                  TORQ_TEMP_DIR + "/simpleperf_report_lib.py")
