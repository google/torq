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

from .base import Command, ValidationError
from .device import AdbDevice
from .utils import are_mutually_exclusive, extract_port, UniqueStore

DEFAULT_COMMS_PORT = "30001"
DEFAULT_IP_ADDR = "0.0.0.0:" + DEFAULT_COMMS_PORT
DEFAULT_VSOCK_ADDR = "vsock://-1:" + DEFAULT_COMMS_PORT
TRACED_ENABLE_PROP = "persist.traced.enable"
TRACED_MACHINE_NAME_PROP = "traced.machine_name"
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
      default=DEFAULT_VSOCK_ADDR,
      help='Socket address used for relayed communication.')

  relay_producer_subparsers.add_parser(
      'disable', help=('Disable traced\'s relay producer port'))

  # Configure subcommand
  configure_parser = vm_subparsers.add_parser(
      'configure', help=('Configure all VMs'))

  configure_parser.add_argument(
      '-p',
      '--primary',
      action=UniqueStore,
      help='Primary machine. Accepts the following formats: '
      '<android-serial> or '
      '<perfetto-machine-name>=<android-serial>. '
      'Where <perfetto-machine-name> is an arbitrary name used to '
      'specify a particular machine in Perfetto config\'s machine name'
      ' filter.')

  configure_parser.add_argument(
      '--primary-cid',
      action=UniqueStore,
      type=int,
      help='The VSOCK CID of the primary machine.'
      f'The default port used is {DEFAULT_COMMS_PORT}.')

  configure_parser.add_argument(
      '--primary-ip',
      action=UniqueStore,
      help='The IP address (port excluded) of the primary machine.'
      f'The default port used is {DEFAULT_COMMS_PORT}.')

  configure_parser.add_argument(
      '--primary-addr',
      action=UniqueStore,
      help='Custom network address, including the port, of the primary machine.'
      'Only VSOCK or IP addresses are supported.')

  configure_parser.add_argument(
      '-s',
      '--secondary',
      action='append',
      default=[],
      help='Secondary machine. Follows the same format as --primary.')


def name_format_error(value):
  alt_value = '='.join(value.split('=')[:2])
  return ValidationError(
      ("Invalid format used in either --primary or --secondary argument: "
       f"'{value}'"), (f"The correct format is one of:\n\t"
                       "  - <device-serial>\n\t"
                       "  - <perfetto-machine-name>=<device-serial>\n\n"
                       f"\tDid you meant to use '{alt_value}'?\n"))


def is_name_format_valid(value):
  splits = len(value.split('='))
  return splits == 1 or splits == 2


def verify_vm_args(args):
  if args.vm_subcommand != "configure":
    return args, None

  if args.primary is not None and not is_name_format_valid(args.primary):
    return None, name_format_error(args.primary)

  for secondary in args.secondary:
    if not is_name_format_valid(secondary):
      return None, name_format_error(secondary)

  if not are_mutually_exclusive(args.primary_cid, args.primary_ip,
                                args.primary_addr):
    return None, ValidationError(
        "--primary-cid, --primary-ip and --primary-addr are mutually exclusive",
        "Please only use one of the flags.")

  if args.secondary and args.primary_cid is None and args.primary_ip is None \
     and args.primary_addr is None:
    return None, ValidationError((
        "Unable to resolve the network address of the primary machine."
    ), ("Please provide the VSOCK CID of the primary machine via --primary-cid\n\t"
        "or the IP address of the primary machine via --primary-ip or a\n\t"
        "custom VSOCK or IP address via --primary-addr"))

  return args, None


def create_vm_command(args):
  match args.vm_subcommand:
    case 'configure':
      return VmCommand('configure', None, None, None)
    case 'relay-producer':
      relay_prod_port = None
      if args.vm_relay_producer_subcommand == 'enable':
        relay_prod_port = args.relay_prod_port
      return VmCommand('relay-producer', args.vm_relay_producer_subcommand,
                       None, relay_prod_port)
    case 'traced-relay':
      relay_port = None
      if args.vm_traced_relay_subcommand == 'enable':
        relay_port = args.relay_port

      return VmCommand('traced-relay', args.vm_traced_relay_subcommand,
                       relay_port, None)
    case _:
      raise ValueError("Invalid vm subcommand was used.")


def get_name_and_serial(flag_value):
  names = flag_value.split('=')
  if len(names) == 1:
    return (None, names[0])
  return (names[0], names[1])


def configure_execute(args):
  if args.primary_cid:
    net_addr = f'vsock://{args.primary_cid}:{DEFAULT_COMMS_PORT}'
  elif args.primary_ip:
    net_addr = f'{args.primary_ip}:{DEFAULT_COMMS_PORT}'
  elif args.primary_addr:
    net_addr = args.primary_addr
  else:  # This case only happens when only setting --primary
    net_addr = DEFAULT_VSOCK_ADDR

  if args.primary:
    machine_name, serial = get_name_and_serial(args.primary)
    primary_device = AdbDevice(serial)
    if (error := primary_device.check_device_connection()) is not None:
      return error
    primary_device.root_device()
    relay_prod_port = DEFAULT_VSOCK_ADDR if "vsock" in net_addr else DEFAULT_IP_ADDR
    if args.primary_addr:
      relay_prod_port = relay_prod_port.replace(DEFAULT_COMMS_PORT,
                                                extract_port(net_addr))
    command = VmCommand('relay-producer', 'enable', None, relay_prod_port)
    if (error := relay_producer_execute(command, primary_device, machine_name)):
      return error

  for secondary in args.secondary:
    machine_name, serial = get_name_and_serial(secondary)
    secondary_device = AdbDevice(serial)
    if (error := secondary_device.check_device_connection()) is not None:
      return error
    secondary_device.root_device()
    if machine_name is not None:
      secondary_device.set_prop(TRACED_MACHINE_NAME_PROP, machine_name)
    command = VmCommand('traced-relay', 'enable', net_addr, None)
    if (error := traced_relay_execute(command, secondary_device)):
      return error
  return None


def traced_relay_execute(command, device):
  if command.subcommand == 'enable':
    if len(device.get_prop(TRACED_HYPERVISOR_PROP)) == 0:
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


def relay_producer_execute(command, device, machine_name=None):
  device.set_prop(TRACED_ENABLE_PROP, "0")

  if command.subcommand == 'enable':
    if machine_name is not None:
      device.set_prop(TRACED_MACHINE_NAME_PROP, machine_name)
    device.set_prop(TRACED_RELAY_PRODUCER_PORT_PROP, command.relay_prod_port)
  else:  #disable
    device.clear_prop(TRACED_RELAY_PRODUCER_PORT_PROP)

  device.set_prop(TRACED_ENABLE_PROP, "1")
  return None


def execute_vm_command(args, device):
  command = create_vm_command(args)
  if command.type != 'configure':
    error = device.check_device_connection()
    if error is not None:
      return error
    device.root_device()
  match command.type:
    case 'configure':
      return configure_execute(args)
    case 'relay-producer':
      return relay_producer_execute(command, device)
    case 'traced-relay':
      return traced_relay_execute(command, device)
    case _:
      raise ValueError("Invalid vm subcommand was used.")


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
