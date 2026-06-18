# Host-Side Script Execution during Tracing (Script Event)

The `script` event type in Torq allows you to execute a host-side script while a trace is being captured on the target device. This is useful for profiling specific critical user journeys (CUJs), automated UI tests, or any command-line operations where you want the trace duration to match the execution of the script.

When using the `script` event, Torq will start the profiler (Perfetto or Simpleperf) on the device, wait for it to initialize, run your host-side script, and immediately stop the profiler once your script finishes.

## Usage

You can specify the script in three ways:

### 1. Inline Command String
Pass a simple command directly as a string to the `--script` argument:

```bash
torq --serial <device-serial> -e script --script "sleep 10"
```

### 2. Script File
Pass the path to an existing script file to the `--script` argument. Torq automatically resolves relative paths to absolute paths to ensure the script can be found during execution:

```bash
torq --serial <device-serial> -e script --script path/to/cuj.sh
```

### 3. Inline Script via Stdin (Heredoc)
Omit the `--script` argument and pipe/redirect the script content into Torq's stdin. This is useful for multi-line inline scripts. Note that the closing `EOF` must not have leading spaces:

```bash
torq --serial <device-serial> -e script <<EOF
echo "Running test commands..."
sleep 5
EOF
```

## Behavior Details

### Shebang Handling
For inline scripts and script files that lack a shebang (e.g., `#!/bin/sh` or `#!/bin/bash`), Torq will automatically execute them using `/bin/sh` to avoid "Exec format error" (`OSError: [Errno 8]`).

### Target Device Environment
When executing the host-side script, Torq injects the target device serial into the `ANDROID_SERIAL` environment variable. This allows any `adb` commands inside your script to automatically target the correct device without needing to specify the `-s` flag repeatedly.

### Trace Duration
Unlike other event types where you must specify a duration using `-d`/`--dur-ms`, the `script` event duration is dynamically controlled by the execution time of the script. Torq will stop the trace immediately after the script exits.
