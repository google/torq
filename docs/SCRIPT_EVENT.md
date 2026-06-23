# Host-Side Script Execution during Tracing

You can execute a host-side script while a trace is being captured on the target device by using the `--script` flag with the `custom` event. This is useful for profiling specific critical user journeys (CUJs), automated UI tests, or any command-line operations where you want the trace duration to match the execution of the script.

When using a script, Torq will start the profiler (Perfetto or Simpleperf) on the device, wait for it to initialize, run your host-side script, and immediately stop the profiler once your script finishes.

Since `custom` is the default event type in Torq, you can omit `-e custom` when using `--script`.

## Usage

You can specify the script in three ways:

### 1. Inline Command String
Pass a simple command directly as a string to the `--script` argument:

```bash
torq --serial <device-serial> --script "sleep 10"
```

### 2. Script File
Pass the path to an existing executable script file to the `--script` argument. Torq automatically resolves relative paths to absolute paths to ensure the script can be found during execution:

```bash
torq --serial <device-serial> --script path/to/cuj.sh
```

If the script file is not executable, Torq will fail with a permission error and suggest making it executable using `chmod +x`.

### 3. Inline Script via Stdin / Pipes
Omit the value for `--script` and pipe or redirect the script content into Torq's stdin.

Using a redirect (Heredoc):
```bash
torq --serial <device-serial> --script <<EOF
echo "Running test commands..."
sleep 5
EOF
```

Using a pipe:
```bash
cat cuj.sh | torq --serial <device-serial> --script
```

## Behavior Details

### Target Device Environment
When executing the host-side script, Torq injects the target device serial into the `ANDROID_SERIAL` environment variable. This allows any `adb` commands inside your script to automatically target the correct device without needing to specify the `-s` flag repeatedly.

### Trace Duration
Unlike other event types where you must specify a duration using `-d`/`--dur-ms`, the trace duration when running a script is dynamically controlled by the execution time of the script. Torq will stop the trace immediately after the script exits.
