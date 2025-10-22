"""
Unit tests for PDU state management
"""
import unittest
import json
from pdu_state import (
    PduStateManager,
    PduHeartBeatState,
    PduStatusState,
    PduUnitLineStatesState
)


class TestPduStateManager(unittest.TestCase):
    """Test PDU State Manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state_manager = PduStateManager()
    
    def test_initialization(self):
        """Test state manager initialization"""
        self.assertIsNotNone(self.state_manager.pdu_n)
        self.assertIsNotNone(self.state_manager.pdu_r)
        self.assertTrue(self.state_manager.pdu_n.initialized)
        self.assertTrue(self.state_manager.pdu_r.initialized)
    
    def test_get_unit_by_apid(self):
        """Test getting unit by APID"""
        unit_n = self.state_manager.get_unit(0x65)
        unit_r = self.state_manager.get_unit(0x66)
        
        self.assertEqual(unit_n, self.state_manager.pdu_n)
        self.assertEqual(unit_r, self.state_manager.pdu_r)
    
    def test_get_unit_by_name(self):
        """Test getting unit by name"""
        unit_n = self.state_manager.get_unit_by_name('pdu_n')
        unit_r = self.state_manager.get_unit_by_name('pdu_r')
        
        self.assertEqual(unit_n, self.state_manager.pdu_n)
        self.assertEqual(unit_r, self.state_manager.pdu_r)
    
    def test_read_heartbeat_state(self):
        """Test reading heartbeat state"""
        state_json = self.state_manager.read_state('pdu_n', 'PduHeartBeat')
        state_dict = json.loads(state_json)
        
        self.assertIn('PduHeartBeat', state_dict)
        self.assertEqual(state_dict['PduHeartBeat']['HeartBeat'], 0x00)
        self.assertEqual(state_dict['PduHeartBeat']['PduState'], 0x00)
    
    def test_update_heartbeat_state(self):
        """Test updating heartbeat state"""
        new_state = {
            "PduHeartBeat": {
                "HeartBeat": 0x42,
                "PduState": 0x02
            }
        }
        
        self.state_manager.update_state('pdu_n', 'PduHeartBeat', json.dumps(new_state))
        
        unit = self.state_manager.get_unit_by_name('pdu_n')
        self.assertEqual(unit.heartbeat.HeartBeat, 0x42)
        self.assertEqual(unit.heartbeat.PduState, 0x02)
    
    def test_read_status_state(self):
        """Test reading status state"""
        state_json = self.state_manager.read_state('pdu_n', 'PduStatus')
        state_dict = json.loads(state_json)
        
        self.assertIn('PduStatus', state_dict)
        self.assertEqual(state_dict['PduStatus']['PduState'], 0x01)
    
    def test_update_unit_line_states(self):
        """Test updating unit line states"""
        new_state = {
            "PduUnitLineStates": {
                "HighPwHeaterEnSel": 0xFF,
                "LowPwHeaterEnSel": 0xAA,
                "ReactionWheelEnSel": 0x0F,
                "PropEnSel": 0x03,
                "AvionicLoadEnSel": 0x01,
                "HdrmEnSel": 0x3F,
                "IsolatedLdoEnSel": 0x00,
                "IsolatedPwEnSel": 0x00,
                "ThermAndFlybackEnSel": 0xFF
            }
        }
        
        self.state_manager.update_state('pdu_r', 'PduUnitLineStates', json.dumps(new_state))
        
        unit = self.state_manager.get_unit_by_name('pdu_r')
        self.assertEqual(unit.unit_line_states.HighPwHeaterEnSel, 0xFF)
        self.assertEqual(unit.unit_line_states.LowPwHeaterEnSel, 0xAA)
        self.assertEqual(unit.unit_line_states.ReactionWheelEnSel, 0x0F)


class TestPduDataclasses(unittest.TestCase):
    """Test PDU dataclasses"""
    
    def test_heartbeat_to_dict(self):
        """Test heartbeat to_dict conversion"""
        heartbeat = PduHeartBeatState(HeartBeat=0x10, PduState=0x02)
        result = heartbeat.to_dict()
        
        self.assertEqual(result['PduHeartBeat']['HeartBeat'], 0x10)
        self.assertEqual(result['PduHeartBeat']['PduState'], 0x02)
    
    def test_status_to_dict(self):
        """Test status to_dict conversion"""
        status = PduStatusState(PduState=0x02, ProtectionStatus=0x01)
        result = status.to_dict()
        
        self.assertEqual(result['PduStatus']['PduState'], 0x02)
        self.assertEqual(result['PduStatus']['ProtectionStatus'], 0x01)
    
    def test_unit_line_states_to_dict(self):
        """Test unit line states to_dict conversion"""
        line_states = PduUnitLineStatesState(
            HighPwHeaterEnSel=0xFF,
            LowPwHeaterEnSel=0xAA
        )
        result = line_states.to_dict()
        
        self.assertEqual(result['PduUnitLineStates']['HighPwHeaterEnSel'], 0xFF)
        self.assertEqual(result['PduUnitLineStates']['LowPwHeaterEnSel'], 0xAA)


if __name__ == '__main__':
    unittest.main()
