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
  termios.tcsetattr(fd, termios.TCSANOW, attrs)


def tty_read(fd, output, timeout=0.1):
  """Reads data from the TTY device and appends it to the output bytearray."""
  r, _, _ = select.select([fd], [], [], timeout)
  if fd in r:
    try:
      chunk = os.read(fd, 4096)
      if chunk:
        output.extend(chunk)
    except BlockingIOError:
      pass


def tty_write(fd, data):
  """Writes data to the TTY device and waits for it to be transmitted."""
  if isinstance(data, str):
    data = data.encode('utf-8')
  os.write(fd, data)
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
    if output.endswith(prompt):
      return len(output) - len(prompt)

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
      help="Timeout in seconds to wait for output (0 = wait forever, default: 0.0)"
  )

  args = parser.parse_args()

  with tty_open(args.device) as fd:
    tty_setup(fd, args.baud)

    # Define signal handler for Ctrl-C
    signal.signal(signal.SIGINT, sigint_handler(fd))

    # Clear buffer before sending
    termios.tcflush(fd, termios.TCIOFLUSH)

    # Write command
    tty_write(fd, args.command + '\n')

    output = bytearray()
    start_time = time.time()
    printed_upto = 0

    # Wait for the command to finish
    while True:
      tty_read(fd, output)

      prompt_idx = find_shell_prompt_idx(output)

      if prompt_idx != -1:  # Found shell prompt!
        to_print = output[printed_upto:prompt_idx]
        if to_print:
          print(to_print.decode('utf-8', errors='replace'), end='', flush=True)
        break
      else:
        # No prompt yet. Print what is safe (keep last 2 bytes).
        safe_idx = max(0, len(output) - 2)
        to_print = output[printed_upto:safe_idx]
        if to_print:
          print(to_print.decode('utf-8', errors='replace'), end='', flush=True)
          printed_upto += len(to_print)

      if args.timeout > 0 and (time.time() - start_time) > args.timeout:
        print(
            f"\nError: Command timed out after {args.timeout} seconds.",
            file=sys.stderr)
        tty_write(fd, CTRL_C)
        args.timeout = 0  # To avoid sending CTRL_C continously

    # Get the exit code
    tty_write(fd, b"echo $?\n")
    output = bytearray()  # Reset output to capture only the exit code

    while True:
      tty_read(fd, output)

      if b'\n' in output or b'\r' in output:
        decoded_output = output.decode('utf-8', errors='replace').strip()
        # The output might contain the echoed "echo $?" command, so we find the last line
        lines = decoded_output.splitlines()
        for line in reversed(lines):
          line = line.strip()
          if line.isdigit():
            sys.exit(int(line))


if __name__ == "__main__":
  main()
