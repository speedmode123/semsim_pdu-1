"""
PDU RS422 Integration Test
Tests OBC-to-SEMSIM communication via RS422 with ICD-compliant commands and responses

PREREQUISITES:
    1. Connect RS422 hardware to /dev/ttyUSB0 (or specified port)
    
    2. Start SEMSIM server in emulator mode in a separate terminal:
       python semsim.py --mode emulator --rs422-port /dev/ttyUSB0 --rs422-baud 115200
    
    3. Wait for server to be ready (you'll see "RS422 listener started")
    
    4. Run this test:
       python -m unittest tests.test_rs422_integration -v
       OR
       python tests/test_rs422_integration.py

NOTES:
    - This test requires RS422 hardware and Linux environment
    - The baud rate must match SEMSIM configuration (default: 115200)
    - Test sends commands via /dev/ttyUSB0 and receives responses
"""
import unittest
import serial
import json
import time

try:
    from pdu_packetization import PduPacket, encode_pdu_packet, decode_pdu_packet, PACKETIZATION_AVAILABLE
    if not PACKETIZATION_AVAILABLE:
        raise ImportError("PDU packetization C library not available")
except ImportError as e:
    raise unittest.SkipTest(f"RS422 test requires pdu_packetization: {e}")

# Test configuration
TEST_PORT = "/dev/ttyUSB0"
TEST_BAUDRATE = 115200
APID = 0x65  # PDU APID

# Command IDs matching PDU ICD
PDU_COMMANDS = {
    "ObcHeartBeat": 1,
    "GetPduStatus": 2,
    "PduGoLoad": 8,
    "PduGoSafe": 9,
    "PduGoOperate": 10,
    "SetUnitPwLines": 11,
    "ResetUnitPwLines": 12,
    "OverwriteUnitPwLines": 13,
    "GetUnitLineStates": 14,
    "GetRawMeasurements": 15,
    "GetConvertedMeasurements": 16
}


