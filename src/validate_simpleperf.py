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
from .base import ValidationError
from .handle_input import HandleInput
from .utils import (path_exists, dir_exists, is_bazel, is_trusted_path,
                    run_subprocess)

TORQ_TEMP_DIR = "/tmp/.torq"
SIMPLEPERF_SCRIPTS_DIR = "/system/extras/simpleperf/scripts"
BUILDER_SCRIPT = SIMPLEPERF_SCRIPTS_DIR + "/binary_cache_builder.py"
GECKO_GENERATOR_SCRIPT = SIMPLEPERF_SCRIPTS_DIR + "/gecko_profile_generator.py"


def _validate_symbols_dir(symbols_path, invalid_message, untrusted_message):
  if not dir_exists(symbols_path):
    return ValidationError(
        invalid_message, "Set --symbols to a valid symbols lib path or set "
        "$ANDROID_PRODUCT_OUT to your android product out directory "
        "(<ANDROID_BUILD_TOP>/out/target/product/<TARGET>).")
  if not is_trusted_path(symbols_path, require_owner=False):
    return ValidationError(
        untrusted_message,
        "Ensure the symbols directory and its parent directories are not "
        "world-writable.")
  return None


def verify_simpleperf_args(args):
  args.simpleperf_scripts_dir = TORQ_TEMP_DIR
  android_build_top = os.environ.get("ANDROID_BUILD_TOP")
  if (not is_bazel() and android_build_top and
      path_exists(android_build_top + BUILDER_SCRIPT) and
      path_exists(android_build_top + GECKO_GENERATOR_SCRIPT)):
    builder_path = android_build_top + BUILDER_SCRIPT
    gecko_path = android_build_top + GECKO_GENERATOR_SCRIPT
    if not (is_trusted_path(builder_path, root_dir=android_build_top) and
            is_trusted_path(gecko_path, root_dir=android_build_top)):
      return None, ValidationError(
          ("Refusing to use untrusted simpleperf scripts under "
           "$ANDROID_BUILD_TOP: %s." %
           (android_build_top + SIMPLEPERF_SCRIPTS_DIR)),
          "Ensure $ANDROID_BUILD_TOP and its simpleperf scripts are owned by "
          "your user and not world-writable.")
    args.simpleperf_scripts_dir = android_build_top + SIMPLEPERF_SCRIPTS_DIR

  if args.symbols is not None:
    error = _validate_symbols_dir(
        args.symbols, ("%s is not a valid path." % args.symbols),
        ("Refusing to use untrusted symbols path: %s." % args.symbols))
    if error is not None:
      return None, error
  else:
    if "ANDROID_PRODUCT_OUT" not in os.environ:
      return None, ValidationError(
          "ANDROID_PRODUCT_OUT is not set.",
          "Set --symbols to a valid symbols lib path or set "
          "$ANDROID_PRODUCT_OUT to your android product out directory "
          "(<ANDROID_BUILD_TOP>/out/target/product/<TARGET>).")
    error = _validate_symbols_dir(
        os.environ["ANDROID_PRODUCT_OUT"],
        ("%s is not a valid $ANDROID_PRODUCT_OUT." %
         os.environ["ANDROID_PRODUCT_OUT"]),
        ("Refusing to use untrusted $ANDROID_PRODUCT_OUT path: %s." %
         os.environ["ANDROID_PRODUCT_OUT"]))
    if error is not None:
      return None, error
    args.symbols = os.environ["ANDROID_PRODUCT_OUT"]

  if args.simpleperf_scripts_dir != TORQ_TEMP_DIR or temp_simpleperf_scripts_exist(
  ):
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
                       " [Y/n]: " % TORQ_TEMP_DIR),
                      fail_suggestion, {
                          "y": download_accepted_callback,
                          "n": rejected_callback
                      },
                      default_choice="y").handle_input())


def temp_simpleperf_scripts_exist():
  return path_exists(
      TORQ_TEMP_DIR + "/binary_cache_builder.py") and path_exists(
          TORQ_TEMP_DIR + "/gecko_profile_generator.py") and path_exists(
              TORQ_TEMP_DIR + "/simpleperf_utils.py") and path_exists(
                  TORQ_TEMP_DIR + "/simpleperf_report_lib.py")
