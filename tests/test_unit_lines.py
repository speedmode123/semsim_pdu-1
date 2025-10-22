"""
Unit Line Tests
Tests for PDU unit line control and MCP hardware integration
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pdu_state import PduStateManager, PduUnitLineStatesState
from mcp_manager import McpManager, MCP_PDU_MAP


class MockMCP23017:
    """Mock MCP23017 for testing without hardware"""
    def __init__(self, address):
        self.address = address
        self.pins = {i: 0xFF for i in range(16)}  # All HIGH (OFF) initially
        
    def set_default_config(self):
        pass
        
    def set_all_output(self):
        pass
        
    def set_pin_level(self, pin, level):
        self.pins[pin] = level
        
    def get_pin_level(self, pin):
        return self.pins[pin]


class TestUnitLineStates(unittest.TestCase):
    """Test PDU unit line state management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state_manager = PduStateManager()
        
    def test_initial_unit_line_states(self):
        """Test that unit lines are initialized to OFF"""
        pdu_n = self.state_manager.get_pdu_state(0x65)
        pdu_r = self.state_manager.get_pdu_state(0x66)
        
        self.assertEqual(pdu_n.unit_line_states.high_pw_heater_en_sel, 0x00)
        self.assertEqual(pdu_n.unit_line_states.low_pw_heater_en_sel, 0x00)
        self.assertEqual(pdu_r.unit_line_states.high_pw_heater_en_sel, 0x00)
        
    def test_set_unit_line_states(self):
        """Test setting unit line states"""
        pdu_n = self.state_manager.get_pdu_state(0x65)
        
        # Turn on first 3 high power heaters (bits 0, 1, 2)
        pdu_n.unit_line_states.high_pw_heater_en_sel = 0b111
        
        self.assertEqual(pdu_n.unit_line_states.high_pw_heater_en_sel, 0b111)
        
    def test_unit_line_to_dict(self):
        """Test unit line state serialization"""
        pdu_n = self.state_manager.get_pdu_state(0x65)
        pdu_n.unit_line_states.high_pw_heater_en_sel = 0xFF
        
        state_dict = pdu_n.unit_line_states.to_dict()
        
        self.assertIn('PduUnitLineStates', state_dict)
        self.assertEqual(state_dict['PduUnitLineStates']['HighPwHeaterEnSel'], 0xFF)
        
    def test_multiple_unit_line_categories(self):
        """Test setting multiple unit line categories"""
        pdu_n = self.state_manager.get_pdu_state(0x65)
        
        pdu_n.unit_line_states.high_pw_heater_en_sel = 0b11111111
        pdu_n.unit_line_states.low_pw_heater_en_sel = 0b1111
        pdu_n.unit_line_states.reaction_wheel_en_sel = 0b1111
        
        self.assertEqual(pdu_n.unit_line_states.high_pw_heater_en_sel, 0b11111111)
        self.assertEqual(pdu_n.unit_line_states.low_pw_heater_en_sel, 0b1111)
        self.assertEqual(pdu_n.unit_line_states.reaction_wheel_en_sel, 0b1111)


class TestMcpMapping(unittest.TestCase):
    """Test MCP to PDU unit line mapping"""
    
    def test_mcp_map_completeness(self):
        """Test that all 71 unit lines are mapped"""
        self.assertEqual(len(MCP_PDU_MAP), 71)
        
        # Check all positions 0-70 are present
        for i in range(71):
            self.assertIn(i, MCP_PDU_MAP)
            
    def test_mcp_map_addresses(self):
        """Test that MCP addresses are valid"""
        valid_addresses = [0x27, 0x26, 0x25, 0x24, 0x23, 0x22]
        
        for pos, (addr, pin) in MCP_PDU_MAP.items():
            self.assertIn(addr, valid_addresses)
            self.assertGreaterEqual(pin, 0)
            self.assertLessEqual(pin, 15)
            
    def test_mcp_map_pin_distribution(self):
        """Test that pins are distributed across MCP boards"""
        addr_counts = {}
        
        for pos, (addr, pin) in MCP_PDU_MAP.items():
            addr_counts[addr] = addr_counts.get(addr, 0) + 1
            
        # Check that we're using all 6 boards
        self.assertEqual(len(addr_counts), 6)


