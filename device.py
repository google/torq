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

from abc import ABC, abstractmethod


class Device(ABC):
  """
  Abstract base class representing a device. This class defines the APIs
  needed to interact with the current device.
  """

  @abstractmethod
  def __init__(self):
    raise NotImplementedError

  @abstractmethod
  def check_device_connection(self, command):
    raise NotImplementedError

  @abstractmethod
  def get_num_cpus(self):
    raise NotImplementedError

  @abstractmethod
  def get_memory(self):
    raise NotImplementedError

  @abstractmethod
  def get_max_num_cpus(self):
    raise NotImplementedError

  @abstractmethod
  def get_max_memory(self):
    raise NotImplementedError

  @abstractmethod
  def set_hw_config(self, hw_config):
    raise NotImplementedError

  @abstractmethod
  def set_num_cpus(self, num_cpus):
    raise NotImplementedError

  @abstractmethod
  def set_memory(self, memory):
    raise NotImplementedError

  @abstractmethod
  def app_exists(self, app):
    raise NotImplementedError

  @abstractmethod
  def simpleperf_event_exists(self, simpleperf_event):
    raise NotImplementedError

  @abstractmethod
  def user_exists(self, user):
    raise NotImplementedError


class AdbDevice(Device):
  """
  Class representing a device. APIs interact with the current device through
  the adb bridge.
  """
  def __init__(self):
    pass

  def check_device_connection(self, command):
    raise NotImplementedError

  def get_num_cpus(self):
    raise NotImplementedError

  def get_memory(self):
    raise NotImplementedError

  def get_max_num_cpus(self):
    raise NotImplementedError

  def get_max_memory(self):
    raise NotImplementedError

  def set_hw_config(self, hw_config):
    raise NotImplementedError

  def set_num_cpus(self, num_cpus):
    raise NotImplementedError

  def set_memory(self, memory):
    raise NotImplementedError

  def app_exists(self, app):
    raise NotImplementedError

  def simpleperf_event_exists(self, simpleperf_event):
    raise NotImplementedError

  def user_exists(self, user):
    raise NotImplementedError
