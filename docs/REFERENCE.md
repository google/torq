# Torq CLI Reference

This document provides a comprehensive reference for the `torq` command-line interface (CLI). Torq is a CLI tool designed for performance testing and trace collection on Android Automotive devices. 

It provides various subcommands to configure Perfetto, trace specific events, interact with virtualized environments, and view captured traces.

## Global Options

These options can be provided for the main `torq` command before specifying a subcommand.

| Argument | Description | Default |
|----------|-------------|---------|
| `--serial` | Specifies the serial of the connected device that will be used for the operation. Supports Android serials and SSH URIs (e.g. ssh://user@host). If not provided, the `ANDROID_SERIAL` environment variable is used. If `ANDROID_SERIAL` is also not set and there is only one device connected, that device is automatically chosen. | |

---

## Subcommand: `profiler`

The `profiler` subcommand is used to trace and profile Android devices. It is the default subcommand when no subcommand is provided.

| Argument | Description | Currently Supported Arguments | Default |
|----------|-------------|-------------------------------|---------|
| `-e, --event` | The event to trace/profile. | `boot`, `user-switch`, `app-startup`, `custom` | `custom` |
| `-p, --profiler` | The performance data source/profiler to use. | `perfetto`, `simpleperf` | `perfetto` |
| `-o, --out-dir` | The path to the output directory where trace files will be saved. | Any local path | `.` (Current directory) |
| `-d, --dur-ms` | The duration (in milliseconds) of the event. Determines when to stop collecting performance data. | Integer >= 3000 | Indefinite until CTRL+C |
| `-a, --app` | The package name of the app to start. (Requires `-e app-startup`) | Any installed package | |
| `-r, --runs` | The number of times to run the event and capture the perf data. | Integer >= 1 | `1` |
| `-s, --simpleperf-event` | Simpleperf supported events to be collected. Can be defined multiple times. (Requires `-p simpleperf`). | e.g. `cpu-cycles`, `instructions` | `cpu-clock` |
| `--perfetto-config` | Predefined Perfetto configs or a filepath with a custom config. | `default`, `lightweight`, `memory`, `qnx`, `android-qnx`, or `<filepath>` | `default` |
| `--between-dur-ms` | Time (ms) to wait before executing the next event run. (Requires `--runs` > 1) | Integer >= 3000 | `10000` |
| `--ui`, `--no-ui` | Specifies whether to open the UI visualization tool (Perfetto UI) after profiling is complete. | `--ui`, `--no-ui` | `--ui` if runs=1 |
| `--excluded-ftrace-events`| Excludes specified ftrace event from the Perfetto config events. Can be defined multiple times. | Any supported ftrace event | |
| `--included-ftrace-events`| Includes specified ftrace event in the Perfetto config events. Can be defined multiple times. | Any supported ftrace event | |
| `--from-user` | The user ID from which to start the user switch. (Requires `-e user-switch`) | Valid User ID | Current User |
| `--to-user` | The user ID of user that the system is switching to. (Requires `-e user-switch`) | Valid User ID | |
| `--symbols` | Specifies the path to the symbols library. (Requires `-p simpleperf`) | Path to symbols | |
| `--trigger-names` | Specifies the names of triggers for Perfetto background tracing. Adds multiple trigger names. | `<name1> ... <nameN>` | |
| `--trigger-timeout-ms` | Specifies the time in milliseconds for Perfetto to wait for a trigger before ending. | Integer | 604800000 (1 week) |
| `--trigger-stop-delay-ms`| Specifies the time in ms to extend trace collection past a trigger event. If multiple triggers are present, you can include a different delay for each or one for them all. | `<delay1> ... <delayN>` | 1000 |
| `--trigger-mode` | Specifies the trigger config mode. `stop` ends tracing after a trigger + delay. `start` begins tracing when a trigger is received and ends after delay. `clone` traces until timeout, returning tracing data every time a trigger is received. | `stop`, `start`, `clone`, `STOP_TRACING`, `START_TRACING`, `CLONE_SNAPSHOT` | `STOP_TRACING` |

---

## Subcommand: `config`

The `config` subcommand is used to list, show, and download predefined Perfetto configs.

### `config list`
Lists all the predefined Perfetto configs available.

### `config show`
Prints the contents of the predefined Perfetto config in the terminal. 

**Usage:** `torq config show <config-name> [options]`

| Argument | Description | Currently Supported Arguments |
|----------|-------------|-------------------------------|
| `<config-name>` | Name of the predefined config to show. | `lightweight`, `default`, `memory`, `qnx`, `android-qnx` |

**Note:** `config show` also supports the following arguments to override configuration fields:
`-d, --dur-ms`, `--excluded-ftrace-events`, `--included-ftrace-events`, `--trigger-names`, `--trigger-timeout-ms`, `--trigger-stop-delay-ms`, `--trigger-mode`.

### `config pull`
Copies a predefined config to the specified file path.

**Usage:** `torq config pull <config-name> [file_path] [options]`

| Argument | Description | Currently Supported Arguments | Default |
|----------|-------------|-------------------------------|---------|
| `<config-name>` | Name of the predefined config to copy. | `lightweight`, `default`, `memory`, `qnx`, `android-qnx` | |
| `[file_path]` | File path to copy the predefined config to. | Any valid path | `./<config-name>.txtpb` |

**Note:** `config pull` also supports the following arguments to override configuration fields:
`-d, --dur-ms`, `--excluded-ftrace-events`, `--included-ftrace-events`, `--trigger-names`, `--trigger-timeout-ms`, `--trigger-stop-delay-ms`, `--trigger-mode`.

---

## Subcommand: `open`

The `open` subcommand is used to open trace files in the Perfetto UI.

**Usage:** `torq open <file_path> [--use_trace_processor]`

| Argument | Description | Default |
|----------|-------------|---------|
| `<file_path>` | Path to the trace file to open. | |
| `--use_trace_processor` | Enables using `trace_processor` to open the trace regardless of its size. | Disabled |

---

## Subcommand: `trigger`

The `trigger` subcommand is used to trigger trace collection from Perfetto when a trigger is included in the trace config.

**Usage:** `torq trigger <trigger_name>`

| Argument | Description |
|----------|-------------|
| `<trigger_name>` | The name of the trigger to send via the `trigger_perfetto` binary. |

---

## Subcommand: `vm`

The `vm` subcommand is used to configure Perfetto in virtualized Android and multi-VM environments. It provides ways to set up `traced` and `traced_relay`.

### `vm traced-relay`
Configures the `traced_relay` component.

| Command | Argument | Description |
|---------|----------|-------------|
| `enable`| `<relay_port>` | Enables `traced_relay` and uses the provided socket address to communicate with `traced`. |
| `disable`| | Disables `traced_relay`. |

### `vm relay-producer`
Configures `traced`'s relay producer socket.

| Command | Argument | Description | Default |
|---------|----------|-------------|---------|
| `enable`| `--address <relay_prod_port>` | Enables `traced`'s relay producer port using the specified socket address for relayed communication. | `vsock://-1:30001` |
| `disable`| | Disables `traced`'s relay producer port. | |

### `vm configure`
Configures the primary VM and secondary VMs for capturing unified traces.

| Argument | Description |
|----------|-------------|
| `-p, --primary` | Primary machine. Accepts the formats: `<device-serial-or-uri>` or `<perfetto-machine-name>=<device-serial-or-uri>`. Where `<device-serial-or-uri>` is an Android serial or an SSH URI (e.g. ssh://user@host), and `<perfetto-machine-name>` is an arbitrary name used to specify a particular machine in Perfetto config's machine name filter. |
| `--primary-cid` | The VSOCK CID of the primary machine. The default port used is 30001. |
| `--primary-ip` | The IP address (port excluded) of the primary machine. The default port used is 30001. |
| `--primary-addr`| Custom network address, including the port, of the primary machine. Only VSOCK or IP addresses are supported. |
| `-s, --secondary` | Secondary machine. Follows the same format as `--primary`. Can be specified multiple times. |
