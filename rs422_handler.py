"""
RS422 Handler Class
Handles RS422 serial communication for PDU emulator mode
"""
import time
import serial
import json
import logging
from threading import Thread, Event

try:
    from pdu_packetization import PduPacket, encode_pdu_packet, decode_pdu_packet, PACKETIZATION_AVAILABLE
    if not PACKETIZATION_AVAILABLE:
        raise ImportError("PDU packetization C library not available")
except ImportError as e:
    raise ImportError(f"RS422 handler requires pdu_packetization module: {e}")

import pdu

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


class RS422Handler:
    """RS422 Serial Communication Handler"""
    
    PDU_COMMANDS = {
        0: "Invalid",
        1: "ObcHeartBeat",
        2: "GetPduStatus",
        3: "AddrUloadStart",
        4: "AddrUloadData",
        5: "AddrUloadAbort",
        6: "AddrDloadRqst",
        7: "AddrDAcknowledge",
        8: "PduGoLoad",
        9: "PduGoSafe",
        10: "PduGoOperate",
        11: "SetUnitPwLines",
        12: "ResetUnitPwLines",
        13: "OverwriteUnitPwLines",
        14: "GetUnitLineStates",
        15: "GetRawMeasurements",
        16: "GetConvertedMeasurements"
    }
    
    def __init__(self, port: str, baudrate: int, state_manager, apid: int = 0x65):
        """Initialize RS422 handler"""
        self.port = port
        self.baudrate = baudrate
        self.state_manager = state_manager
        self.apid = apid
        self.serial_port = None
        self.running = Event()
        self.thread = None
        
    def connect(self):
        """Connect to RS422 serial port"""
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1.0
            )
            self.serial_port.flushInput()
            self.serial_port.flushOutput()
            LOGGER.info(f"RS422 connected: {self.port} @ {self.baudrate} baud")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to connect RS422: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from RS422 serial port"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            LOGGER.info("RS422 disconnected")
    
    def start(self):
        """Start RS422 listener thread"""
        if not self.serial_port or not self.serial_port.is_open:
            if not self.connect():
                return False
        
        self.running.set()
        self.thread = Thread(target=self._listener_loop, daemon=True)
        self.thread.start()
        LOGGER.info("RS422 listener started")
        return True
    
    def stop(self):
        """Stop RS422 listener thread"""
        self.running.clear()
        if self.thread:
            self.thread.join(timeout=2.0)
        self.disconnect()
        LOGGER.info("RS422 listener stopped")
    
    def _listener_loop(self):
        """Main RS422 listener loop"""
        while self.running.is_set():
            try:
                frame = self._read_frame()
                if frame:
                    self._process_frame(frame)
            except Exception as e:
                LOGGER.error(f"RS422 listener error: {e}")
                time.sleep(0.1)
    
    def _read_frame(self):
        """Read complete RS422 frame from serial port"""
        try:
            # Look for start byte (0x55)
            start_byte = self.serial_port.read(1)
            if not start_byte or start_byte[0] != 0x55:
                return None
            
            frame = bytearray(start_byte)
            
            # Read until end byte (0x55)
            while self.running.is_set():
                byte = self.serial_port.read(1)
                if not byte:
                    break
                    
                frame.extend(byte)
                
                # Check for end byte
                if byte[0] == 0x55 and len(frame) > 1:
                    LOGGER.debug(f"RS422 RX: {frame.hex()}")
                    return bytes(frame)
            
            return None
            
        except Exception as e:
            LOGGER.error(f"RS422 read error: {e}")
            return None
    
    def _process_frame(self, frame: bytes):
        """Process received RS422 frame"""
        try:
            # Decode RS422 frame
            decoded_packet = decode_pdu_packet(frame)
            message_id = decoded_packet.message_id
            logical_unit_id = decoded_packet.logical_unit_id
            payload = list(decoded_packet.payload)
            
            # Get command name
            command_name = self.PDU_COMMANDS.get(message_id, "Unknown")
            LOGGER.info(f"RS422 Command: {command_name} (MID: {message_id}, LID: {logical_unit_id})")
            
            # Convert to JSON command format
            json_command = self._convert_to_json(command_name, logical_unit_id, payload)
            LOGGER.info(f"OBC to SEMSIM (RS422): {json_command}")
            
            # Process command
            response = self._process_command(json_command, message_id, logical_unit_id)
            
            # Send response back via RS422
            if response:
                self._send_response(response, message_id, logical_unit_id)
                
        except Exception as e:
            LOGGER.error(f"RS422 frame processing error: {e}")
    
    def _convert_to_json(self, command_name: str, logical_unit_id: int, payload: list) -> dict:
        """Convert RS422 command to JSON format"""
        try:
            # Convert payload bytes to string and parse JSON
            payload_bytes = bytes(payload)
            payload_str = payload_bytes.decode('utf-8')
            json_data = json.loads(payload_str)
            LOGGER.info(f"[RS422] Decoded JSON payload: {json_data}")
            return json_data
        except Exception as e:
            LOGGER.warning(f"[RS422] Failed to decode JSON payload: {e}, falling back to binary parsing")
            
            # Fallback to binary parsing for non-JSON payloads
            if command_name == "ObcHeartBeat":
                heartbeat = payload[0] if len(payload) > 0 else 0
                LOGGER.info(f"[RS422] Extracted heartbeat from binary payload: {heartbeat}")
                return {"ObcHeartBeat": {"HeartBeat": heartbeat}}
            
            elif command_name == "GetPduStatus":
                return {"GetPduStatus": {}}
            
            elif command_name == "PduGoLoad":
                return {"PduGoLoad": {}}
            
            elif command_name == "PduGoSafe":
                return {"PduGoSafe": {}}
            
            elif command_name == "PduGoOperate":
                return {"PduGoOperate": {}}
            
            elif command_name == "SetUnitPwLines":
                parameters = payload[0] if len(payload) > 0 else 0
                return {"SetUnitPwLines": {"LogicUnitId": logical_unit_id, "Parameters": parameters}}
            
            elif command_name == "ResetUnitPwLines":
                parameters = payload[0] if len(payload) > 0 else 0
                return {"ResetUnitPwLines": {"LogicUnitId": logical_unit_id, "Parameters": parameters}}
            
            elif command_name == "OverwriteUnitPwLines":
                parameters = payload[0] if len(payload) > 0 else 0
                return {"OverwriteUnitPwLines": {"LogicUnitId": logical_unit_id, "Parameters": parameters}}
            
            elif command_name == "GetUnitLineStates":
                return {"GetUnitLineStates": {}}
            
            elif command_name == "GetRawMeasurements":
                return {"GetRawMeasurements": {"LogicUnitId": logical_unit_id}}
            
            elif command_name == "GetConvertedMeasurements":
                return {"GetConvertedMeasurements": {"LogicUnitId": logical_unit_id}}
            
            else:
                LOGGER.warning(f"Unknown RS422 command: {command_name}")
                return {}

    def _process_command(self, json_command: dict, message_id: int, logical_unit_id: int):
        """Process command and generate response"""
        command_name = list(json_command.keys())[0] if json_command else None
        if not command_name:
            return None
        
        params = json_command[command_name]
        
        try:
            # Process command using PDU functions
            if command_name == "ObcHeartBeat":
                response_json = pdu.ObcHeartBeat(json_command, self.apid, self.state_manager)
                return json.loads(response_json)
            
            elif command_name == "GetPduStatus":
                response_json = pdu.GetPduStatus(params, self.apid, self.state_manager)
                return json.loads(response_json)
            
            elif command_name == "PduGoLoad":
                pdu.PduGoTo(command_name, self.apid, self.state_manager)
                response_json, _, _ = pdu.GetMsgAcknowledgement(json_command, self.apid, self.state_manager)
                return response_json
            
            elif command_name == "PduGoSafe":
                pdu.PduGoTo(command_name, self.apid, self.state_manager)
                response_json, _, _ = pdu.GetMsgAcknowledgement(json_command, self.apid, self.state_manager)
                return response_json
            
            elif command_name == "PduGoOperate":
                pdu.PduGoTo(command_name, self.apid, self.state_manager)
                response_json, _, _ = pdu.GetMsgAcknowledgement(json_command, self.apid, self.state_manager)
                return response_json
            
            elif command_name == "SetUnitPwLines":
                pdu.SetUnitPwLines(json_command, self.apid, self.state_manager)
                response_json, _, _ = pdu.GetMsgAcknowledgement(json_command, self.apid, self.state_manager)
                return response_json
            
            elif command_name == "ResetUnitPwLines":
                pdu.ResetUnitPwLines(json_command, self.apid, self.state_manager)
                response_json, _, _ = pdu.GetMsgAcknowledgement(json_command, self.apid, self.state_manager)
                return response_json
            
            elif command_name == "OverwriteUnitPwLines":
                pdu.OverwriteUnitPwLines(json_command, self.apid, self.state_manager)
                response_json, _, _ = pdu.GetMsgAcknowledgement(json_command, self.apid, self.state_manager)
                return response_json
            
            elif command_name == "GetUnitLineStates":
                response_json = pdu.GetUnitLineStates(params, self.apid, self.state_manager)
                return json.loads(response_json)
            
            elif command_name == "GetRawMeasurements":
                response_json = pdu.GetRawMeasurements(params, self.apid, self.state_manager)
                return json.loads(response_json)
            
            elif command_name == "GetConvertedMeasurements":
                response_json = pdu.GetConvertedMeasurements(params, self.apid, self.state_manager)
                return json.loads(response_json)
            
            else:
                LOGGER.warning(f"Unhandled RS422 command: {command_name}")
                return None
                
        except ValueError as e:
            LOGGER.error(f"RS422 command validation error: {e}")
            unit = self.state_manager.get_unit(self.apid)
            unit.msg_acknowledgement.RequestedMsgId = command_name
            unit.msg_acknowledgement.PduReturnCode = 1  # Error
            return unit.msg_acknowledgement.to_dict()
        
        except Exception as e:
            LOGGER.error(f"RS422 command processing error: {e}")
            return None
    
    def _send_response(self, response_dict: dict, message_id: int, logical_unit_id: int):
        """Send response back via RS422"""
        try:
            # Convert response to JSON bytes
            response_json = json.dumps(response_dict)
            payload = list(response_json.encode('utf-8'))
            
            # Create RS422 frame
            packet = PduPacket()
            packet.message_id = message_id
            packet.logical_unit_id = logical_unit_id
            for byte in payload:
                packet.payload.append(byte)
            
            frame = encode_pdu_packet(packet)
            
            # Send frame
            self.serial_port.write(frame)
            LOGGER.debug(f"RS422 TX: {frame.hex()}")
            LOGGER.info(f"SEMSIM to OBC (RS422): {response_dict}")
            
        except Exception as e:
            LOGGER.error(f"RS422 send error: {e}")