@patch('mcp_manager.MCP23017', MockMCP23017)
class TestMcpManager(unittest.TestCase):
    """Test MCP Manager with mocked hardware"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state_manager = PduStateManager()
        self.mcp_manager = McpManager(self.state_manager, poll_interval=0.01)
        
    def tearDown(self):
        """Clean up"""
        if self.mcp_manager:
            self.mcp_manager.stop()
            
    def test_mcp_manager_initialization(self):
        """Test MCP manager initializes all boards"""
        self.assertEqual(len(self.mcp_manager.mcp_boards), 6)
        
        # Check all expected addresses are initialized
        expected_addresses = [0x27, 0x26, 0x25, 0x24, 0x23, 0x22]
        for addr in expected_addresses:
            self.assertIn(addr, self.mcp_manager.mcp_boards)
            
    def test_set_unit_line_on(self):
        """Test turning on a unit line"""
        # Turn on unit line 0 (should be MCP 0x27, pin 0)
        self.mcp_manager.set_unit_line(0, True)
        
        # Check that the pin is LOW (ON)
        mcp_board = self.mcp_manager.mcp_boards[0x27]
        self.assertEqual(mcp_board.get_pin_level(0), 0x00)  # LOW = ON
        
    def test_set_unit_line_off(self):
        """Test turning off a unit line"""
        # First turn on
        self.mcp_manager.set_unit_line(0, True)
        # Then turn off
        self.mcp_manager.set_unit_line(0, False)
        
        # Check that the pin is HIGH (OFF)
        mcp_board = self.mcp_manager.mcp_boards[0x27]
        self.assertEqual(mcp_board.get_pin_level(0), 0xFF)  # HIGH = OFF
        
    def test_get_unit_line_state(self):
        """Test reading unit line state"""
        # Turn on unit line 5
        self.mcp_manager.set_unit_line(5, True)
        
        # Read state
        state = self.mcp_manager.get_unit_line_state(5)
        self.assertTrue(state)
        
        # Turn off
        self.mcp_manager.set_unit_line(5, False)
        state = self.mcp_manager.get_unit_line_state(5)
        self.assertFalse(state)
        
    def test_multiple_unit_lines(self):
        """Test controlling multiple unit lines"""
        # Turn on lines 0, 5, 10, 20
        for line in [0, 5, 10, 20]:
            self.mcp_manager.set_unit_line(line, True)
            
        # Verify all are on
        for line in [0, 5, 10, 20]:
            self.assertTrue(self.mcp_manager.get_unit_line_state(line))
            
        # Turn off line 5
        self.mcp_manager.set_unit_line(5, False)
        
        # Verify states
        self.assertTrue(self.mcp_manager.get_unit_line_state(0))
        self.assertFalse(self.mcp_manager.get_unit_line_state(5))
        self.assertTrue(self.mcp_manager.get_unit_line_state(10))
        
    def test_invalid_unit_line(self):
        """Test that invalid unit line raises error"""
        with self.assertRaises(ValueError):
            self.mcp_manager.set_unit_line(71, True)  # Max is 70
            
        with self.assertRaises(ValueError):
            self.mcp_manager.set_unit_line(-1, True)
            
    def test_get_switch_positions(self):
        """Test parsing unit line states into switch positions"""
        pdu_n = self.state_manager.get_pdu_state(0x65)
        
        # Set first 3 high power heaters ON
        pdu_n.unit_line_states.high_pw_heater_en_sel = 0b111
        
        pos_on, pos_off = self.mcp_manager._get_switch_positions(pdu_n.unit_line_states)
        
        # First 3 positions should be ON
        self.assertIn(0, pos_on)
        self.assertIn(1, pos_on)
        self.assertIn(2, pos_on)
        
        # Position 3 should be OFF
        self.assertIn(3, pos_off)
        
    def test_unit_line_categories(self):
        """Test that all unit line categories are processed correctly"""
        pdu_n = self.state_manager.get_pdu_state(0x65)
        
        # Set various categories
        pdu_n.unit_line_states.high_pw_heater_en_sel = 0xFF  # 8 bits
        pdu_n.unit_line_states.reaction_wheel_en_sel = 0b1111  # 4 bits
        
        pos_on, pos_off = self.mcp_manager._get_switch_positions(pdu_n.unit_line_states)
        
        # Should have some ON positions
        self.assertGreater(len(pos_on), 0)
        # Should have some OFF positions
        self.assertGreater(len(pos_off), 0)


class TestMcpIntegration(unittest.TestCase):
    """Integration tests for MCP manager with state manager"""
    
    @patch('mcp_manager.MCP23017', MockMCP23017)
    def test_state_change_triggers_hardware_update(self):
        """Test that changing PDU state triggers MCP hardware update"""
        state_manager = PduStateManager()
        mcp_manager = McpManager(state_manager, poll_interval=0.01)
        
        try:
            # Start monitoring
            mcp_manager.start()
            
            # Change PDU state to OPERATE
            pdu_n = state_manager.get_pdu_state(0x65)
            pdu_n.pdu_status.PduState = 2  # OPERATE state
            
            # Turn on some unit lines
            pdu_n.unit_line_states.high_pw_heater_en_sel = 0b11
            
            # Give time for monitoring thread to process
            import time
            time.sleep(0.1)
            
            # Check that hardware was updated
            self.assertTrue(mcp_manager.get_unit_line_state(0))
            self.assertTrue(mcp_manager.get_unit_line_state(1))
            
        finally:
            mcp_manager.stop()


if __name__ == '__main__':
    unittest.main()
