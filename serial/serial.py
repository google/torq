#
# Copyright (C) 2026 The Android Open Source Project
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
import sys
import time
import termios
import argparse
import select
import signal
from contextlib import contextmanager

BAUD_MAP = {
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
    57600: termios.B57600,
    115200: termios.B115200,
}
CTRL_C = b'\x03'
SHELL_PROMPTS = [b'$ ', b'# ']


def create_dumper(filepath, command):
  """Setup a dump file and return a logging function and a close function."""
  dump_file = None

  def dump_log(data):
    nonlocal filepath
    if not filepath:
      return
    if isinstance(data, str):
      data = data.encode('utf-8')
    nonlocal dump_file
    dump_file.write(data)
    dump_file.flush()

  def close_dumper():
    nonlocal filepath
    if not filepath:
      return
    dump_log(f"\n--- END COMMAND: {command} ---\n")
    nonlocal dump_file
    dump_file.close()

  if not filepath:
    return dump_log, close_dumper

  try:
    dump_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dump_dir, exist_ok=True)
    dump_file = open(filepath, 'ab')
  except Exception as e:
    raise ValueError(f"Failed to create dump file at {filepath}: {e}")

  dump_file.write(f"--- COMMAND: {command} ---\n".encode('utf-8'))
  dump_file.flush()

  return dump_log, close_dumper


@contextmanager
def tty_open(device):
  """Context manager to open and close a TTY device."""
  try:
    # Open device in read-write, non-blocking mode
    fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
  except Exception as e:
    print(f"Error opening {device}: {e}")
    sys.exit(1)

  try:
    yield fd
  finally:
    os.close(fd)


def tty_setup(fd, baudrate=115200):
  # attrs is a list: [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
  attrs = termios.tcgetattr(fd)

  # Set raw mode
  attrs[0] &= ~(
      termios.IGNBRK | termios.BRKINT | termios.PARMRK | termios.ISTRIP
      | termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IXON)
  attrs[1] &= ~termios.OPOST
  attrs[2] &= ~(termios.CSIZE | termios.PARENB)
  attrs[2] |= (termios.CS8 | termios.CREAD | termios.CLOCAL)
  attrs[3] &= ~(
      termios.ECHO | termios.ECHONL | termios.ICANON | termios.ISIG
      | termios.IEXTEN)

  # Set baud
  target_baud = BAUD_MAP.get(baudrate, termios.B115200)
  attrs[4] = target_baud
  attrs[5] = target_baud

  # VMIN and VTIME
  attrs[6][termios.VMIN] = 0
  attrs[6][termios.VTIME] = 0

  # Set attributes
  termios.tcsetattr(fd, termios.TCSADRAIN, attrs)


def tty_read(fd, output, dump_log=lambda x: None):
  """Reads data from the TTY device and appends it to the output bytearray."""
  r, _, _ = select.select([fd], [], [], 0.1)
  if fd in r:
    try:
      chunk = os.read(fd, 4096)
      if not chunk:
        print("\nError: TTY device disconnected (EOF).", file=sys.stderr)
        sys.exit(1)
      if chunk:
        output.extend(chunk)
        dump_log(chunk)
    except BlockingIOError:
      pass
    except OSError as e:
      print(f"\nError reading from TTY device: {e}", file=sys.stderr)
      sys.exit(1)


def tty_write(fd, data):
  """Writes data to the TTY device and waits for it to be transmitted."""
  if isinstance(data, str):
    data = data.encode('utf-8')

  written = 0
  while written < len(data):
    try:
      written += os.write(fd, data[written:])
    except BlockingIOError:
      # Wait a tiny bit for the output buffer to drain
      select.select([], [fd], [], 0.01)

  termios.tcdrain(fd)


def sigint_handler(fd):

  def signal_handler(sig, frame):
    # Send Ctrl-C to the remote device
    tty_write(fd, CTRL_C)
    # By not exiting here, the main loop will continue to wait for the
    # shell prompt and fetch the actual remote exit code.

  return signal_handler


