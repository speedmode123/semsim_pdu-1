"""
Telemetry/Telecommand Manager
Refactored to use PduStateManager and support hardware/simulator modes
"""
import time
import socket
import json
import logging
from threading import Thread
import struct

import pdu

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

# Hardware imports (optional, only for emulator mode)
try:
    import board
    import busio
    import digitalio
    from adafruit_mcp230xx.mcp23017 import MCP23017
    HARDWARE_AVAILABLE = True
except (ImportError, NotImplementedError) as e:
    HARDWARE_AVAILABLE = False
    LOGGER.warning(f"Hardware libraries not available - running in simulator mode only: {e}")


def configure_hardware():
    """Configure MCP hardware (only in emulator mode)"""
    if not HARDWARE_AVAILABLE:
        return None, None, None, None, None
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mcp = MCP23017(i2c, address=0x26)
        
        # Configure pins for reading pulses
        def configure_pin_read_pulse(pin):
            pin_obj = mcp.get_pin(pin)
            pin_obj.direction = digitalio.Direction.INPUT
            pin_obj.pull = digitalio.Pull.UP
            return pin_obj
        
        # Load pin configuration
        # Note: This would need the actual pin allocation file
        # For now, using placeholder pin numbers
        pdu_n_epc_on = configure_pin_read_pulse(0)
        pdu_n_epc_off = configure_pin_read_pulse(1)
        pdu_r_epc_on = configure_pin_read_pulse(2)
        pdu_r_epc_off = configure_pin_read_pulse(3)
        
        return mcp, pdu_n_epc_on, pdu_n_epc_off, pdu_r_epc_on, pdu_r_epc_off
    except Exception as e:
        LOGGER.error(f"Failed to configure hardware: {e}")
        return None, None, None, None, None


def send_converted_measurements(j_command_packet, apid, type, subtype, address, UDPServerSocket, state_manager, count):
    """Send periodic converted measurements"""
    serverAddressPort = ("host.docker.internal", 5005)
    UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    
    try:
        UDPServerSocket.connect(serverAddressPort)
    except:
        LOGGER.warning("Could not connect to periodic measurement endpoint")
        return
    
    while True:
        try:
            GetConvertedMeasurements = pdu.GetConvertedMeasurementsPeriodic(j_command_packet, apid, state_manager)
            GetConvertedMeasurements_L = json.loads(GetConvertedMeasurements)
            json_object = json.dumps(GetConvertedMeasurements_L)
            Response_GetConvertedMeasurements = SpacePacketCommand(count, json_object, apid, type, subtype+1)
            
            UDPServerSocket.sendall(Response_GetConvertedMeasurements)
            LOGGER.info(f"Send Period Measurement")
        except ConnectionError as e:
            break
        except Exception as e:
            LOGGER.error(f"Error sending periodic measurements: {e}")
            break
        time.sleep(1)


def tmtc_manager(state_manager, localIP, tclocalPort, hardware_mode=False):
    """Main TMTC manager - handles commands and responses"""
    UDPServerSocket = configurator(localIP, tclocalPort)
    
    # Configure hardware if in emulator mode
    pdu_n_status = 0
    pdu_r_status = 0
    hardware_pins = None
    
    if hardware_mode:
        mcp, pdu_n_epc_on, pdu_n_epc_off, pdu_r_epc_on, pdu_r_epc_off = configure_hardware()
        if mcp:
            hardware_pins = (pdu_n_epc_on, pdu_n_epc_off, pdu_r_epc_on, pdu_r_epc_off)
            LOGGER.info("Hardware configured successfully")
    
    threads = {}
    
    try:
        while True:
            # Check hardware status if in emulator mode
            if hardware_mode and hardware_pins:
                pdu_n_epc_on, pdu_n_epc_off, pdu_r_epc_on, pdu_r_epc_off = hardware_pins
                
                if not pdu_n_epc_on.value:
                    pdu_n_status = 1
                if not pdu_n_epc_off.value:
                    pdu_n_status = 0
                if not pdu_r_epc_on.value:
                    pdu_r_status = 1
                if not pdu_r_epc_off.value:
                    pdu_r_status = 0
            else:
                # In simulator mode, always enabled
                pdu_n_status = 1
                pdu_r_status = 1
            
            if pdu_n_status or pdu_r_status:
                customize_listening(UDPServerSocket, threads, state_manager)
                
    except Exception as e:
        time.sleep(1)
        UDPServerSocket.close()
        raise e


