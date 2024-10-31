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

from validation_error import ValidationError

class HandleInput:
  def __init__(self, input_msg, fail_suggestion, yes_callback_func,
      no_callback_func):
    self.input_msg = input_msg
    self.fail_suggestion = fail_suggestion
    self.yes_callback_func = yes_callback_func
    self.no_callback_func = no_callback_func
    self.max_attempts = 3

  def handle_input(self):
    i = 0
    while i < self.max_attempts:
      confirmation = input(self.input_msg)

      if confirmation.lower() == "y":
        return self.yes_callback_func()
      if confirmation.lower() == "n":
        return self.no_callback_func()

      print("Invalid input. Please try again.")
      i += 1

    return ValidationError("Invalid inputs.",
                           self.fail_suggestion)
