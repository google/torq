# Testing Torq

This document provides detailed instructions on how to set up and run tests for `torq`.

## Test Suites

Torq has three main categories of tests:
1. **Unit Tests:** Test individual components in isolation.
2. **Integration Tests:** Test Android events functionality using 1 real or emulated Android device.
3. **Advanced Integration Tests:** Test end-to-end unified vm tracing involving 2 real or emulated Android devices.

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
Integration tests require at least one active Android device or Cuttlefish (CVD) instance.

### Prerequisites
ADB: Installed and available in your PATH.

Root Access: adbd must be running as root on the target device(s).

Environment: ANDROID_PRODUCT_OUT should be set if testing simpleperf or specific binary pushing.

One device: Launch at least one Android device or Cuttlefish instance.

### Running all integration tests:
```bash
./tools/torq_test --integration
```

### Targeting Specific Devices
If you have multiple devices connected and want to specify which device to use, provide the --serial flags:

```bash
./tools/torq_test --integration --serial <primary-serial>
```

If no serial is provided with the --serial flag, the first adb device detected will be used in the test.

## 3. Advanced Integration Tests
Some integration tests have specific hardware or environment requirements.

### VM Unified Tracing
Torq can aggregate trace data from two different virtual machines using VSOCK/IP.

### Setup Requirements:

Two devices: Launch 2 Android devices or Cuttlefish instances on the same network.

VSOCK Support: Ensure the kernel supports /dev/vsock.

Primary CID: Use --primary-cid flag to provide the VSOCK guest CID of one of the launched instances to be used as primary.

Execution: If either --serial2 or --primary-cid is missing, the test is skipped.

### Example:
```bash
./tools/torq_test --integration \
    --serial 0.0.0.0:6520 \
    --serial2 0.0.0.0:6521 \
    --primary-cid 3
```

### Troubleshooting VM Unified Tracing Test Failures
##### 1. "Machine count is 1" in Unified Tracing Test:
- Ensure the traced-relay process is running on the secondary VM using:
```bash
adb shell ls /system/bin/traced_relay
```

- Check secondary device to confirm the VSOCK connection is established using:

```bash
adb shell netstat -an | grep <primary-cid>
```

##### 2. "Permission Denied" errors
- Ensure that both devices are running as root, if they aren't then make them root using:
```bash
adb -s <serial> root
adb -s <serial2> root
```

- The current enforcing state of the devices can be checked using:
```bash
adb -s <serial> shell getenforce
adb -s <serial2> shell getenforce
```

- If the devices are in "Enforcing" mode, they can be switched to "Permissive" mode using:
```bash
adb -s <serial> shell setenforce 0
adb -s <serial2> shell setenforce 0
```
