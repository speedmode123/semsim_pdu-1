"""
Communication tests for PDU simulator
Tests TCP/IP communication and command/response flow
"""
import unittest
import socket
import json
import time
from threading import Thread
from pdu_state import PduStateManager
from tmtc_manager import SpacePacketCommand, SpacePacketDecoder


class TestCommunication(unittest.TestCase):
    """Test PDU communication protocols"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state_manager = PduStateManager()
        self.test_ip = "127.0.0.1"
        self.test_port = 8484
        self.apid = 0x65
    
    def test_space_packet_encoding(self):
        """Test CCSDS Space Packet encoding"""
        command = {"GetPduStatus": {}}
        json_cmd = json.dumps(command)
        
        packet = SpacePacketCommand(0x01, json_cmd, self.apid, 2, 5)
        
        self.assertIsInstance(packet, bytes)
        self.assertGreater(len(packet), 0)
    
    def test_space_packet_decoding(self):
        """Test CCSDS Space Packet decoding"""
        # Create a packet
        command = {"GetPduStatus": {}}
        json_cmd = json.dumps(command)
        packet = SpacePacketCommand(0x01, json_cmd, self.apid, 2, 5)
        
        # Decode it
        data_field, apid, type, subtype = SpacePacketDecoder(packet)
        
        self.assertEqual(apid, self.apid)
        self.assertEqual(type, 2)
        self.assertEqual(subtype, 5)
        self.assertGreater(len(data_field), 0)
    
    def test_space_packet_roundtrip(self):
        """Test encoding and decoding roundtrip"""
        original_cmd = {"ObcHeartBeat": {"HeartBeat": 42}}
        json_cmd = json.dumps(original_cmd)
        
        # Encode
        packet = SpacePacketCommand(0x05, json_cmd, self.apid, 2, 1)
        
        # Decode
        data_field, apid, type, subtype = SpacePacketDecoder(packet)
        
        # Extract command
        command_packet = data_field[12:]
        decoded_cmd = json.loads(command_packet)
        
        self.assertEqual(decoded_cmd, original_cmd)
    
    def test_udp_socket_creation(self):
        """Test UDP socket creation and binding"""
        try:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            sock.bind((self.test_ip, self.test_port))
            sock.close()
            success = True
        except:
            success = False
        
        self.assertTrue(success)
    
    def test_command_response_flow(self):
        """Test complete command-response flow"""
        # This would require running the actual server
        # For now, just test the packet structure
        
        commands = [
            {"GetPduStatus": {}},
            {"ObcHeartBeat": {"HeartBeat": 1}},
            {"GetUnitLineStates": {}},
        ]
        
        for cmd in commands:
            json_cmd = json.dumps(cmd)
            packet = SpacePacketCommand(0x01, json_cmd, self.apid, 2, 1)
            
            # Verify packet can be decoded
            data_field, apid, type, subtype = SpacePacketDecoder(packet)
            command_packet = data_field[12:]
            decoded_cmd = json.loads(command_packet)
            
            self.assertEqual(decoded_cmd, cmd)


class TestPacketization(unittest.TestCase):
    """Test PDU packet encoding/decoding"""
    
    def test_packet_structure(self):
        """Test packet structure integrity"""
        test_data = {
            "TestCommand": {
                "param1": 123,
                "param2": "test"
            }
        }
        
        json_data = json.dumps(test_data)
        packet = SpacePacketCommand(0x10, json_data, 0x65, 2, 5)
        
        # Verify packet header
        self.assertEqual(len(packet), len(json_data) + 18)  # 6 byte header + 12 byte data header
    
    def test_multiple_apids(self):
        """Test packets with different APIDs"""
        command = {"GetPduStatus": {}}
        json_cmd = json.dumps(command)
        
        packet_n = SpacePacketCommand(0x01, json_cmd, 0x65, 2, 5)
        packet_r = SpacePacketCommand(0x01, json_cmd, 0x66, 2, 5)
        
        _, apid_n, _, _ = SpacePacketDecoder(packet_n)
        _, apid_r, _, _ = SpacePacketDecoder(packet_r)
        
        self.assertEqual(apid_n, 0x65)
        self.assertEqual(apid_r, 0x66)


if __name__ == '__main__':
    unittest.main()
