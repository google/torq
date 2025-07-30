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

import argparse
from .base import Command, ValidationError

TRACED_ENABLE_PROP = "persist.traced.enable"
TRACED_RELAY_PRODUCER_PORT_PROP = "traced.relay_producer_port"
TRACED_RELAY_PORT_PROP = "traced_relay.relay_port"
TRACED_HYPERVISOR_PROP = "ro.traced.hypervisor"


def add_vm_parser(subparsers):
  vm_parser = subparsers.add_parser(
      'vm',
      help=('The vm subcommand is used '
            'to configure perfetto in '
            'virtualized Android.'))
  vm_subparsers = vm_parser.add_subparsers(dest='vm_subcommand')

  # Traced relay subcommand
  traced_relay_parser = vm_subparsers.add_parser(
      'traced-relay', help=('Configure traced_relay'))
  traced_relay_subparsers = traced_relay_parser.add_subparsers(
      dest='vm_traced_relay_subcommand')

  enable_tr_parser = traced_relay_subparsers.add_parser(
      'enable', help=('Enable traced_relay'))
  enable_tr_parser.add_argument(
      'relay_port', help='Socket address to communicate with traced.')

  traced_relay_subparsers.add_parser('disable', help=('Disable traced_relay'))

  # Traced relay producer subcommand
  relay_producer_parser = vm_subparsers.add_parser(
      'relay-producer', help=('Configure traced\'s relay '
                              'producer socket'))
  relay_producer_subparsers = \
        relay_producer_parser.add_subparsers(dest='vm_relay_producer_subcommand')

  enable_rp_parser = \
        relay_producer_subparsers.add_parser('enable',
                                             help=('Enable traced\'s relay producer port'))
  enable_rp_parser.add_argument(
      '--address',
      dest='relay_prod_port',
      default='vsock://-1:30001',
      help='Socket address used for relayed communication.')

  relay_producer_subparsers.add_parser(
      'disable', help=('Disable traced\'s relay producer port'))


def verify_vm_args(args):
  return args, None


def create_vm_command(args):
  if args.vm_subcommand == 'traced-relay':
    relay_port = None
    if args.vm_traced_relay_subcommand == 'enable':
      relay_port = args.relay_port

    return VmCommand(args.vm_subcommand, args.vm_traced_relay_subcommand,
                     relay_port, None)
  # relay-producer command
  relay_prod_port = None
  if args.vm_relay_producer_subcommand == 'enable':
    relay_prod_port = args.relay_prod_port
  return VmCommand(args.vm_subcommand, args.vm_relay_producer_subcommand, None,
                   relay_prod_port)


def traced_relay_execute(command, device):
  if command.subcommand == 'enable':
    if (len(device.get_prop(TRACED_HYPERVISOR_PROP)) == 0):
      # Traced_relay can only be used in virtualized environments,
      # therefore set the |TRACED_HYPERVISOR_PROP| to true if
      # enabling traced_relay.
      print(f"Setting sysprop \"{TRACED_HYPERVISOR_PROP}\" to \"true\"")
      device.set_prop(TRACED_HYPERVISOR_PROP, "true")
    device.set_prop(TRACED_RELAY_PORT_PROP, command.relay_port)
    device.set_prop(TRACED_ENABLE_PROP, "2")
  else:  # disable
    device.set_prop(TRACED_ENABLE_PROP, "1")
  return None


def relay_producer_execute(command, device):
  if command.subcommand == 'enable':
    device.set_prop(TRACED_ENABLE_PROP, "0")
    device.set_prop(TRACED_RELAY_PRODUCER_PORT_PROP, command.relay_prod_port)
    device.set_prop(TRACED_ENABLE_PROP, "1")
  else:  #disable
    device.set_prop(TRACED_ENABLE_PROP, "0")
    device.clear_prop(TRACED_RELAY_PRODUCER_PORT_PROP)
    device.set_prop(TRACED_ENABLE_PROP, "1")
  return None


def execute_vm_command(args, device):
  command = create_vm_command(args)
  error = device.check_device_connection()
  if error is not None:
    return error
  device.root_device()
  if command.type == 'traced-relay':
    return traced_relay_execute(command, device)
  # else it's a relay-producer command
  return relay_producer_execute(command, device)


class VmCommand(Command):
  """
  Represents commands which configure perfetto
  in virtualized Android.
  """

  def __init__(self, type, subcommand, relay_port, relay_prod_port):
    super().__init__(type)
    self.subcommand = subcommand
    self.relay_port = relay_port
    self.relay_prod_port = relay_prod_port

  def validate(self, device):
    raise NotImplementedError
