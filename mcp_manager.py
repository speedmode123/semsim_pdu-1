"""
MCP Manager - Controls MCP23017 GPIO expanders for PDU unit line hardware control
Maps 71 PDU unit lines to specific MCP addresses and GPIO pins
"""
import time
import logging
import json
from threading import Thread, Event
from typing import Optional
from mcp import GPIO_PINS, MCP23017, PIN_LEVELS, PIN_DIRECTIONS
from pdu_state import PduStateManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

MCP_PDU_MAP = {
    0: (0x27, 0), 1: (0x27, 1), 2: (0x27, 2), 3: (0x27, 3),
    4: (0x27, 4), 5: (0x27, 5), 6: (0x27, 6), 7: (0x27, 7),
    8: (0x27, 8), 9: (0x27, 9), 10: (0x27, 10), 11: (0x27, 11),
    12: (0x27, 12), 13: (0x27, 13), 14: (0x27, 14), 15: (0x27, 15),
    16: (0x26, 0), 17: (0x26, 1), 18: (0x26, 2), 19: (0x26, 3),
    20: (0x26, 4), 21: (0x26, 5), 22: (0x26, 6), 23: (0x26, 7),
    24: (0x25, 0), 25: (0x25, 1), 26: (0x25, 2), 27: (0x25, 3),
    28: (0x25, 4), 29: (0x25, 5), 30: (0x25, 6), 31: (0x25, 7),
    32: (0x25, 8), 33: (0x25, 9), 34: (0x25, 10), 35: (0x25, 11),
    36: (0x25, 12), 37: (0x25, 13), 38: (0x25, 14), 39: (0x25, 15),
    40: (0x24, 0), 41: (0x24, 1), 42: (0x24, 2), 43: (0x24, 3),
    44: (0x24, 4), 45: (0x24, 5), 46: (0x24, 6), 47: (0x24, 7),
    48: (0x23, 0), 49: (0x23, 1), 50: (0x23, 2), 51: (0x23, 3),
    52: (0x23, 4), 53: (0x23, 5), 54: (0x23, 6), 55: (0x23, 7),
    56: (0x23, 8), 57: (0x23, 9), 58: (0x23, 10), 59: (0x23, 11),
    60: (0x23, 12), 61: (0x23, 13), 62: (0x23, 14), 63: (0x23, 15),
    64: (0x22, 0), 65: (0x22, 1), 66: (0x22, 2), 67: (0x22, 3),
    68: (0x22, 4), 69: (0x22, 5), 70: (0x22, 6)
}


