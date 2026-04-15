# torq: AAOS Performance CLI

**torq** is a command-line tool designed to streamline and standardize OS
performance profiling across Android Automotive devices. By providing a flexible
and easy-to-use interface, **torq** enables engineers and OEMs to capture and
analyze performance data for critical system events such as boot, user switch,
app startup, or any of their own interactions with their device. This tool helps
ensure consistent results amongst different users and helps reduce the time and
effort required for performance analysis, ensuring that developers can focus on
optimizing their systems and bug detection rather than navigating fragmented
tooling solutions.


## Getting Started

To start using **torq** follow these steps:

- Go to *torq*'s directory and build it:

```bash
bazel build //:torq
export PATH="$(pwd)/bazel-bin:$PATH"
```

- Connect to an Android device or start an emulator.
- Ensure the connected device appears in `adb devices`.
- Capture a perfetto trace using *torq*:

```bash
torq -d 7000
```

## Building Torq

**torq** uses [Bazel](https://bazel.build) as its build system.

To build and use torq using [Bazel](https://bazel.build/), run:
```bash
bazel build //:torq
./bazel-bin/torq --help
```

## Quick one-line commands

**torq**'s main goal is to allow developers to quickly trace and profile Android
in the least amount of steps while being flexible enough to cover many different
use cases. This list of commands demonstrates just that.

| Command | Description  |
|----------|-------------|
| `torq -d 7000` | Run a custom event for 7 seconds. |
| `torq -e user-switch --from-user 10 --to-user 11` | Run a user-switch event, switching from user 10 to user 11. |
| `torq -e boot --perfetto-config ./config` | Run a boot event, using the user's local Perfetto config specified in the ./config file path. |
| `torq -e boot -r 5 --between-dur-ms 3000` | Run a boot event 5 times, waiting 3 seconds between each boot run. |
| `torq -e app-startup -a android.google.kitchensink` | Run an app-startup event, starting the android.google.kitchensink package. |
| `torq -e user-switch --to-user 9 --serial emulator-5554` | Run a user-switch event, switching to user 9 on the connected device with serial, emulator-5554. |
| `torq -p simpleperf -d 10000` | Run a custom event using the Simpleperf profiler for 10 seconds. |
| `torq -p simpleperf -s cpu-cycles -s instructions` | Run a custom event using the Simpleperf profiler, in which the stats, cpu-cycles and instructions, are collected. |
| `torq -d 10000 --perfetto-config lightweight` | Run a custom event for 10 seconds using the "lightweight" predefined Perfetto config. |
| `torq config show memory` | Print the contents of the memory predefined Perfetto config to the terminal. |
| `torq open trace.perfetto-trace` | Open a trace in the perfetto UI. |
| `torq -d 10000 --exclude-ftrace-event power/cpu_idle` | Run a custom event for 10 seconds, using the "default" predefined Perfetto config, in which the ftrace event, power/cpu_idle, is not collected. |

## CLI Reference

For a complete list of all the `torq` subcommands and flags, please refer to the [CLI Reference](docs/REFERENCE.md).

## Configure perfetto in virtualized Android

Working on a multi-VM environments has its challenges. In order to obtain a unified trace
containing the trace data from multiple VMs you could leverage Perfetto's *traced* and *traced_relay*
binaries. Torq provides commands to greatly simplify the configuration process.

For example, to switch a VM from using `traced` to `traced_relay`, you could run:
```console
torq vm traced-relay enable vsock://3:30001
```
To enable the relay producer port in `traced`, you could run:
```console
torq vm relay-producer enable
```

### CLI Arguments

For a complete list of arguments for the `torq vm` subcommand, please refer to the [CLI Reference](docs/REFERENCE.md#subcommand-vm).

## Configure trigger configs for perfetto

When you want to get traces in response to specific code paths, Perfetto's
trigger configs can collect traces when specific triggers are received via the
trigger_perfetto binary. Torq provides commands to add Perfetto triggers to your
trace configs as well as to call the trigger_perfetto binary.

To add a trigger to your config, you could run:
```console
torq --trigger-names trigger1
```

To add a trigger to your config that traces for 10 seconds after the trigger is
received, you could run:
```console
torq --trigger-names trigger1 --trigger-stop-delay-ms 10000
```

To trigger a trace collection, you could run:
```console
torq trigger <trigger-name>
```

### CLI Arguments

For a complete list of arguments for the `torq trigger` subcommand, please refer to the [CLI Reference](docs/REFERENCE.md#subcommand-trigger).

## Activate Perfetto triggers

When you want to get traces in response to specific code paths, Perfetto's
trigger configs can collect traces when specific triggers are received via the
trigger_perfetto binary. Torq provides a subcommand to trigger trace collection
for a trigger included in a Perfetto config.

### CLI Arguments

For a complete list of arguments for the `torq trigger` subcommand, please refer to the [CLI Reference](docs/REFERENCE.md#subcommand-trigger).

## Testing Torq

For a detailed guide on test setup, VM requirements, and troubleshooting, please refer to the [Torq Testing Doc](docs/TORQ_TESTING.md)

## Contributing to Torq

Before starting development in **torq**'s codebase, run:
```bash
./tools/build_deps
```

Also, before submitting code remember to format the code. Run:
```bash
./tools/format_sources
```