def find_shell_prompt_idx(output):
  """Finds the index of a shell prompt in the output, or -1 if not found."""
  for prompt in SHELL_PROMPTS:
    idx = output.find(b'\n' + prompt)
    if idx != -1:
      return idx + 1

    idx = output.find(b'\r' + prompt)
    if idx != -1:
      return idx + 1
  return -1


def main():
  parser = argparse.ArgumentParser(description="Serial command executor")
  parser.add_argument(
      "-c",
      "--command",
      required=True,
      help="Command to execute on the remote device")
  parser.add_argument(
      "-d",
      "--device",
      required=True,
      help="Serial device to use (e.g., /dev/ttyUSB1)")
  parser.add_argument(
      "-b",
      "--baud",
      type=int,
      default=115200,
      choices=list(BAUD_MAP.keys()),
      help="Baud rate (default: 115200)")
  parser.add_argument(
      "-t",
      "--timeout",
      type=float,
      default=0.0,
      help="Timeout in seconds to wait for output (0 = wait forever, default: 0)"
  )
  parser.add_argument(
      "--dump",
      type=str,
      help="Filepath to dump exactly the chunks being read. File will be created if it doesn't exist."
  )

  args = parser.parse_args()

  dump_log, close_dumper = create_dumper(args.dump, args.command)

  with tty_open(args.device) as fd:
    tty_setup(fd, args.baud)

    # Define signal handler for Ctrl-C
    signal.signal(signal.SIGINT, sigint_handler(fd))

    # Clear buffer before sending
    termios.tcdrain(fd)
    termios.tcflush(fd, termios.TCIOFLUSH)

    # Send a newline and wait for a prompt to clear any pending output or
    # messages from previous background processes. This is a hack to flush
    # any pending none relevant output from the TTY device (e.g terminated
    # process output).
    tty_write(fd, '\n')
    sync_output = bytearray()
    while find_shell_prompt_idx(sync_output) == -1:
      tty_read(fd, sync_output)

    # Write command
    tty_write(fd, args.command + '\n')

    # For multi-line commands, the shell echoes the first line, then uses
    # secondary prompts ('> ') for the rest. We only skip the first line's echo.
    first_line_cmd = args.command.splitlines()[0].encode('utf-8')

    output = bytearray()
    start_time = time.time()
    printed_upto = 0
    echo_skipped = False

    # Wait for the command to finish
    while True:
      if args.timeout > 0 and (time.time() - start_time) > args.timeout:
        print(
            f"\nError: Command timed out after {args.timeout} seconds.",
            file=sys.stderr)
        tty_write(fd, CTRL_C)
        args.timeout = 0  # To avoid sending CTRL_C continously

      tty_read(fd, output, dump_log)

      # Skip the TTY device echoing the first line of the command.
      if not echo_skipped:
        cmd_idx = output.find(first_line_cmd)
        if cmd_idx != -1:
          newline_idx = output.find(b'\n', cmd_idx + len(first_line_cmd))
          if newline_idx == -1:
            continue
          printed_upto = newline_idx + 1
          echo_skipped = True
        else:
          continue

      prompt_idx = find_shell_prompt_idx(output)

      if prompt_idx != -1:  # Found shell prompt!
        to_print = output[printed_upto:prompt_idx]
        if to_print:
          print(to_print.decode('utf-8', errors='replace'), end='', flush=True)
        break
      else:
        # No prompt yet. Print what is safe (keep last 2 bytes).
        safe_idx = max(printed_upto, len(output) - 2)
        to_print = output[printed_upto:safe_idx]
        if to_print:
          print(to_print.decode('utf-8', errors='replace'), end='', flush=True)
          printed_upto = safe_idx

    dump_log(f"\n  -- GET EXIT CODE --\n")

    # Get the exit code
    tty_write(fd, b"echo $?\n")
    output = bytearray()  # Reset output to capture only the exit code

    while True:
      tty_read(fd, output, dump_log)

      if b'\n' in output or b'\r' in output:
        decoded_output = output.decode('utf-8', errors='replace').strip()
        # The output might contain the echoed "echo $?" command, so we find the last line
        lines = decoded_output.splitlines()
        for line in reversed(lines):
          line = line.strip()
          if line.isdigit():
            close_dumper()
            sys.exit(int(line))


if __name__ == "__main__":
  main()
