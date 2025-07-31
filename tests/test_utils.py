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

import sys
from src.torq import create_parser, run


def parameterized(items, setup_func):
  """
  Function to create a decorator function that parameterizes a test method using
  unittest.subTest given a setup function and a list of items.

  Args:
      items: A list of items to iterate over for the test.
      setup_func: A function to setup subtests.

  Returns:
      A decorator function that runs setup function and subtests for each item.
  """

  def decorator(test_method):

    def decorated_test(self, *args, **kwargs):
      for item in items:
        with self.subTest(item=item):
          setup_func(self, item)
          test_method(self, item, *args, **kwargs)

    return decorated_test

  return decorator


def parameterized_profiler(setup_func):
  return parameterized(["perfetto", "simpleperf"], setup_func)


def create_parser_from_cli(command_string):
  sys.argv = command_string.split()
  return create_parser()


def parse_cli(command_string):
  parser = create_parser_from_cli(command_string)
  return parser.parse_args()


def run_cli(command_string):
  sys.argv = command_string.split()
  run()
