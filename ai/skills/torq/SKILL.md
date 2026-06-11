---
name: torq
description: Capture a perfetto or simpleperf trace using the Torq CLI.
---

# Torq Skill

This skill allows capturing performance traces using the Torq CLI tool.

## Prerequisites

- Ensure you have a device connected and authorized via ADB.
- Ensure that the torq CLI is available (e.g `which torq`).

## 1. Capturing a Trace

You can capture either a Perfetto trace (default) or a Simpleperf trace. This is specified via the
`-p`/`--profiler` flag. By default perfetto is selected and the `-p` flag doesn't need to be specified.

The next step is to specify the trace duration, which needs to be expressed in milliseconds, via the
`-d`/`--duration` flag. Setting an explicit duration is optional. If no `--duration` flag is passed, 
then the trace will continue indefinitely until `Ctrl+C` is pressed to stop the trace collection.

> [!Note]
> In the case that Ctrl+C doesn't kill the torq process (might be running in the background), then
> you can run `ps aux | grep torq` to get the PID for the torq process and send a SIGINT to it.

By default the trace files are opened in the browser, given it is almost always the desired behavior.
In the case you don't want the files to be opened in the browser, you can specify `--no-ui` to skip
this.

> [!Note]
> But always prefer to launch the trace files in the browser, only use `--no-ui` if it
> is intentionally mentioned.

The trace files will be saved in the current directory (or the directory specified by
`-o`/`--out-dir` flag) with a default prefix (e.g., `trace-...`).

Here are some examples of how to capture traces with torq:

```bash
# Capture a Perfetto trace for 20 seconds
torq -d 20000

# Run an indefinite trace (make sure to press Ctrl+C to cancel trace session)
torq

# Skip opening the trace in the browser
torq -d 20000 --no-ui

# Capture a simpleperf profile for 10 seconds
torq -p simpleperf -d 10000

# Store trace in /tmp/perfetto-traces
torq -d 5000 -o /tmp/perfetto-traces
```

### Trigger System Events

With torq it is possible to trigger different system events while capturing a trace. One can specify
the event via the `-e`/`--event` flag. You can see the supported events via `torq profiler --help`
command.

Here are some examples on how to do this:

```bash
# Capture a boottime trace
torq -d 60000 -e boot

# Capture a user switch trace
torq -d 10000 -e user-switch --from-user 11 --to-user 12

# Capture an app startup in the trace
torq -d 4000 -e app-startup -a com.google.android.apps.maps
```

### Help

To better understand all the alternatives of the `profiler` subcommand in torq, you can always
run:

```bash
torq profiler --help
```
