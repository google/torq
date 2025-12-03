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

import signal

from abc import ABC, abstractmethod

ANDROID_SDK_VERSION_S = 32
ANDROID_SDK_VERSION_T = 33
PERFETTO_VERSION_WITH_MULTI_VM_SUPPORT = 54


class Command(ABC):
  """
  Abstract base class representing a command.
  """

  def __init__(self, type):
    self.type = type

  def get_type(self):
    return self.type

  @abstractmethod
  def validate(self, device):
    raise NotImplementedError


# TODO(b/433995149): Remove, only used by profiler subcommand
class CommandExecutor(ABC):
  """
  Abstract base class representing a command executor.
  """

  def __init__(self):
    pass

  def execute(self, command, device):
    for sig in [signal.SIGINT, signal.SIGTERM]:
      signal.signal(sig, lambda s, f: self.signal_handler(s, f))
    error = device.check_device_connection()
    if error is not None:
      return error
    device.root_device()
    error = command.validate(device)
    if error is not None:
      return error
    return self.execute_command(command, device)

  @abstractmethod
  def execute_command(self, command, device):
    raise NotImplementedError

  def signal_handler(self, sig, frame):
    pass


class ValidationError:

  def __init__(self, message, suggestion):
    self.message = message
    self.suggestion = suggestion
