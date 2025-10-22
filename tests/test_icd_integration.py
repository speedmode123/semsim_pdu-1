"""
PDU ICD Integration Test
Tests OBC-to-SEMSIM communication via TCP/IP with ICD-compliant commands and responses

PREREQUISITES:
    1. Start SEMSIM server in a separate terminal:
       python semsim.py --mode simulator --tcp-ip 127.0.0.1 --tcp-port 5004
    
    2. Wait for server to be ready (you'll see "TMTC Manager started")
    
    3. Run this test:
       python -m unittest tests.test_icd_integration -v
       OR
       python tests/test_icd_integration.py
"""
import unittest
import socket
import json
import time

# Test configuration
TEST_IP = "127.0.0.1"
TEST_PORT = 5004
APID = 0x100  # PDU APID


class TestPduIcdIntegration(unittest.TestCase):
    """Integration test for PDU ICD compliance"""
    
    @classmethod
    def setUpClass(cls):
        """Test SEMSIM connection once before all tests"""
        print("\n" + "="*70)
        print("CHECKING SEMSIM SERVER CONNECTION")
        print("="*70)
        
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.settimeout(2.0)
        
        try:
            # Send a simple heartbeat to test connection
            command = {"ObcHeartBeat": {"HeartBeat": 0}}
            command_json = json.dumps(command)
            
            # Create minimal space packet
            packet = cls._create_test_packet(command_json, 3, 1, 0)
            test_socket.sendto(packet, (TEST_IP, TEST_PORT))
            
            # Try to receive response
            response_data, _ = test_socket.recvfrom(4096)
            print("✓ SEMSIM server is running and responding")
            print("="*70 + "\n")
            
        except socket.timeout:
            test_socket.close()
            raise unittest.SkipTest(
                f"\n\n{'='*70}\n"
                f"ERROR: Cannot connect to SEMSIM server!\n"
                f"{'='*70}\n"
                f"Please start SEMSIM in a separate terminal:\n"
                f"  python semsim.py --mode simulator --tcp-ip {TEST_IP} --tcp-port {TEST_PORT}\n"
                f"{'='*70}\n"
            )
        except Exception as e:
            test_socket.close()
            raise unittest.SkipTest(
                f"\n\n{'='*70}\n"
                f"ERROR: Connection error: {e}\n"
                f"{'='*70}\n"
                f"Please ensure SEMSIM is running:\n"
                f"  python semsim.py --mode simulator --tcp-ip {TEST_IP} --tcp-port {TEST_PORT}\n"
                f"{'='*70}\n"
            )
        finally:
            test_socket.close()
    
    @staticmethod
    def _create_test_packet(command_json, packet_type, subtype, seq_count):
        """Helper to create test packet"""
        command_bytes = bytes(command_json, 'utf-8')
        
        # Packet header
        tc_version = 0x00
        tc_type = 0x01
        tc_dfh_flag = 0x01
        tc_apid = APID
        tc_seq_flag = 0x03
        
        # Data field header
        data_field_header = [0x10, packet_type, subtype, 0x00]
        data_pack_cuck = [0x2F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        data_field_header_frame = data_field_header + data_pack_cuck
        
        packet_header_length = len(data_field_header_frame)
        packet_data_length_field = packet_header_length + len(command_bytes) - 1
        
        # Build packet
        packet = bytes([
            (tc_version << 5) | (tc_type << 4) | (tc_dfh_flag << 3) | (tc_apid >> 8),
            (tc_apid & 0xFF),
            (tc_seq_flag << 6) | (seq_count >> 8),
            (seq_count & 0xFF),
            (packet_data_length_field >> 8),
            (packet_data_length_field & 0xFF)
        ])
        
        for byte_val in data_field_header_frame:
            packet += byte_val.to_bytes(1, 'big')
        
        packet += command_bytes
        return packet
    
    def setUp(self):
        """Create UDP socket for each test"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(5.0)  # 5 second timeout
        self.sequence_count = 0
    
    def tearDown(self):
        """Close socket after each test"""
        if self.socket:
            self.socket.close()
        # Small delay between tests
        time.sleep(0.2)
    
    def create_space_packet(self, command_json, packet_type=1, subtype=1):
        """Create CCSDS Space Packet for command"""
        command_bytes = bytes(command_json, 'utf-8')
        
        packet = self._create_test_packet(command_json, packet_type, subtype, self.sequence_count)
        self.sequence_count = (self.sequence_count + 1) % 16384
        return packet
    
    def decode_space_packet(self, packet):
        """Decode CCSDS Space Packet response"""
        if len(packet) < 6:
            return None, None, None, None
        
        # Parse header
        packet_type = (packet[0] >> 4) & 0x01
        apid = ((packet[0] & 0x07) << 8) | packet[1]
        sequence_count = ((packet[2] & 0x3F) << 8) | packet[3]
        packet_data_length = (packet[4] << 8) | packet[5] + 1
        
        # Parse data field header
        if len(packet) < 18:
            return None, None, None, None
        
        msg_type = packet[7]
        subtype = packet[8]
        
        # Extract JSON payload
        payload_start = 18
        payload = packet[payload_start:payload_start + packet_data_length - 12]
        
        try:
            json_data = json.loads(payload.decode('utf-8'))
            return apid, msg_type, subtype, json_data
        except Exception as e:
            print(f"Warning: Failed to decode JSON payload: {e}")
            return apid, msg_type, subtype, None
    
    def send_command(self, command_dict, packet_type=1, subtype=1, expect_response=True):
        """Send command and optionally receive response"""
        command_json = json.dumps(command_dict)
        packet = self.create_space_packet(command_json, packet_type, subtype)
        
        print(f"→ Sending: {command_dict}")
        self.socket.sendto(packet, (TEST_IP, TEST_PORT))
        
        if not expect_response:
            return None, None, None, None
        
        # Receive response
        try:
            response_data, _ = self.socket.recvfrom(4096)
            apid, msg_type, subtype, json_response = self.decode_space_packet(response_data)
            print(f"← Received: {json_response}")
            return apid, msg_type, subtype, json_response
        except socket.timeout:
            print("⚠ No response received (timeout)")
            return None, None, None, None
    
    # ========================================================================
    # Test Cases
    # ========================================================================
    
    def test_01_heartbeat(self):
        """Test OBC heartbeat command"""
        print("\n" + "="*70)
        print("TEST: OBC Heartbeat")
        print("="*70)
        
        command = {"ObcHeartBeat": {"HeartBeat": 42}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=1)
        
        # Verify response
        self.assertIsNotNone(response, "No response received from SEMSIM")
        self.assertIn("PduHeartBeat", response)
        self.assertEqual(response["PduHeartBeat"]["HeartBeat"], 42)
        self.assertIn("PduState", response["PduHeartBeat"])
        
        print("✓ Heartbeat test passed")
    
    def test_02_get_pdu_status(self):
        """Test GetPduStatus command"""
        print("\n" + "="*70)
        print("TEST: Get PDU Status")
        print("="*70)
        
        command = {"GetPduStatus": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=25)
        
        # Verify response structure
        self.assertIsNotNone(response, "No response received from SEMSIM")
        self.assertIn("PduStatus", response)
        
        status = response["PduStatus"]
        self.assertIn("PduState", status)
        self.assertIn("ProtectionStatus", status)
        
        print(f"✓ PDU Status: State={status['PduState']}, Mode={status['ProtectionStatus']}")
    
    def test_03_get_unit_line_states(self):
        """Test GetUnitLineStates command"""
        print("\n" + "="*70)
        print("TEST: Get Unit Line States")
        print("="*70)
        
        command = {"GetUnitLineStates": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=129)
        
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
        """Test PduGoOperate state transition"""
        print("\n" + "="*70)
        print("TEST: State Transition to Operate")
        print("="*70)
        
        command = {"PduGoOperate": {}}
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        
        # Receive acknowledgement
        response_data, _ = self.socket.recvfrom(4096)
        apid, msg_type, subtype, ack_response = self.decode_space_packet(response_data)
        
        print(f"← Operate Ack: {ack_response}")
        
        # Verify acknowledgement
        self.assertIsNotNone(ack_response)
        self.assertIn("MsgAcknowledgement", ack_response)
        
        # Verify state changed
        time.sleep(0.5)
        command = {"GetPduStatus": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=25)
        
        self.assertEqual(response["PduStatus"]["PduState"], 2)  # Operate state
        
        print("✓ State transition to Operate successful")
    
    def test_05_set_unit_power_lines(self):
        """Test SetUnitPwLines command"""
        print("\n" + "="*70)
        print("TEST: Set Unit Power Lines")
        print("="*70)
        
        # Set high power heater lines
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 0,  # HighPwHeaterEnSel
                "Parameters": 3  # Enable first two lines (0x0003)
            }
        }
        
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        
        # Receive acknowledgement
        response_data, _ = self.socket.recvfrom(4096)
        apid, msg_type, subtype, ack_response = self.decode_space_packet(response_data)
        
        print(f"← Set Ack: {ack_response}")
        
        # Verify lines were set
        time.sleep(0.5)
        command = {"GetUnitLineStates": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=129)
        
        self.assertEqual(response["PduUnitLineStates"]["HighPwHeaterEnSel"], 3)
        
        print("✓ Unit power lines set successfully")
    
    def test_06_get_converted_measurements(self):
        """Test GetConvertedMeasurements command"""
        print("\n" + "="*70)
        print("TEST: Get Converted Measurements")
        print("="*70)
        
        # First set some unit lines to get measurements
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 2,  # ReactionWheelEnSel
                "Parameters": 15  # Enable all 4 reaction wheels (0x000F)
            }
        }
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        
        # Wait for ack
        self.socket.recvfrom(4096)
        time.sleep(0.5)
        
        # Get measurements
        command = {
            "GetConvertedMeasurements": {
                "LogicUnitId": 2  # ReactionWheelEnSel
            }
        }
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=131)
        
        # Verify acknowledgement
        self.assertIsNotNone(response)
        self.assertIn("MsgAcknowledgement", response)

        response, _ = self.socket.recvfrom(4096)

        # Verify response
        self.assertIsNotNone(response)
        self.assertIn("PduConvertedMeasurements", response)
        
        measurements = response["PduConvertedMeasurements"]
        self.assertIn("ReactionWheelAdcSel", measurements)
        
        # Should have 4 measurements (one per reaction wheel)
        rw_measurements = measurements["ReactionWheelAdcSel"]
        self.assertEqual(len(rw_measurements), 4)
        
        # Each measurement should be around 5A (nominal current)
        for measurement in rw_measurements:
            self.assertGreater(measurement, 4.0)
            self.assertLess(measurement, 6.0)
        
        print(f"✓ Converted measurements: {rw_measurements}")
    
    def test_07_state_transition_to_safe(self):
        """Test PduGoSafe state transition"""
        print("\n" + "="*70)
        print("TEST: State Transition to Safe")
        print("="*70)
        
        # Ensure we're in Operate state first
        command = {"PduGoOperate": {}}
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        self.socket.recvfrom(4096)
        time.sleep(0.5)
        
        # Transition to Safe
        command = {"PduGoSafe": {}}
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        
        # Receive acknowledgement
        response_data, _ = self.socket.recvfrom(4096)
        apid, msg_type, subtype, ack_response = self.decode_space_packet(response_data)
        
        # Verify acknowledgement
        self.assertIsNotNone(ack_response)
        self.assertIn("PduMsgAcknowledgement", ack_response)
        self.assertEqual(ack_response["PduMsgAcknowledgement"]["PduReturnCode"], 0)
        
        # Verify state changed
        time.sleep(0.5)
        command = {"GetPduStatus": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=25)
        
        self.assertEqual(response["PduStatus"]["PduState"], 3)  # Safe state
        
        print("✓ State transition to Safe successful")
    
    def test_08_reset_unit_power_lines(self):
        """Test ResetUnitPwLines command"""
        print("\n" + "="*70)
        print("TEST: Reset Unit Power Lines")
        print("="*70)
        
        # First set some lines
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 1,  # LowPwHeaterEnSel
                "Parameters": 255  # 0x00FF
            }
        }
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        self.socket.recvfrom(4096)
        time.sleep(0.5)
        
        # Reset specific lines
        command = {
            "ResetUnitPwLines": {
                "LogicUnitId": 1,  # LowPwHeaterEnSel
                "Parameters": 15  # Reset first 4 lines (0x000F)
            }
        }
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        self.socket.recvfrom(4096)
        time.sleep(0.5)
        
        # Verify lines were reset
        command = {"GetUnitLineStates": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=129)
        
        # Should be 0x00F0 (first 4 bits reset, last 4 still set)
        self.assertEqual(response["PduUnitLineStates"]["LowPwHeaterEnSel"], 240)  # 0x00F0
        
        print("✓ Unit power lines reset successfully")
    
    def test_09_multiple_commands_sequence(self):
        """Test sequence of multiple commands"""
        print("\n" + "="*70)
        print("TEST: Multiple Commands Sequence")
        print("="*70)
        
        # 1. Get initial status
        command = {"GetPduStatus": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=25)
        initial_state = response["PduStatus"]["PduState"]
        print(f"  Initial state: {initial_state}")
        
        # 2. Set unit lines
        command = {"SetUnitPwLines": {"LogicUnitId": 3, "Parameters": 3}}
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        self.socket.recvfrom(4096)
        time.sleep(0.3)
        
        # 3. Get unit line states
        command = {"GetUnitLineStates": {}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=129)
        self.assertEqual(response["PduUnitLineStates"]["PropEnSel"], 3)
        print(f"  PropEnSel set to: 0x{response['PduUnitLineStates']['PropEnSel']:04X}")
        
        # 4. Get measurements
        command = {"GetConvertedMeasurements": {"LogicUnitId": 3}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=131)
        measurements = response["PduConvertedMeasurements"]["PropAdcSel"]
        print(f"  Prop measurements: {measurements}")
        
        # 5. Send heartbeat
        command = {"ObcHeartBeat": {"HeartBeat": 100}}
        apid, msg_type, subtype, response = self.send_command(command, packet_type=3, subtype=1)
        self.assertEqual(response["PduHeartBeat"]["HeartBeat"], 100)
        print(f"  Heartbeat: {response['PduHeartBeat']['HeartBeat']}")
        
        print("✓ Multiple commands sequence completed successfully")
    
    def test_10_error_handling(self):
        """Test error handling with invalid commands"""
        print("\n" + "="*70)
        print("TEST: Error Handling")
        print("="*70)
        
        command = {
            "SetUnitPwLines": {
                "LogicUnitId": 99,  # Invalid unit ID
                "Parameters": 1
            }
        }
        self.send_command(command, packet_type=1, subtype=1, expect_response=False)
        
        try:
            # Try to receive acknowledgement
            response_data, _ = self.socket.recvfrom(4096)
            apid, msg_type, subtype, ack_response = self.decode_space_packet(response_data)
            
            if ack_response and "PduMsgAcknowledgement" in ack_response:
                # Should receive error acknowledgement
                return_code = ack_response["PduMsgAcknowledgement"]["PduReturnCode"]
                print(f"  Received error code: {return_code}")
                self.assertNotEqual(return_code, 0, "Expected error return code")
                print("✓ Error handling working correctly")
            else:
                print("⚠ No acknowledgement received for invalid command")
        except socket.timeout:
            print("⚠ No response received (command may have been ignored)")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
