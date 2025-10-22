"""
PDU Packet Encoding/Decoding
Wrapper for C library with graceful fallback for simulator mode
"""
import ctypes
import sys
import logging

LOGGER = logging.getLogger(__name__)

MAX_PAYLOAD_SIZE = 255

# Try to load the C library for packet encoding/decoding
PACKETIZATION_AVAILABLE = False
pdu_packetization_lib = None

try:
    # Setup ctypes for PDU packet lib
    if sys.platform.startswith("win") and sys.maxsize > 2**32:
        pdu_packetization_lib = ctypes.cdll.LoadLibrary("resource/pdu_packetization.dll")
        PACKETIZATION_AVAILABLE = True
    elif sys.platform.startswith("lin") and sys.maxsize > 2**32:
        pdu_packetization_lib = ctypes.cdll.LoadLibrary("resource/pdu_packetization.so")
        PACKETIZATION_AVAILABLE = True
    else:
        LOGGER.warning(f"Platform {sys.platform} not supported for C library or not using 64-bit Python")
        
    if PACKETIZATION_AVAILABLE:
        pdu_packetization_lib.PS_HasNextByte.restype = ctypes.c_bool
        pdu_packetization_lib.PS_NextByte.restype = ctypes.c_ubyte
        pdu_packetization_lib.PD_Apply.restype = ctypes.c_int
        LOGGER.info("PDU packetization C library loaded successfully")
        
except (OSError, FileNotFoundError) as e:
    LOGGER.warning(f"PDU packetization C library not available: {e}")
    LOGGER.warning("RS422 interface will not be available - simulator mode only")
    PACKETIZATION_AVAILABLE = False
except Exception as e:
    LOGGER.warning(f"Unexpected error loading packetization library: {e}")
    PACKETIZATION_AVAILABLE = False


class PduPacketCStruct(ctypes.Structure):
    """C structure for PDU packet"""
    _fields_ = [('u8MessageAndLogicalUnitId', ctypes.c_ubyte),
                ('u8PayloadLength', ctypes.c_ubyte),
                ('au8Payload', ctypes.c_ubyte * MAX_PAYLOAD_SIZE)]


class PduPacketSerializerCStruct(ctypes.Structure):
    """C structure for packet serializer"""
    _fields_ = [('psPacket', ctypes.POINTER(PduPacketCStruct)),
                ('eState', ctypes.c_uint),
                ('u8Index', ctypes.c_ubyte),
                ('bHasPendingByte', ctypes.c_bool),
                ('u8PendingByte', ctypes.c_ubyte),
                ('u16Crc', ctypes.c_ushort)]


class PduPacketDeserializerCStruct(ctypes.Structure):
    """C structure for packet deserializer"""
    _fields_ = [('eState', ctypes.c_uint),
                ('u8Index', ctypes.c_ubyte),
                ('bStuffByte', ctypes.c_bool),
                ('u16CalculatedCrc', ctypes.c_ushort),
                ('u8ReceivedCrc0', ctypes.c_ubyte)]


class PduPacket:
    """Python representation of PDU packet"""
    def __init__(self):
        self.message_id = 0
        self.logical_unit_id = 0
        self.payload = []

    def __str__(self):
        return (f"Message ID: {self.message_id}, Logical Unit ID: {self.logical_unit_id} "
                f"\nPayload:{[hex(value) for value in self.payload]}")


def encode_pdu_packet(pdu_packet: PduPacket) -> bytes:
    """Encode PDU packet to bytes using C library"""
    if not PACKETIZATION_AVAILABLE:
        raise RuntimeError("PDU packetization C library not available")
    
    # Convert python PDU packet to c type for passing to lib
    c_packet = PduPacketCStruct()
    c_packet.u8MessageAndLogicalUnitId = (pdu_packet.message_id << 4) | pdu_packet.logical_unit_id
    c_packet.u8PayloadLength = len(pdu_packet.payload)
    c_packet.au8Payload = (ctypes.c_ubyte * MAX_PAYLOAD_SIZE)(*pdu_packet.payload)

    # Setup C serializer
    serializer_pointer = (PduPacketSerializerCStruct * 1)(PduPacketSerializerCStruct())
    packet_pointer = (PduPacketCStruct * 1)(c_packet)
    pdu_packetization_lib.PS_ResetSerializer(serializer_pointer, packet_pointer)

    # Setup python list for storing encoded values and call C lib functions to encode and store into it
    encoded_packet = bytearray()
    while pdu_packetization_lib.PS_HasNextByte(serializer_pointer):
        current_byte = pdu_packetization_lib.PS_NextByte(serializer_pointer)
        encoded_packet.extend(current_byte.to_bytes(length=1, byteorder='little'))

    return bytes(encoded_packet)


def decode_pdu_packet(encoded_packet: bytes) -> PduPacket:
    """Decode bytes to PDU packet using C library"""
    if not PACKETIZATION_AVAILABLE:
        raise RuntimeError("PDU packetization C library not available")
    
    # Setup C PduPacket
    packet_pointer = (PduPacketCStruct * 1)(PduPacketCStruct())
    pdu_packetization_lib.PP_InitializePacket(packet_pointer, 0)

    # Setup C deserializer
    deserializer_pointer = (PduPacketDeserializerCStruct * 1)(PduPacketDeserializerCStruct())
    pdu_packetization_lib.PD_ResetDeSerializer(deserializer_pointer)

    # Call C lib function for decoding encoded packet, one byte at a time
    for byte_value in encoded_packet:
        status = pdu_packetization_lib.PD_Apply(deserializer_pointer, byte_value, packet_pointer)
        if status != 1:
            LOGGER.debug(f"Final status code for decoding was: {status}")
            break

    # Build python PduPacket object from C PduPacket type
    pdu_packet = PduPacket()
    pdu_packet.logical_unit_id = packet_pointer[0].u8MessageAndLogicalUnitId & 0xF
    pdu_packet.message_id = (packet_pointer[0].u8MessageAndLogicalUnitId >> 4) & 0xF
    for x in range(0, packet_pointer[0].u8PayloadLength):
        pdu_packet.payload.append(packet_pointer[0].au8Payload[x])

    return pdu_packet
