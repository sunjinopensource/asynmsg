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


class MessagePacker(asynmsg.MessagePacker):
    def __init__(self):
        super(MessagePacker, self).__init__()

    def pack(self, msg_id, msg_data):
        bytes = struct.pack('H', msg_id)
        if msg_data is not None:
            bytes += msg_data
        return bytes

    def unpack(self, bytes_):
        msg_id = struct.unpack_from('H', bytes_[:struct.calcsize('H')])[0]
        return (msg_id, bytes(bytes_[struct.calcsize('H'):]))

class SessionS(asynmsg.SessionS):
    message_packer = MessagePacker()

    def send_protobuf(self, msg_id, msg_data):
        if msg_data is None:
            return self.send_message(msg_id, msg_data)
        else:
            return self.send_message(msg_id, msg_data.SerializeToString())

class SessionC(asynmsg.SessionC):
    message_packer = MessagePacker()

    def send_protobuf(self, msg_id, msg_data):
        if msg_data is None:
            return self.send_message(msg_id, msg_data)
        else:
            return self.send_message(msg_id, msg_data.SerializeToString())

