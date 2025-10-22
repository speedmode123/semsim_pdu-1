"""
Unit tests for PDU commands
"""
import unittest
import json
from pdu_state import PduStateManager
import pdu


class TestPduCommands(unittest.TestCase):
    """Test PDU command processing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state_manager = PduStateManager()
        self.apid_n = 0x65
        self.apid_r = 0x66
    
    def test_get_pdu_status(self):
        """Test GetPduStatus command"""
        result = pdu.GetPduStatus({}, self.apid_n, self.state_manager)
        result_dict = json.loads(result)
        
        self.assertIn('PduStatus', result_dict)
        self.assertEqual(result_dict['PduStatus']['PduState'], 0x01)
    
    def test_obc_heartbeat(self):
        """Test ObcHeartBeat command"""
        heartbeat_cmd = {
            "ObcHeartBeat": {
                "HeartBeat": 0x42
            }
        }
        
        result = pdu.ObcHeartBeat(heartbeat_cmd, self.apid_n, self.state_manager)
        result_dict = json.loads(result)
        
        self.assertEqual(result_dict['PduHeartBeat']['HeartBeat'], 0x42)
    
    def test_pdu_go_operate(self):
        """Test PduGoOperate command"""
        # Set initial state to Load (1)
        unit = self.state_manager.get_unit(self.apid_n)
        unit.status.PduState = 1
        
        # Execute PduGoOperate
        pdu.PduGoTo("PduGoOperate", self.apid_n, self.state_manager)
        
        # Verify state changed to Operate (2)
        self.assertEqual(unit.status.PduState, 2)
    
    def test_pdu_go_safe(self):
        """Test PduGoSafe command"""
        # Set initial state to Operate (2)
        unit = self.state_manager.get_unit(self.apid_n)
        unit.status.PduState = 2
        
        # Execute PduGoSafe
        pdu.PduGoTo("PduGoSafe", self.apid_n, self.state_manager)
        
        # Verify state changed to Safe (3)
        self.assertEqual(unit.status.PduState, 3)
    
    def test_pdu_go_maintenance(self):
        """Test PduGoMaintenance command"""
        # Set initial state to Safe (3)
        unit = self.state_manager.get_unit(self.apid_n)
        unit.status.PduState = 3
        
        # Execute PduGoMaintenance
        pdu.PduGoTo("PduGoMaintenance", self.apid_n, self.state_manager)
        
        # Verify state changed to Maintenance (4)
        self.assertEqual(unit.status.PduState, 4)
    
    def test_set_unit_pw_lines(self):
        """Test SetUnitPwLines command"""
        set_cmd = {
            "SetUnitPwLines": {
                "LogicUnitId": 0,  # HighPwHeaterEnSel
                "Parameters": 0xFF
            }
        }
        
        pdu.SetUnitPwLines(set_cmd, self.apid_n, self.state_manager)
        
        unit = self.state_manager.get_unit(self.apid_n)
        self.assertEqual(unit.unit_line_states.HighPwHeaterEnSel, 0xFF)
    
    def test_get_unit_line_states(self):
        """Test GetUnitLineStates command"""
        # Set some line states
        unit = self.state_manager.get_unit(self.apid_n)
        unit.unit_line_states.ReactionWheelEnSel = 0x0F
        
        result = pdu.GetUnitLineStates({}, self.apid_n, self.state_manager)
        result_dict = json.loads(result)
        
        self.assertEqual(result_dict['PduUnitLineStates']['ReactionWheelEnSel'], 0x0F)
    
    def test_msg_acknowledgement_accepted(self):
        """Test message acknowledgement for accepted command"""
        # Set state to Load (1) so PduGoOperate is accepted
        unit = self.state_manager.get_unit(self.apid_n)
        unit.status.PduState = 1
        
        cmd = {"PduGoOperate": {}}
        ack, type, subtype = pdu.GetMsgAcknowlegement(cmd, self.apid_n, self.state_manager)
        
        self.assertEqual(ack['MsgAcknowlegement']['RequestedMsgId'], 'PduGoOperate')
        self.assertEqual(ack['MsgAcknowlegement']['PduReturnCode'], 0)
        self.assertEqual(subtype, 7)  # Accepted
    
    def test_msg_acknowledgement_rejected(self):
        """Test message acknowledgement for rejected command"""
        # Set state to Operate (2) so PduGoOperate is rejected
        unit = self.state_manager.get_unit(self.apid_n)
        unit.status.PduState = 2
        
        cmd = {"PduGoOperate": {}}
        ack, type, subtype = pdu.GetMsgAcknowlegement(cmd, self.apid_n, self.state_manager)
        
        self.assertEqual(ack['MsgAcknowlegement']['RequestedMsgId'], 'PduGoOperate')
        self.assertEqual(ack['MsgAcknowlegement']['PduReturnCode'], 1)
        self.assertEqual(subtype, 8)  # Rejected


if __name__ == '__main__':
    unittest.main()