def cmd_processing(j_command_packet, apid, type, subtype, address, UDPServerSocket, state_manager, count):
    """Process incoming commands"""
    t = Thread(target=send_converted_measurements, args=(j_command_packet, apid, type, subtype, address, UDPServerSocket, state_manager, count,))
    
    for cmd, param_list in j_command_packet.items():
        if cmd == "ObcHeartBeat":
            PduHeartBeat = pdu.ObcHeartBeat(j_command_packet, apid, state_manager)
            json_object = json.dumps(json.loads(PduHeartBeat))
            Response_PduHeartBeat = SpacePacketCommand(count, json_object, apid, type, subtype+1)
            UDPServerSocket.sendto(Response_PduHeartBeat, address)
            LOGGER.info(f"SEMSIM to OBC: {PduHeartBeat}")
            
        elif cmd == "GetPduStatus":
            PduStatus = pdu.GetPduStatus(param_list, apid, state_manager)
            json_object = json.dumps(json.loads(PduStatus))
            Response_PduStatus = SpacePacketCommand(count, json_object, apid, type, subtype+1)
            UDPServerSocket.sendto(Response_PduStatus, address)
            LOGGER.info(f"SEMSIM to OBC: {PduStatus}")
            
        elif cmd == "PduGoMaintenance":
            if t.is_alive():
                t.join()
            pdu.PduGoTo(cmd, apid, state_manager)
            
        elif cmd == "PduGoSafe":
            if t.is_alive():
                t.join()
            pdu.PduGoTo(cmd, apid, state_manager)
            
        elif cmd == "PduGoOperate":
            pdu.PduGoTo(cmd, apid, state_manager)
            if not t.is_alive():
                t.start()
                
        elif cmd == "SetUnitPwLines":
            pdu.SetUnitPwLines(j_command_packet, apid, state_manager)
            
        elif cmd == "GetUnitLineStates":
            PduUnitLineStates = pdu.GetUnitLineStates(param_list, apid, state_manager)
            json_object = json.dumps(json.loads(PduUnitLineStates))
            Response_PduUnitLineStates = SpacePacketCommand(count, json_object, apid, type, subtype+1)
            UDPServerSocket.sendto(Response_PduUnitLineStates, address)
            LOGGER.info(f"SEMSIM to OBC: {PduUnitLineStates}")
            
        elif cmd == "ResetUnitPwLines":
            pdu.ResetUnitPwLines(j_command_packet, apid, state_manager)
            
        elif cmd == "OverwriteUnitPwLines":
            pdu.OverwriteUnitPwLines(j_command_packet, apid, state_manager)
            
        elif cmd == "GetRawMeasurements":
            GetRawMeasurements = pdu.GetRawMeasurements(j_command_packet, apid, state_manager)
            GetRawMeasurements_L = json.loads(GetRawMeasurements)
            json_object = json.dumps(GetRawMeasurements_L)
            Response_GetRawMeasurements = SpacePacketCommand(count, json_object, apid, type, subtype+1)
            UDPServerSocket.sendto(Response_GetRawMeasurements, address)
            
        elif cmd == "GetConvertedMeasurements":
            GetConvertedMeasurements = pdu.GetConvertedMeasurements(j_command_packet, apid, state_manager)
            GetConvertedMeasurements_L = json.loads(GetConvertedMeasurements)
            json_object = json.dumps(GetConvertedMeasurements_L)
            Response_GetConvertedMeasurements = SpacePacketCommand(count, json_object, apid, type, subtype+1)
            UDPServerSocket.sendto(Response_GetConvertedMeasurements, address)
            
        else:
            LOGGER.info(f"OBC cmd_name: {cmd} Not Implemented")


def cmd_unloader(packet_data_field):
    """Unload command from packet"""
    command_packet = packet_data_field[12:]
    j_command_packet = json.loads(command_packet)
    return j_command_packet


