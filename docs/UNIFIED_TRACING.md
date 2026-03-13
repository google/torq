# Unified Tracing with Torq

Unified tracing allows you to capture a single, synchronized trace across multiple virtual machines (VMs) or devices, such as Android and QNX running simultaneously. This is critical for understanding cross-OS interactions and full-system performance. 

Torq simplifies the setup of Perfetto's unified tracing architecture by automating the configuration of `traced` (the central tracing daemon) and `traced_relay` (the daemon that forwards traces from guest VMs to the host VM).

## Architecture Overview

Perfetto supports a central daemon (`traced`) that collects traces, and a relay daemon (`traced_relay`) that can run on other machines/VMs to forward trace data to the central daemon over a socket.

In a typical setup involving Android and QNX:
1. **Primary Machine:** The central VM running `traced`. It opens a "relay producer port" to listen for incoming connections from `traced_relay` instances. 
2. **Secondary Machines:** The guest VMs (like QNX or secondary Android instances) running `traced_relay`. They connect to the primary machine's socket to forward their trace data.

To capture a unified trace, the primary machine must use a Perfetto configuration that includes data sources for all the VMs and explicitly sets `trace_all_machines: true`.

## Configuring VMs with Torq

The `torq vm configure` command automates the entire setup of `traced` and `traced_relay` across multiple devices. 

It takes a `--primary` device and one or more `--secondary` devices. Devices can be specified using Android serials (e.g. `emulator-5554`) or SSH URIs (e.g. `ssh://root@172.12.345.678`).

### 1. Identify Network Address
The secondary machines need to know how to reach the primary machine. You must provide the network address of the primary machine using one of the following flags:
* `--primary-cid <cid>`: The VSOCK Context ID of the primary machine (commonly used in Android virtualization). Default port is `30001`.
* `--primary-ip <ip>`: The IP address of the primary machine. Default port is `30001`.
* `--primary-addr <address>`: A custom network address, including the port (e.g., `vsock://-1:30001` or `10.0.2.2:4000`).

### 2. Machine Names (Optional but Recommended)
To distinguish between different machines in the Perfetto UI, you can assign a machine name to each device by prefixing the serial/URI with `<name>=`. If omitted, Perfetto will just show trace data without a specific machine identifier grouping.

### Example: Android (Primary) and QNX (Secondary)

Assume you have an Android device connected via adb (`emulator-5554`) and a QNX device accessible via SSH (`ssh://root@192.168.1.100`). The Android device is accessible via an IP address of `192.168.1.50`.

```bash
torq vm configure \
  --primary-ip 192.168.1.50 \
  --primary android=emulator-5554 \
  --secondary qnx=ssh://root@192.168.1.100
```

**What this command does:**
1. Connects to `emulator-5554` (Android) and enables its `traced` relay producer port on `192.168.1.50:30001`. It assigns the machine name `android`.
2. Connects to `ssh://root@192.168.1.100` (QNX) and starts `traced_relay`, configuring it to forward data to `192.168.1.50:30001`. It assigns the machine name `qnx` (if supported).

## Capturing a Unified Trace

Once the VMs are configured, you can capture a trace from the primary machine. You need to use a config that collects data from all machines.

Torq provides a predefined config named `android-qnx` specifically for this use case. It merges the default Android data sources with QNX data sources (`qnx.kernel`) and enables `trace_all_machines: true`.

```bash
torq --serial emulator-5554 --perfetto-config android-qnx -d 10000
```

**What this command does:**
1. Connects to the primary device (`emulator-5554`).
2. Starts tracing using the `android-qnx` predefined configuration for 10 seconds.
3. Because `trace_all_machines: true` is set, the primary `traced` daemon will also instruct all connected `traced_relay` instances (like your QNX device) to start collecting their respective data sources.
4. Pulls the unified trace file to your host machine and opens it in the Perfetto UI.

## Troubleshooting and Manual Configuration

If you need to manually configure the relay producer or traced_relay, Torq provides explicit subcommands.

### Enable Relay Producer (Primary)
```bash
# Enable on a specific device
torq --serial emulator-5554 vm relay-producer enable --address vsock://-1:30001

# Disable
torq --serial emulator-5554 vm relay-producer disable
```

### Enable Traced Relay (Secondary)
```bash
# Enable on a QNX device
torq --serial ssh://root@192.168.1.100 vm traced-relay enable 192.168.1.50:30001

# Disable
torq --serial ssh://root@192.168.1.100 vm traced-relay disable
```
