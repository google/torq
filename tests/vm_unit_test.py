#
# Copyright (C) 2025 The Android Open Source Project
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

import io
import unittest
from contextlib import redirect_stderr
from src.device import AndroidDevice, OsCodes, QnxDevice
from src.vm import (DEFAULT_IP_ADDR, TRACED_ENABLE_PROP,
                    TRACED_MACHINE_NAME_PROP, TRACED_RELAY_PORT_PROP,
                    TRACED_RELAY_PRODUCER_PORT_PROP, DEFAULT_VSOCK_ADDR)
from tests.test_utils import run_cli
from unittest import mock

TEST_SERIAL = "test-serial"


class VmUnitTest(unittest.TestCase):

  def setUp(self):
    self.mock_device = mock.create_autospec(AndroidDevice, instance=True)
    self.mock_device.os.return_value = OsCodes.OS_ANDROID
    self.mock_qnx_device = mock.create_autospec(QnxDevice, instance=True)
    self.mock_qnx_device.os.return_value = OsCodes.OS_QNX
    self.torq_get_device_patcher = mock.patch(
        'src.torq.get_device', autospec=True)
    self.mock_torq_get_device = self.torq_get_device_patcher.start()
    self.mock_torq_get_device.return_value = (self.mock_device, None)

    self.vm_get_device_patcher = mock.patch('src.vm.get_device', autospec=True)
    self.mock_vm_get_device = self.vm_get_device_patcher.start()
    self.mock_vm_get_device.return_value = (self.mock_device, None)

  def tearDown(self):
    self.torq_get_device_patcher.stop()
    self.vm_get_device_patcher.stop()
    self.mock_device = None
    self.mock_qnx_device = None

  def test_set_primary(self):

    run_cli(f"torq vm configure --primary {TEST_SERIAL}")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PRODUCER_PORT_PROP,
                                              DEFAULT_VSOCK_ADDR)
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "1")

  def test_set_primary_with_machine_name(self):

    run_cli(f"torq vm configure --primary machine_name={TEST_SERIAL}")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_MACHINE_NAME_PROP,
                                              "machine_name")
    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PRODUCER_PORT_PROP,
                                              DEFAULT_VSOCK_ADDR)
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "1")

  def test_set_primary_with_tcp(self):

    run_cli(f"torq vm configure --primary {TEST_SERIAL} --primary-ip 0.0.0.2")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PRODUCER_PORT_PROP,
                                              DEFAULT_IP_ADDR)
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "1")

  def test_set_primary_with_custom_vsock_addr(self):

    run_cli(
        f"torq vm configure --primary {TEST_SERIAL} --primary-addr vsock://5:4000"
    )

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PRODUCER_PORT_PROP,
                                              "vsock://-1:4000")
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "1")

  def test_set_primary_with_custom_tcp_addr(self):

    run_cli(
        f"torq vm configure --primary {TEST_SERIAL} --primary-addr 0.0.0.1:4000"
    )

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PRODUCER_PORT_PROP,
                                              "0.0.0.0:4000")
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "1")

  def test_primary_with_incorrect_name_format(self):
    tmp_stderr = io.StringIO()

    with redirect_stderr(tmp_stderr):
      run_cli("torq vm configure --primary p1=hello=bye")

    output = tmp_stderr.getvalue()
    self.assertIn(
        "Invalid format used in either "
        "--primary or --secondary argument: 'p1=hello=bye'", output)

  def test_primary_with_empty_string(self):
    tmp_stderr = io.StringIO()

    with redirect_stderr(tmp_stderr):
      # Use a list to simulate sys.argv with an empty string argument
      with mock.patch("sys.argv", ["torq", "vm", "configure", "--primary", ""]):
        from src.torq import run
        run()

    output = tmp_stderr.getvalue()
    self.assertIn(
        "Invalid format used in either "
        "--primary or --secondary argument: ''", output)

  def test_primary_with_empty_serial(self):
    tmp_stderr = io.StringIO()

    with redirect_stderr(tmp_stderr):
      run_cli("torq vm configure --primary machine=")

    output = tmp_stderr.getvalue()
    self.assertIn(
        "Invalid format used in either "
        "--primary or --secondary argument: 'machine='", output)

  def test_multiple_primaries_error(self):
    tmp_stderr = io.StringIO()

    with self.assertRaises(SystemExit), redirect_stderr(tmp_stderr):
      run_cli("torq vm configure --primary p1 --primary p2")

    output = tmp_stderr.getvalue()
    self.assertIn("--primary can only be specified once", output)

  def test_set_secondary(self):

    run_cli(f"torq vm configure --primary-cid 4 --secondary {TEST_SERIAL}")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PORT_PROP,
                                              "vsock://4:30001")
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "2")

  def test_set_secondary_with_machine_name(self):

    run_cli(
        f"torq vm configure --primary-cid 4 --secondary guest_name={TEST_SERIAL}"
    )

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_MACHINE_NAME_PROP,
                                              "guest_name")
    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PORT_PROP,
                                              "vsock://4:30001")
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "2")

  def test_set_secondary_with_ip(self):

    run_cli(f"torq vm configure --primary-ip 0.0.0.0 --secondary {TEST_SERIAL}")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PORT_PROP,
                                              "0.0.0.0:30001")
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "2")

  def test_multiple_secondary_without_primary_address(self):
    tmp_stderr = io.StringIO()

    with redirect_stderr(tmp_stderr):
      run_cli("torq vm configure --secondary machine2")

    output = tmp_stderr.getvalue()
    self.assertIn(
        "Unable to resolve the network address of the primary machine", output)

  def test_multiple_primary_cid_error(self):
    tmp_stderr = io.StringIO()

    with self.assertRaises(SystemExit), redirect_stderr(tmp_stderr):
      run_cli("torq vm configure --primary-cid 1 --primary-cid 2")

    output = tmp_stderr.getvalue()
    self.assertIn("--primary-cid can only be specified once", output)

  def test_multiple_primary_ip_error(self):
    tmp_stderr = io.StringIO()

    with self.assertRaises(SystemExit), redirect_stderr(tmp_stderr):
      run_cli("torq vm configure --primary-ip 0.0.0.0 --primary-ip 0.0.0.1")

    output = tmp_stderr.getvalue()
    self.assertIn("--primary-ip can only be specified once", output)

  def test_multiple_primary_addr_error(self):
    tmp_stderr = io.StringIO()

    with self.assertRaises(SystemExit), redirect_stderr(tmp_stderr):
      run_cli(
          "torq vm configure --primary-addr 0.0.0.0:3000 --primary-addr 0.0.0.1:4000"
      )

    output = tmp_stderr.getvalue()
    self.assertIn("--primary-addr can only be specified once", output)

  def test_set_multiple_machines(self):

    run_cli(f"torq vm configure --primary-cid 4 --primary main={TEST_SERIAL} "
            "--secondary guest=test-serial2")

    self.assertEqual(self.mock_vm_get_device.call_count, 2)
    self.mock_vm_get_device.assert_any_call(TEST_SERIAL, True)
    self.mock_vm_get_device.assert_any_call("test-serial2", True)

    # Assert the primary machine
    self.mock_device.set_prop.assert_any_call(TRACED_MACHINE_NAME_PROP, "main")
    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PRODUCER_PORT_PROP,
                                              "vsock://-1:30001")

    # Assert the secondary machine
    self.mock_device.set_prop.assert_any_call(TRACED_MACHINE_NAME_PROP, "guest")
    self.mock_device.set_prop.assert_any_call(TRACED_RELAY_PORT_PROP,
                                              "vsock://4:30001")
    # Assert the last call
    self.mock_device.set_prop.assert_called_with(TRACED_ENABLE_PROP, "2")

  def test_set_primary_qnx(self):
    self.mock_vm_get_device.return_value = (self.mock_qnx_device, None)

    run_cli(f"torq vm configure --primary {TEST_SERIAL}")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_qnx_device.set_traced_producer_relay_port.assert_called_once_with(
        DEFAULT_VSOCK_ADDR, None)

  def test_set_secondary_qnx(self):
    self.mock_vm_get_device.return_value = (self.mock_qnx_device, None)

    run_cli(f"torq vm configure --primary-cid 4 --secondary {TEST_SERIAL}")

    self.mock_vm_get_device.assert_called_once_with(TEST_SERIAL, True)

    self.mock_qnx_device.set_traced_relay.assert_called_once_with(
        "vsock://4:30001", None)

  def test_vm_relay_producer_enable_qnx(self):
    self.mock_torq_get_device.return_value = (self.mock_qnx_device, None)

    run_cli(f"torq --serial {TEST_SERIAL} vm relay-producer enable")

    self.mock_torq_get_device.assert_called_once_with(TEST_SERIAL, False)
    self.mock_qnx_device.set_traced_producer_relay_port.assert_called_once_with(
        DEFAULT_VSOCK_ADDR, None)

  def test_vm_relay_producer_disable_qnx(self):
    self.mock_torq_get_device.return_value = (self.mock_qnx_device, None)

    run_cli(f"torq --serial {TEST_SERIAL} vm relay-producer disable")

    self.mock_torq_get_device.assert_called_once_with(TEST_SERIAL, False)
    self.mock_qnx_device.set_traced_producer_relay_port.assert_called_once_with(
        None)

  def test_vm_traced_relay_enable_qnx(self):
    self.mock_torq_get_device.return_value = (self.mock_qnx_device, None)

    run_cli(
        f"torq --serial {TEST_SERIAL} vm traced-relay enable vsock://4:30001")

    self.mock_torq_get_device.assert_called_once_with(TEST_SERIAL, False)
    self.mock_qnx_device.set_traced_relay.assert_called_once_with(
        "vsock://4:30001", None)

  def test_vm_traced_relay_disable_qnx(self):
    self.mock_torq_get_device.return_value = (self.mock_qnx_device, None)

    run_cli(f"torq --serial {TEST_SERIAL} vm traced-relay disable")

    self.mock_torq_get_device.assert_called_once_with(TEST_SERIAL, False)
    self.mock_qnx_device.set_traced_relay.assert_called_once_with(None)


if __name__ == "__main__":
  unittest.main()
