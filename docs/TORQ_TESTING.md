# Testing Torq

This document provides detailed instructions on how to  set up and run tests for `torq`.

## Test Suites

Torq has three main categories of tests:
1. **Unit Tests:** Test individual components in isolation.
2. **Integration Tests:** Test android events functionality involving real or emulated Android device.
2. **Advanced Integration Tests:** Test unified end-to-end vm tracing involving 2 real or emulated Android devices.


The `tools/torq_test` script is the recommended entry point for running all tests.

---

## 1. Unit Tests

Unit tests do not require an Android device and are the fastest way to verify code changes.

### Running all unit tests:
```bash
./tools/torq_test --unit
```
(OR)
```bash
./tools/torq_test
```

### Running a specific unit test:
``` bash
./tools/torq_test --unit <test_name>
```
### Example:
``` bash
./tools/torq_test --unit torq_unit_test
```

## 2. Integration Tests
Integration tests require at least one (and sometimes two) active Android devices or Cuttlefish (CVD) instances.

### Prerequisites
ADB: Installed and available in your PATH.

Root Access: adbd must be running as root on the target device(s).

Environment: ANDROID_PRODUCT_OUT should be set if testing simpleperf or specific binary pushing.

One CVD Instances: Launch at least one Cuttlefish instance.

### Running all integration tests:
```bash
./tools/torq_test --integration
```

### Targeting Specific Devices
If you have multiple devices connected, or want to specify which device to use, provide the --serial flags:

```bash
./tools/torq_test --integration --serial <primary-serial>
```

## 3. Advanced Integration Tests
Some integration tests have specific hardware or environment requirements.

### VM Unified Tracing
Torq can aggregate trace data from two different virtual machines using VSOCK/IP.

### Setup Requirements:

Two CVD Instances: Launch Cuttlefish with at least two instances on same network.

VSOCK Support: Ensure the kernel supports /dev/vsock.

Primary CID: VSOCK guest CID of one of the launched instances to be used as primary.

Execution: Test automatically skipped unless --serial2 and --primary-cid are provided:

### Example:
```bash
./tools/torq_test --integration \
    --serial 0.0.0.0:6520 \
    --serial2 0.0.0.0:6521 \
    --primary-cid 3
```

### Troubleshooting
If you encounter "Machine count is 1" in Unified Tracing:

Ensure the traced-relay process is running on the secondary VM.

Verify setenforce 0 has been applied to both VMs.

Check secondary device to confirm the VSOCK connection is ESTABLISHED using:
```bash
adb shell netstat -an | grep <primary-cid>
```

### SELinux
Integration tests often require interacting with system daemons like traced. If you encounter "Permission Denied" errors, ensure the devices are in permissive mode:

```bash
adb shell setenforce 0
```