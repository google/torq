# torq-serial

`torq-serial` is a specialized serial port communication utility designed to execute commands on remote devices via TTY interfaces. Its primary purpose is to provide the serial communication backbone for the `torq` CLI, enabling it to interact with devices that lack standard networking or ADB access.

Unlike simple terminal emulators, it behaves more like a remote shell executor (similar to `ssh` or `adb shell`), providing real-time output streaming and reliable exit code propagation.

## Features

- **Automated Execution:** Sends a command and waits for completion by detecting standard shell prompts (`$` or `#`).
- **Exit Code Propagation:** Automatically fetches and returns the remote command's exit code as its own.
- **SIGINT Forwarding:** Pressing `Ctrl-C` locally sends a `CTRL_C` (`\x03`) signal to the remote device, allowing for graceful interruption of remote processes.
- **Timeout Support:** Supports execution timeouts, sending a remote interrupt if the command exceeds the specified duration.
- **Clean Output:** Suppresses internal communication (like exit code fetching) to provide a clean output stream.
- **Debugging Support:** Supports dumping raw TTY traffic to a file for troubleshooting.

## Build

You can build `torq-serial` using Bazel from the root of the workspace:

```bash
bazel build //:torq-serial
```

This will generate an executable binary at `./bazel-bin/torq-serial`.

## Usage

After building, you can run the `torq-serial` executable directly:

```bash
torq-serial -d <device> -c "<command>" [options]
```

### Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `-d`, `--device` | **Required.** The serial device path (e.g., `/dev/ttyUSB0`). | N/A |
| `-c`, `--command` | **Required.** The command string to execute on the remote device. | N/A |
| `-b`, `--baud` | Baud rate. Choices: `9600`, `19200`, `38400`, `57600`, `115200`. | `115200` |
| `-t`, `--timeout` | Timeout in seconds. `0.0` means wait forever. | `0.0` |
| `--dump` | Filepath to dump raw TTY traffic (appends if file exists). | N/A |

## Examples

**Run a simple command:**
```bash
torq-serial -d /dev/ttyUSB1 -c "ls -l /etc"
```

**Run a long command with a timeout:**
```bash
torq-serial -d /dev/ttyUSB1 -c "sleep 60" -t 10
```

**Check the exit code of a failed command:**
```bash
torq-serial -d /dev/ttyUSB1 -c "non_existent_command"
echo $?
```

**Debug communication by dumping raw traffic:**
```bash
torq-serial -d /dev/ttyUSB1 -c "ls /" --dump /tmp/serial_debug.txt
cat /tmp/serial_debug.txt
```
