import ctypes
import sys

MAX_PAYLOAD_SIZE = 255

# Setup ctypes for PDU packet lib
if sys.platform.startswith("win") and sys.maxsize > 2**32:  # check and validate platform to load shared library file
    pdu_packetization_lib = ctypes.cdll.LoadLibrary("resource/pdu_packetization.dll")
elif sys.platform.startswith("lin") and sys.maxsize > 2**32:
    pdu_packetization_lib = ctypes.cdll.LoadLibrary("resource/pdu_packetization.so")
else:
    print("Error invalid platform or not using 64-bit Python interpreter")
    sys.exit(1)
    
pdu_packetization_lib.PS_HasNextByte.restype = ctypes.c_bool
pdu_packetization_lib.PS_NextByte.restype = ctypes.c_ubyte
pdu_packetization_lib.PD_Apply.restype = ctypes.c_int


class PduPacketCStruct(ctypes.Structure):
    _fields_ = [('u8MessageAndLogicalUnitId', ctypes.c_ubyte),
                ('u8PayloadLength', ctypes.c_ubyte),
                ('au8Payload', ctypes.c_ubyte * MAX_PAYLOAD_SIZE)]


class PduPacketSerializerCStruct(ctypes.Structure):
    _fields_ = [('psPacket', ctypes.POINTER(PduPacketCStruct)),
                ('eState', ctypes.c_uint),  # Treat enums as integers
                ('u8Index', ctypes.c_ubyte),
                ('bHasPendingByte', ctypes.c_bool),
                ('u8PendingByte', ctypes.c_ubyte),
                ('u16Crc', ctypes.c_ushort)]


class PduPacketDeserializerCStruct(ctypes.Structure):
    _fields_ = [('eState', ctypes.c_uint),  # Treat enums as integers
                ('u8Index', ctypes.c_ubyte),
                ('bStuffByte', ctypes.c_bool),
                ('u16CalculatedCrc', ctypes.c_ushort),
                ('u8ReceivedCrc0', ctypes.c_ubyte)]


class PduPacket:
    message_id = 0
    logical_unit_id = 0
    payload = []

    def __init__(self):
        self.payload = []
        pass

    def __str__(self):
        return (f"Message ID: {self.message_id}, Logical Unit ID: {self.logical_unit_id} "
                f"\nPayload:{[hex(value) for value in self.payload]}")


def encode_pdu_packet(pdu_packet: PduPacket) -> bytes:
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
    # Setup C PduPacket
    packet_pointer = (PduPacketCStruct * 1)(PduPacketCStruct())
    pdu_packetization_lib.PP_InitializePacket(packet_pointer, 0)

    # Setup C deserializer
    deserializer_pointer = (PduPacketDeserializerCStruct * 1)(PduPacketDeserializerCStruct())
    pdu_packetization_lib.PD_ResetDeSerializer(deserializer_pointer)

    # Call C lib function for decoding encoded packet, one byte at a time, stop and print if status code is not
    # InProgress=1
    for byte_value in encoded_packet:
        status = pdu_packetization_lib.PD_Apply(deserializer_pointer, byte_value, packet_pointer)

        if status != 1:
            print(f"Final status code for decoding was: {status}")
            break

    # Build python PduPacket object from C PduPacket type
    pdu_packet = PduPacket()
    pdu_packet.logical_unit_id = packet_pointer[0].u8MessageAndLogicalUnitId & 0xF
    pdu_packet.message_id = (packet_pointer[0].u8MessageAndLogicalUnitId >> 4) & 0xF
    for x in range(0, packet_pointer[0].u8PayloadLength):
        pdu_packet.payload.append(packet_pointer[0].au8Payload[x])

    return pdu_packet


# if __name__ == '__main__':
#     # Test/example driver code

#     # Packet encoding
#     packet = PduPacket()
#     packet.message_id = 4
#     packet.logical_unit_id = 5
#     packet.payload.append(0x4)
#     packet.payload.append(0xAA)
#     packet.payload.append(0xFF)
#     packet.payload.append(0xC0)
#     packet.payload.append(0x55)

#     print("Encoded Packet:")
#     encoded_packet = encode_pdu_packet(packet)
#     print([hex(value) for value in encoded_packet])

#     # Decoding of packet that was just encoded
#     print("\n\nDecoded Packet:")
#     print(str(decode_pdu_packet(encoded_packet)))

#     # Build example PduGoOperate packet
#     packet = PduPacket()
#     packet.message_id = 10 # PduGoOperate Message ID is 10
#     packet.logical_unit_id = 0 # There is no logical ID, so just set to 0
#     # Payload is empty, so do not append anything to it

#     encoded_operate = encode_pdu_packet(packet)
#     print([hex(value) for value in encoded_operate])