class McpManager:
    """
    Manages MCP23017 GPIO expanders for PDU unit line control.
    Monitors PDU state and controls hardware GPIO pins accordingly.
    """
    
    def __init__(self, state_manager: PduStateManager, poll_interval: float = 0.1):
        """
        Initialize MCP Manager
        
        Args:
            state_manager: PDU state manager instance
            poll_interval: How often to check for state changes (seconds)
        """
        self.state_manager = state_manager
        self.poll_interval = poll_interval
        self.running = Event()
        self.thread: Optional[Thread] = None
        
        self.mcp_addresses = [0x27, 0x26, 0x25, 0x24, 0x23, 0x22]
        self.mcp_boards = {}
        
        # Track previous state to detect changes
        self.prev_pos_to_on = []
        self.prev_pos_to_off = []
        
        LOGGER.info("Initializing MCP23017 boards...")
        self._initialize_mcp_boards()
        
    def _initialize_mcp_boards(self):
        """Initialize all MCP23017 boards and set all pins to OUTPUT mode, HIGH (OFF)"""
        for mcp_addr in self.mcp_addresses:
            try:
                mcp_board = MCP23017(mcp_addr)
                mcp_board.set_default_config()
                mcp_board.set_all_output()
                # Set all pins HIGH (unit lines OFF)
                for pin in range(16):
                    mcp_board.set_pin_level(pin, PIN_LEVELS.HIGH.value)
                self.mcp_boards[mcp_addr] = mcp_board
                LOGGER.info(f"Initialized MCP23017 at address 0x{mcp_addr:02X}")
            except Exception as e:
                LOGGER.error(f"Failed to initialize MCP23017 at 0x{mcp_addr:02X}: {e}")
                raise
                
    def start(self):
        """Start the MCP manager monitoring thread"""
        if self.thread is not None and self.thread.is_alive():
            LOGGER.warning("MCP manager already running")
            return
            
        self.running.set()
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        LOGGER.info("MCP manager started")
        
    def stop(self):
        """Stop the MCP manager monitoring thread"""
        if self.thread is None:
            return
            
        LOGGER.info("Stopping MCP manager...")
        self.running.clear()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        LOGGER.info("MCP manager stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop - checks PDU state and updates MCP pins"""
        while self.running.is_set():
            try:
                self._update_unit_lines()
                time.sleep(self.poll_interval)
            except Exception as e:
                LOGGER.error(f"Error in MCP monitor loop: {e}")
                time.sleep(1.0)
                
    def _update_unit_lines(self):
        """Check PDU state and update MCP GPIO pins for unit lines"""
        pos_to_on = []
        pos_to_off = []
        
        for pdu_id in [0x65, 0x66]:
            pdu_state = self.state_manager.get_pdu_state(pdu_id)
            
            # Only process if PDU is not in OFF (0) or INIT (1) state
            if pdu_state.pdu_status.pdu_state not in [0, 1]:
                unit_line_states = pdu_state.unit_line_states
                new_on, new_off = self._get_switch_positions(unit_line_states)
                pos_to_on.extend(new_on)
                pos_to_off.extend(new_off)
        
        # Detect changes and update hardware
        pos_to_on_sorted = sorted(set(pos_to_on))
        pos_to_off_sorted = sorted(set(pos_to_off))
        
        if pos_to_on_sorted != sorted(self.prev_pos_to_on):
            self.prev_pos_to_on = pos_to_on_sorted
            self._set_pins_on(pos_to_on_sorted)
            
        if pos_to_off_sorted != sorted(self.prev_pos_to_off):
            self.prev_pos_to_off = pos_to_off_sorted
            self._set_pins_off(pos_to_off_sorted)
            
    def _get_switch_positions(self, unit_line_states) -> tuple[list[int], list[int]]:
        """
        Parse unit line states and determine which positions should be ON/OFF
        
        Returns:
            Tuple of (positions_to_turn_on, positions_to_turn_off)
        """
        pos_to_on = []
        pos_to_off = []
        idx = 0
        
        # High Power Heaters (18 lines)
        htr_hp = list(format(unit_line_states.high_pw_heater_en_sel, '024b'))
        htr_hp.reverse()
        for bit in htr_hp[0:18]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # Low Power Heaters (22 lines)
        htr_lp = list(format(unit_line_states.low_pw_heater_en_sel, '024b'))
        htr_lp.reverse()
        for bit in htr_lp[0:22]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # Avionics Load (2 lines)
        av_load = list(format(unit_line_states.avionic_load_en_sel, '016b'))
        av_load.reverse()
        for bit in av_load[0:2]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # HDRM (12 lines)
        hdrm_load = list(format(unit_line_states.hdrm_en_sel, '016b'))
        hdrm_load.reverse()
        for bit in hdrm_load[0:12]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # Reaction Wheels (4 lines)
        rw_load = list(format(unit_line_states.reaction_wheel_en_sel, '016b'))
        rw_load.reverse()
        for bit in rw_load[0:4]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # Propulsion (2 lines)
        prop_load = list(format(unit_line_states.prop_en_sel, '008b'))
        prop_load.reverse()
        for bit in prop_load[0:2]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # Isolated LDO (6 lines)
        stm_load = list(format(unit_line_states.isolated_ldo_en_sel, '016b'))
        stm_load.reverse()
        for bit in stm_load[0:6]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        # Isolated Power (3 lines)
        iso_load = list(format(unit_line_states.isolated_pw_en_sel, '008b'))
        iso_load.reverse()
        for bit in iso_load[0:3]:
            if int(bit) == 1:
                pos_to_on.append(idx)
            else:
                pos_to_off.append(idx)
            idx += 1
            
        return pos_to_on, pos_to_off
        
    def _set_pins_on(self, positions: list[int]):
        """Turn ON unit lines (set GPIO pins LOW)"""
        if not positions:
            return
            
        LOGGER.info(f"Turning ON unit lines: {positions}")
        for pos in positions:
            if pos not in MCP_PDU_MAP:
                LOGGER.warning(f"Invalid unit line position: {pos}")
                continue
                
            mcp_addr, pin = MCP_PDU_MAP[pos]
            try:
                mcp_board = self.mcp_boards.get(mcp_addr)
                if mcp_board is None:
                    LOGGER.error(f"MCP board at 0x{mcp_addr:02X} not initialized")
                    continue
                    
                # Only change if currently HIGH (OFF)
                if mcp_board.get_pin_level(pin) == PIN_LEVELS.HIGH.value:
                    mcp_board.set_pin_level(pin, PIN_LEVELS.LOW.value)
                    LOGGER.debug(f"Unit line {pos} ON (MCP 0x{mcp_addr:02X} pin {pin})")
            except Exception as e:
                LOGGER.error(f"Failed to turn ON unit line {pos}: {e}")
                
    def _set_pins_off(self, positions: list[int]):
        """Turn OFF unit lines (set GPIO pins HIGH)"""
        if not positions:
            return
            
        LOGGER.info(f"Turning OFF unit lines: {positions}")
        for pos in positions:
            if pos not in MCP_PDU_MAP:
                LOGGER.warning(f"Invalid unit line position: {pos}")
                continue
                
            mcp_addr, pin = MCP_PDU_MAP[pos]
            try:
                mcp_board = self.mcp_boards.get(mcp_addr)
                if mcp_board is None:
                    LOGGER.error(f"MCP board at 0x{mcp_addr:02X} not initialized")
                    continue
                    
                # Only change if currently LOW (ON)
                if mcp_board.get_pin_level(pin) == PIN_LEVELS.LOW.value:
                    mcp_board.set_pin_level(pin, PIN_LEVELS.HIGH.value)
                    LOGGER.debug(f"Unit line {pos} OFF (MCP 0x{mcp_addr:02X} pin {pin})")
            except Exception as e:
                LOGGER.error(f"Failed to turn OFF unit line {pos}: {e}")
                
    def set_unit_line(self, position: int, state: bool):
        """
        Manually set a specific unit line state
        
        Args:
            position: Unit line position (0-70)
            state: True for ON, False for OFF
        """
        if position not in MCP_PDU_MAP:
            raise ValueError(f"Invalid unit line position: {position}")
            
        if state:
            self._set_pins_on([position])
        else:
            self._set_pins_off([position])
            
    def get_unit_line_state(self, position: int) -> bool:
        """
        Get current hardware state of a unit line
        
        Args:
            position: Unit line position (0-70)
            
        Returns:
            True if ON (LOW), False if OFF (HIGH)
        """
        if position not in MCP_PDU_MAP:
            raise ValueError(f"Invalid unit line position: {position}")
            
        mcp_addr, pin = MCP_PDU_MAP[position]
        mcp_board = self.mcp_boards.get(mcp_addr)
        if mcp_board is None:
            raise RuntimeError(f"MCP board at 0x{mcp_addr:02X} not initialized")
            
        # LOW = ON, HIGH = OFF
        return mcp_board.get_pin_level(pin) == PIN_LEVELS.LOW.value
        
    def shutdown(self):
        """Shutdown MCP manager and turn off all unit lines"""
        self.stop()
        LOGGER.info("Turning off all unit lines...")
        for mcp_addr, mcp_board in self.mcp_boards.items():
            try:
                for pin in range(16):
                    mcp_board.set_pin_level(pin, PIN_LEVELS.HIGH.value)
                LOGGER.info(f"All pins set HIGH on MCP 0x{mcp_addr:02X}")
            except Exception as e:
                LOGGER.error(f"Error shutting down MCP 0x{mcp_addr:02X}: {e}")
