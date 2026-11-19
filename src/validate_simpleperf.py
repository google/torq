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
from .pinned_files import (PinnedDownloadError, SIMPLEPERF_BASE_URL,
                           SIMPLEPERF_EXECUTABLES, download_pinned_files,
                           ensure_private_dir, get_simpleperf_cache_dir,
                           get_simpleperf_files, verify_files)
from .utils import path_exists, dir_exists, is_bazel

SIMPLEPERF_SCRIPTS_DIR = "/system/extras/simpleperf/scripts"
BUILDER_SCRIPT = SIMPLEPERF_SCRIPTS_DIR + "/binary_cache_builder.py"
# Pinned simpleperf scripts that Bazel fetches and verifies at build time (see
# MODULE.bazel and third_party/simpleperf/BUILD), relative to the torq root.
BUNDLED_SIMPLEPERF_SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "third_party",
    "simpleperf", "scripts")


def verify_simpleperf_args(args):
  args.simpleperf_scripts_dir = None
  if not is_bazel() and ("ANDROID_BUILD_TOP" in os.environ and
                         path_exists(os.environ["ANDROID_BUILD_TOP"] +
                                     BUILDER_SCRIPT)):
    args.simpleperf_scripts_dir = (
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

  if args.simpleperf_scripts_dir is not None:
    return args, None

  if bundled_simpleperf_scripts_exist():
    args.simpleperf_scripts_dir = BUNDLED_SIMPLEPERF_SCRIPTS_DIR
    return args, None

  cache_dir = get_simpleperf_cache_dir()
  try:
    ensure_private_dir(os.path.dirname(cache_dir))
  except (OSError, PinnedDownloadError) as e:
    return None, ValidationError(
        "Cannot use the torq cache directory: %s" % e,
        "Make sure '%s' is a directory owned by you that only you can"
        " write to." % os.path.dirname(cache_dir))

  if not cached_simpleperf_scripts_exist():
    error = download_simpleperf_scripts()
    if error is not None:
      return None, error

  args.simpleperf_scripts_dir = cache_dir
  return args, None


def download_simpleperf_scripts():
  cache_dir = get_simpleperf_cache_dir()
  fail_suggestion = ("Set $ANDROID_BUILD_TOP to your android root "
                     "path and make sure you have $ANDROID_BUILD_TOP"
                     "/system/extras/simpleperf/scripts "
                     "downloaded.")

  def download_accepted_callback():
    try:
      download_pinned_files(
          SIMPLEPERF_BASE_URL,
          get_simpleperf_files(),
          cache_dir,
          executables=SIMPLEPERF_EXECUTABLES)
    except (OSError, PinnedDownloadError) as e:
      return ValidationError(
          "Error while downloading simpleperf scripts: %s" % e,
          "Try again or " + fail_suggestion[0].lower() + fail_suggestion[1:])
    return None

  def rejected_callback():
    return ValidationError("Did not download simpleperf scripts.",
                           fail_suggestion)

  return (HandleInput(("You do not have an Android Root configured "
                       "with the simpleperf directory. To use "
                       "simpleperf, torq will download pinned, checksum-"
                       "verified simpleperf scripts to '%s'. Are you ok "
                       "with this download? [Y/n]: " % cache_dir),
                      fail_suggestion, {
                          "y": download_accepted_callback,
                          "n": rejected_callback
                      },
                      default_choice="y").handle_input())


def bundled_simpleperf_scripts_exist():
  return verify_files(
      BUNDLED_SIMPLEPERF_SCRIPTS_DIR,
      get_simpleperf_files(),
      follow_symlinks=True)


def cached_simpleperf_scripts_exist():
  cache_dir = get_simpleperf_cache_dir()
  if not os.path.isdir(cache_dir):
    return False
  try:
    ensure_private_dir(cache_dir)
  except (OSError, PinnedDownloadError):
    return False
  return verify_files(cache_dir, get_simpleperf_files())
