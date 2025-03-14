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

from .validation_error import ValidationError

class HandleInput:
  """Class that requests input from the user with a message and then calls a
  callback based on the user's input, or gives an error if no valid input was
  given

  Attributes:
    input_msg: A string containing a message that is displayed when requesting user input
    fail_suggestion: A string containing a suggestion displayed when the user exceeds max attempts
    choices: A dictionary mapping possible user inputs (key) to functions (value)
    default_choice: A default choice from the choices dictionary if the user inputs nothing.
  """
  def __init__(self, input_msg, fail_suggestion, choices,
      default_choice = None):
    self.input_msg = input_msg
    self.fail_suggestion = fail_suggestion
    self.choices = choices
    self.max_attempts = 3
    if default_choice is not None and default_choice not in choices:
      raise Exception("Default choice is not in choices dictionary.")
    self.default_choice = default_choice

  def handle_input(self):
    i = 0
    while i < self.max_attempts:
      response = input(self.input_msg).lower()

      if response == "" and self.default_choice is not None:
        return self.choices[self.default_choice]()
      elif response in self.choices:
        return self.choices[response]()

      i += 1
      if i < self.max_attempts:
        print("Invalid input. Please try again.")

    return ValidationError("Invalid inputs.",
                           self.fail_suggestion)