def cmd_ack_generator(j_command_packet, apid, address, state_manager, UDPServerSocket):
    """Generate command acknowledgement"""
    for cmd, param_list in j_command_packet.items():
        LOGGER.info(f"CMD: {cmd}")
        
        # Commands that don't need ack
        if cmd in ["ObcHeartBeat", "GetUnitLineStates", "GetRawMeasurements", "GetPduStatus"]:
            continue
        
        try:
            MsgAcknowledgement, TYPE, SUBTYPE = pdu.GetMsgAcknowledgement(j_command_packet, apid, state_manager)
            json_object = json.dumps(MsgAcknowledgement)
            ack_command = SpacePacketCommand(0x02, json_object, apid, TYPE, SUBTYPE)
            UDPServerSocket.sendto(ack_command, address)
            LOGGER.info(f"SEMSIM to OBC: {MsgAcknowledgement}")
        except Exception as e:
            LOGGER.error(f"Failed to Create Ack SpacePacket: {e}")


def SpacePacketDecoder(buffer):
    """Decode CCSDS Space Packet"""
    try:
        packet_data_field = b''
        packet_type = (buffer[0] >> 4) & 0x01
        packet_sec_hdr_flag = (buffer[0] >> 3) & 0x01
        apid = ((buffer[0] & 0x07) << 8) + buffer[1]
        sequence_flags = buffer[2] >> 6
        packet_sequence_count = ((buffer[2] & 0x3F) << 8) + buffer[3]
        packet_version = buffer[0] >> 5
        packet_data_length = (buffer[4] << 8) + buffer[5] + 1
        packet_data_field += buffer[6:]
        type = buffer[7]
        subtype = buffer[8]
    except:
        LOGGER.error("Failed to decode SpacePacket")
        packet_data_field = {}
        apid = type = subtype = 0
    return packet_data_field, apid, type, subtype


def SpacePacketCommand(count, command, apid, type, subtype):
    """Create CCSDS Space Packet"""
    try:
        packet_dataframelength = len(bytes(command, 'utf-8'))
        tc_version = 0x00
        tc_type = 0x00
        tc_dfh_flag = 0x01
        tc_apid = apid
        tc_seq_flag = 0x03
        tc_seq_count = count
        data_field_header = [0x10, type, subtype, 0x00]
        data_pack_cuck = [0x2F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        data_field_header_frame = data_field_header + data_pack_cuck
        data_pack_data_field_header_frame = b''
        for p in data_field_header_frame:
            data_pack_data_field_header_frame += p.to_bytes(1, 'big')
        packet_dataheaderlength = len(data_pack_data_field_header_frame)
        packet_datalength = packet_dataheaderlength + packet_dataframelength - 1
        databytes = bytes([(tc_version << 5) + (tc_type << 4) + (tc_dfh_flag << 3) + (tc_apid >> 8), 
                          (tc_apid & 0xFF), 
                          (tc_seq_flag << 6) + (tc_seq_count >> 8), 
                          (tc_seq_count & 0xFF), 
                          (packet_datalength >> 8), 
                          (packet_datalength & 0xFF)])
        databytes += data_pack_data_field_header_frame
        databytes += bytes(command, 'utf-8')
        LOGGER.info(f"SEMSIM to OBC FRAME: {databytes}")
    except:
        databytes = b''
        LOGGER.error("Failed to Create SpacePacket")
    return databytes


def configurator(localIP, tclocalPort):
    """Configure UDP socket"""
    UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPServerSocket.bind((localIP, tclocalPort))
    return UDPServerSocket


def customize_listening(UDPServerSocket, threads, state_manager):
    """Listen for incoming commands"""
    bufferSize = 4096
    count = 0
    byteAddressPair = UDPServerSocket.recvfrom(bufferSize)
    message = byteAddressPair[0]
    address = byteAddressPair[1]
    
    if message:
        clientIP = "Client IP Address:{}".format(address)
        LOGGER.info(f"{clientIP}")
        
        data, apid, type, subtype = SpacePacketDecoder(message)
        j_command_packet = cmd_unloader(data)
        LOGGER.info(f"OBC to SEMSIM: {j_command_packet}")
        
        cmd_ack_generator(j_command_packet, apid, address, state_manager, UDPServerSocket)
        cmd_processing(j_command_packet, apid, type, subtype, address, UDPServerSocket, state_manager, count)