class TestPduRs422Integration(unittest.TestCase):
    """Integration test for PDU RS422 ICD compliance"""
    
    @classmethod
    def setUpClass(cls):
        """Test RS422 connection once before all tests"""
        print("\n" + "="*70)
        print("CHECKING RS422 CONNECTION")
        print("="*70)
        
        try:
            # Try to open RS422 port
            test_serial = serial.Serial(
                port=TEST_PORT,
                baudrate=TEST_BAUDRATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=2.0
            )
            test_serial.flushInput()
            test_serial.flushOutput()
            
            # Send a simple heartbeat to test connection
            command_dict = {"ObcHeartBeat": {"HeartBeat": 0}}
            frame = cls._create_test_frame("ObcHeartBeat", 0, command_dict)
            test_serial.write(frame)
            
            # Try to receive response
            response_frame = cls._read_frame(test_serial)
            if response_frame:
                print("✓ RS422 connection is working and SEMSIM is responding")
                print("="*70 + "\n")
            else:
                raise Exception("No response from SEMSIM")
            
            test_serial.close()
            
        except serial.SerialException as e:
            raise unittest.SkipTest(
                f"\n\n{'='*70}\n"
                f"ERROR: Cannot open RS422 port {TEST_PORT}!\n"
                f"{'='*70}\n"
                f"Possible causes:\n"
                f"  - RS422 hardware not connected\n"
                f"  - Port {TEST_PORT} does not exist\n"
                f"  - Permission denied (try: sudo chmod 666 {TEST_PORT})\n"
                f"  - Port already in use by SEMSIM\n"
                f"\nError: {e}\n"
                f"{'='*70}\n"
            )
        except Exception as e:
            raise unittest.SkipTest(
                f"\n\n{'='*70}\n"
                f"ERROR: RS422 connection test failed: {e}\n"
                f"{'='*70}\n"
                f"Please ensure SEMSIM is running in emulator mode:\n"
                f"  python semsim.py --mode emulator --rs422-port {TEST_PORT} --rs422-baud {TEST_BAUDRATE}\n"
                f"{'='*70}\n"
            )
    
    @staticmethod
    def _create_test_frame(command_name, logical_unit_id, command_dict):
        """Helper to create test RS422 frame"""
        message_id = PDU_COMMANDS.get(command_name, 0)
        command_json = json.dumps(command_dict)
        payload_bytes = list(command_json.encode('utf-8'))
        
        packet = PduPacket()
        packet.message_id = message_id
        packet.logical_unit_id = logical_unit_id
        for byte in payload_bytes:
            packet.payload.append(byte)
        
        return encode_pdu_packet(packet)
    
    @staticmethod
    def _read_frame(ser, timeout=5.0):
        """Helper to read RS422 frame"""
        start_time = time.time()
        frame = bytearray()
        
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                byte = ser.read(1)
                if not byte:
                    continue
                
                # Look for start byte (0x55)
                if len(frame) == 0:
                    if byte[0] == 0x55:
                        frame.extend(byte)
                else:
                    frame.extend(byte)
                    # Check for end byte (0x55)
                    if byte[0] == 0x55 and len(frame) > 1:
                        return bytes(frame)
        
        return None
    
    def setUp(self):
        """Open RS422 serial port for each test"""
        self.serial = serial.Serial(
            port=TEST_PORT,
            baudrate=TEST_BAUDRATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=5.0
        )
        self.serial.flushInput()
        self.serial.flushOutput()
    
    def tearDown(self):
        """Close serial port after each test"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        # Small delay between tests
        time.sleep(0.2)
    
    def create_rs422_frame(self, command_name, logical_unit_id, command_dict):
        """Create RS422 frame for command"""
        message_id = PDU_COMMANDS.get(command_name, 0)
        command_json = json.dumps(command_dict)
        payload_bytes = list(command_json.encode('utf-8'))
        
        packet = PduPacket()
        packet.message_id = message_id
        packet.logical_unit_id = logical_unit_id
        for byte in payload_bytes:
            packet.payload.append(byte)
        
        return encode_pdu_packet(packet)
    
    def decode_rs422_frame(self, frame):
        """Decode RS422 frame response"""
        try:
            decoded_packet = decode_pdu_packet(frame)
            message_id = decoded_packet.message_id
            logical_unit_id = decoded_packet.logical_unit_id
            payload = bytes(decoded_packet.payload)
            
            # Parse JSON payload
            json_data = json.loads(payload.decode('utf-8'))
            return message_id, logical_unit_id, json_data
        except Exception as e:
            print(f"Warning: Failed to decode RS422 frame: {e}")
            return None, None, None
    
    def send_command(self, command_name, logical_unit_id, command_dict, expect_response=True):
        """Send command via RS422 and optionally receive response"""
        frame = self.create_rs422_frame(command_name, logical_unit_id, command_dict)
        
        print(f"→ Sending: {command_dict}")
        self.serial.write(frame)
        
        if not expect_response:
            return None, None, None
        
        # Receive response
        response_frame = self._read_frame(self.serial)
        if response_frame:
            message_id, lid, json_response = self.decode_rs422_frame(response_frame)
            print(f"← Received: {json_response}")
            return message_id, lid, json_response
        else:
            print("⚠ No response received (timeout)")
            return None, None, None
    
    # ========================================================================
    # Test Cases (matching TCP/IP integration test)
    # ========================================================================
    
    def test_01_heartbeat(self):
        """Test OBC heartbeat command via RS422"""
        print("\n" + "="*70)
        print("TEST: OBC Heartbeat (RS422)")
        print("="*70)
        
        command = {"ObcHeartBeat": {"HeartBeat": 42}}
        msg_id, lid, response = self.send_command("ObcHeartBeat", 0, command)
        
        # Verify response
        self.assertIsNotNone(response, "No response received from SEMSIM")
        self.assertIn("PduHeartBeat", response)
        self.assertEqual(response["PduHeartBeat"]["HeartBeat"], 42)
        self.assertIn("PduState", response["PduHeartBeat"])
        
        print("✓ RS422 Heartbeat test passed")
    
    def test_02_get_pdu_status(self):
        """Test GetPduStatus command via RS422"""
        print("\n" + "="*70)
        print("TEST: Get PDU Status (RS422)")
        print("="*70)
        
        command = {"GetPduStatus": {}}
        msg_id, lid, response = self.send_command("GetPduStatus", 0, command)
        
        # Verify response structure
        self.assertIsNotNone(response, "No response received from SEMSIM")
        self.assertIn("PduStatus", response)
        
        status = response["PduStatus"]
        self.assertIn("PduState", status)
        self.assertIn("ProtectionStatus", status)
        
        print(f"✓ PDU Status: State={status['PduState']}, Mode={status['ProtectionStatus']}")
    
    def test_03_get_unit_line_states(self):
        """Test GetUnitLineStates command via RS422"""
        print("\n" + "="*70)
        print("TEST: Get Unit Line States (RS422)")
        print("="*70)
        
        command = {"GetUnitLineStates": {}}
        msg_id, lid, response = self.send_command("GetUnitLineStates", 0, command)
        
        # Verify response structure
        self.assertIsNotNone(response, "No response received from SEMSIM")
        self.assertIn("PduUnitLineStates", response)
        
        unit_lines = response["PduUnitLineStates"]
        expected_lines = [
            "HighPwHeaterEnSel", "LowPwHeaterEnSel", "ReactionWheelEnSel",
            "PropEnSel", "AvionicLoadEnSel", "HdrmEnSel",
            "IsolatedLdoEnSel", "IsolatedPwEnSel", "ThermAndFlybackEnSel"
        ]
        
        for line in expected_lines:
            self.assertIn(line, unit_lines)
        
        print(f"✓ Unit Line States retrieved: {len(expected_lines)} categories")
    
    def test_04_state_transition_to_operate(self):
        """Test PduGoOperate state transition via RS422"""
        print("\n" + "="*70)
        print("TEST: State Transition to Operate (RS422)")
        print("="*70)
        
        command = {"PduGoOperate": {}}
        self.send_command("PduGoOperate", 0, command, expect_response=False)
        
        # Receive acknowledgement
        response_frame = self._read_frame(self.serial)
        msg_id, lid, ack_response = self.decode_rs422_frame(response_frame)
        
        print(f"← Operate Ack: {ack_response}")
        
        # Verify acknowledgement
        self.assertIsNotNone(ack_response)
        self.assertIn("MsgAcknowledgement", ack_response)
        
        # Verify state changed
        time.sleep(0.5)
        command = {"GetPduStatus": {}}
        msg_id, lid, response = self.send_command("GetPduStatus", 0, command)
        
        self.assertEqual(response["PduStatus"]["PduState"], 2)  # Operate state
        
        print("✓ State transition to Operate successful")
    
    def test_05_set_unit_power_lines(self):
        """Test SetUnitPwLines command via RS422"""
        print("\n" + "="*70)
        print("TEST: Set Unit Power Lines (RS422)")
        print("="*70)
        
        # Set high power heater lines
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 0,  # HighPwHeaterEnSel
                "Parameters": 3  # Enable first two lines (0x0003)
            }
        }
        
        self.send_command("SetUnitPwLines", 0, command, expect_response=False)
        
        # Receive acknowledgement
        response_frame = self._read_frame(self.serial)
        msg_id, lid, ack_response = self.decode_rs422_frame(response_frame)
        
        print(f"← Set Ack: {ack_response}")
        
        # Verify lines were set
        time.sleep(0.5)
        command = {"GetUnitLineStates": {}}
        msg_id, lid, response = self.send_command("GetUnitLineStates", 0, command)
        
        self.assertEqual(response["PduUnitLineStates"]["HighPwHeaterEnSel"], 3)
        
        print("✓ Unit power lines set successfully via RS422")
    
    def test_06_get_converted_measurements(self):
        """Test GetConvertedMeasurements command via RS422"""
        print("\n" + "="*70)
        print("TEST: Get Converted Measurements (RS422)")
        print("="*70)
        
        # First set some unit lines to get measurements
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 2,  # ReactionWheelEnSel
                "Parameters": 15  # Enable all 4 reaction wheels (0x000F)
            }
        }
        self.send_command("SetUnitPwLines", 2, command, expect_response=False)
        
        # Receive acknowledgement
        response_frame = self._read_frame(self.serial)
        msg_id, lid, ack_response = self.decode_rs422_frame(response_frame)
        
        print(f"← Set Ack: {ack_response}")
        
        time.sleep(0.5)  # Wait for measurements to update
        
        command = {
            "GetConvertedMeasurements": {
                "LogicUnitId": 2  # ReactionWheelEnSel
            }
        }
        msg_id, lid, response = self.send_command("GetConvertedMeasurements", 2, command)
        
        # Verify response
        self.assertIsNotNone(response, "No response received from SEMSIM")
        self.assertIn("PduConvertedMeasurements", response)
        
        measurements = response["PduConvertedMeasurements"]
        self.assertIn("ReactionWheelAdcSel", measurements)
        
        # Should have 4 measurements (one per reaction wheel)
        rw_measurements = measurements["ReactionWheelAdcSel"]
        self.assertEqual(len(rw_measurements), 4)
        
        print(f"✓ Converted measurements: {rw_measurements}")
    
    def test_07_reset_unit_power_lines(self):
        """Test ResetUnitPwLines command via RS422"""
        print("\n" + "="*70)
        print("TEST: Reset Unit Power Lines (RS422)")
        print("="*70)
        
        # First set some lines
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 1,  # LowPwHeaterEnSel
                "Parameters": 255  # 0x00FF
            }
        }
        self.send_command("SetUnitPwLines", 1, command, expect_response=False)
        
        response_frame = self._read_frame(self.serial)
        msg_id, lid, ack_response = self.decode_rs422_frame(response_frame)
        print(f"← Set Ack: {ack_response}")
        
        time.sleep(0.5)
        
        # Reset specific lines
        command = {
            "ResetUnitPwLines": {
                "LogicUnitId": 1,  # LowPwHeaterEnSel
                "Parameters": 15  # Reset first 4 lines (0x000F)
            }
        }
        self.send_command("ResetUnitPwLines", 1, command, expect_response=False)
        
        response_frame = self._read_frame(self.serial)
        msg_id, lid, ack_response = self.decode_rs422_frame(response_frame)
        print(f"← Reset Ack: {ack_response}")
        
        time.sleep(0.5)
        
        # Verify lines were reset
        command = {"GetUnitLineStates": {}}
        msg_id, lid, response = self.send_command("GetUnitLineStates", 0, command)
        
        # Should be 0x00F0 (first 4 bits reset, last 4 still set)
        self.assertEqual(response["PduUnitLineStates"]["LowPwHeaterEnSel"], 240)  # 0x00F0
        
        print("✓ Unit power lines reset successfully via RS422")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
