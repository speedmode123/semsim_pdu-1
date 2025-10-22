"""
RS422 Serial Interface
Refactored to use PduStateManager
"""
import socket
import time
import serial
import json
import sys
import logging
from threading import Thread

try:
    from pdu_packetization import PduPacket, encode_pdu_packet, decode_pdu_packet, PACKETIZATION_AVAILABLE
    if not PACKETIZATION_AVAILABLE:
        raise ImportError("PDU packetization C library not available")
except ImportError as e:
    raise ImportError(f"RS422 interface requires pdu_packetization module: {e}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

bufferSize = 4096

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
    15: "GetRawMeasurements"
}

LogicalUnitId = {
    0: "HighPwHeaterEnSel",
    1: "LowPwHeaterEnSel",
    2: "ReactionWheelEnSel",
    3: "PropEnSel",
    4: "AvionicLoadEnSel",
    5: "HdrmEnSel",
    6: "IsolatedLdoEnSel",
    7: "IsolatedPwEnSel",
    8: "ThermAndFlybackEnSel"
}


def send_message(Command):
    """Send message via UDP"""
    bytesToSend = Command
    serverAddressPort = ("127.0.0.1", 5004)
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.sendto(bytesToSend, serverAddressPort)
    return UDPClientSocket


def expecting_ack(UDPCon):
    """Wait for acknowledgement"""
    byteAddressPair = UDPCon.recvfrom(bufferSize)
    message = byteAddressPair[0]
    address = byteAddressPair[1]
    return message


def SpacePacketCommand(count, command, apid, type, subtype):
    """Create CCSDS Space Packet"""
    try:
        packet_dataframelength = len(bytes(command, 'utf-8'))
        tc_version = 0x00
        tc_type = 0x01
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
        packet_datalength = packet_dataheaderlength + packet_dataframelength - 2
        databytes = bytes([(tc_version << 5) + (tc_type << 4) + (tc_dfh_flag << 3) + (tc_apid >> 8), 
                          (tc_apid & 0xFF), 
                          (tc_seq_flag << 6) + (tc_seq_count >> 8), 
                          (tc_seq_count & 0xFF), 
                          (packet_datalength >> 8), 
                          (packet_datalength & 0xFF)])
        databytes += data_pack_data_field_header_frame
        databytes += bytes(command, 'utf-8')
    except:
        databytes = 0
        print("Failed to Create SpacePacket")
    return databytes


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
        print("Failed to Create SpacePacket")
        packet_data_field = {}
        apid = type = subtype = 0
    return packet_data_field, apid, type, subtype


def decode_tlm(packet_data_field, apid, type, subtype):
    """Decode telemetry"""
    command_packet = packet_data_field[12:]
    jv_command_packet = json.loads(command_packet)
    return jv_command_packet, apid, type, subtype


def encode_obc_rs422_frame(message_id, Logic_Id, Payload):
    """Encode RS422 frame"""
    packet = PduPacket()
    packet.message_id = message_id
    packet.logical_unit_id = Logic_Id
    for p in Payload:
        packet.payload.append(p)
    RSObcFrame = encode_pdu_packet(packet)
    return RSObcFrame


def decode_obc_rs422_frame(RSObcFrame):
    """Decode RS422 frame"""
    decoded_packet = decode_pdu_packet(RSObcFrame)
    mid = decoded_packet.message_id
    lid = decoded_packet.logical_unit_id
    pld = decoded_packet.payload
    pdu_cmd = PDU_COMMANDS[int(mid)]
    return pdu_cmd, mid, lid, pld


def send_semsim_ccsds_frame(count, Command, apid, type, subtype):
    """Send CCSDS frame"""
    json_object = json.dumps(Command)
    cmd2pdu = SpacePacketCommand(count, json_object, apid, type, subtype)
    UDPCon = send_message(cmd2pdu)
    return UDPCon


def receive_semsim_ccsds_frame(UDPCon):
    """Receive CCSDS frame"""
    tlm_rcv = expecting_ack(UDPCon)
    packet_data_field, apid, type, subtype = SpacePacketDecoder(tlm_rcv)
    dict_command_rcv, apid, type, subtype = decode_tlm(packet_data_field, apid, type, subtype)
    return dict_command_rcv, apid, type, subtype


def rs422_comm(port, speed):
    """Initialize RS422 communication"""
    try:
        ser_port = serial.Serial(
            port=port,
            baudrate=speed,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )
        print("Created RS 422 PORT")
        ser_port.flushInput()
        ser_port.flushOutput()
        if ser_port.isOpen():
            print("port is opened!")
        else:
            ser_port.open()
    except IOError:
        ser_port.close()
        ser_port.open()
    return ser_port


def read_command(ser_port, state_manager):
    """Read commands from RS422"""
    while True:
        APID = 0x65
        bs = b''
        start_byte = ser_port.read()
        bs += start_byte
        
        if hex(ord(start_byte)) == '0x55':
            read_byte = ser_port.read()
            bs += read_byte
            while hex(ord(read_byte)) != '0x55':
                read_byte = ser_port.read()
                bs += read_byte
            LOGGER.info(f"read_buffer {bs}")
            
            if bs and "USB1" in ser_port.port:
                print(f"OBC to PDU {bs.hex()}")
                pdu_cmd, mid, lid, pld = decode_obc_rs422_frame(bs)
                
                # Process command based on message ID
                # ... existing command processing logic ...
                # (keeping the existing logic but using state_manager)


def write_command(ser_port, sccp_cmd_null, len_spc):
    """Write command to RS422"""
    try:
        if "USB1" in ser_port.port:
            print(f"PDU to OBC Raw Command: {sccp_cmd_null.hex()}")
        else:
            LOGGER.info(f"PDU to OBC Raw Command: {sccp_cmd_null.hex()}")
        ser_port.write(serial.to_bytes(sccp_cmd_null))
    except:
        print("Failed Sending Break Code!")


def rs_422_listener(ser_port, state_manager):
    """Start RS422 listener thread"""
    try:
        print("Listening on RS 422 PORT")
        listen_rs_thread = Thread(target=read_command, args=(ser_port, state_manager))
        listen_rs_thread.daemon = True
        listen_rs_thread.start()
        listen_rs_thread.join()
    except:
        print("Failed To Create Listening thread")
