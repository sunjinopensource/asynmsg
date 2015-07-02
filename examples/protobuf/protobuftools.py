import asynmsg
import struct

def protobuf_handler_config(msg_id, msg_cls=None):
    def wrapper(func):
        @asynmsg.message_handler_config(msg_id)
        def wrapper2(self, msgid, msg_data):
            if msg_cls is None:
                proto_data = msg_data
            else:
                proto_data = msg_cls()
                proto_data.ParseFromString(msg_data)
            return func(self, msgid, proto_data)
        return wrapper2
    return wrapper


class SessionS(asynmsg.SessionS):
    def encode_message_to_bytes(self, msg_id, msg_data):
        bytes = struct.pack('H', msg_id)
        if msg_data is not None:
            bytes += msg_data.SerializeToString()
        return bytes

    def decode_message_from_bytes(self, bytes):
        msg_id = struct.unpack_from('H', bytes[:struct.calcsize('H')])[0]
        return (msg_id, bytes[struct.calcsize('H'):])


class SessionC(asynmsg.SessionC):
    def encode_message_to_bytes(self, msg_id, msg_data):
        bytes = struct.pack('H', msg_id)
        if msg_data is not None:
            bytes += msg_data.SerializeToString()
        return bytes

    def decode_message_from_bytes(self, bytes):
        msg_id = struct.unpack_from('H', bytes[:struct.calcsize('H')])[0]
        return (msg_id, bytes[struct.calcsize('H'):])
