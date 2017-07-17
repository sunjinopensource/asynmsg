import asynmsg
import struct
import google.protobuf.message

def protobuf_handler_config(msg_id, msg_cls=None):
    def wrapper(func):
        @asynmsg.message_handler_config(msg_id)
        def wrapper2(self, msg_id, msg_data):
            if msg_cls is None:
                proto_data = msg_data
            else:
                proto_data = msg_cls()
                if issubclass(msg_cls, google.protobuf.message.Message):
                    proto_data.ParseFromString(msg_data)

            if self.has_netlog:
                self.log_info('%s[RECV %04d] %s=%s' % (self.get_low_level_desc(), msg_id,
                                                       '' if proto_data is None else proto_data.__class__.__name__,
                                                       '' if proto_data is None else str(proto_data)))

            return func(self, msg_id, proto_data)
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


def _send_message(cls, self, msg_id, msg_data):
    if self.has_netlog:
        self.log_info('%s[SEND %04d] %s=%s' % (self.get_low_level_desc(), msg_id,
                                            '' if msg_data is None else msg_data.__class__.__name__,
                                            '' if msg_data is None else str(msg_data)))

    if msg_data is not None:
        if isinstance(msg_data, google.protobuf.message.Message):
            msg_data = msg_data.SerializeToString()

    return super(cls, self).send_message(msg_id, msg_data)


class SessionS(asynmsg.SessionS):
    message_packer = MessagePacker()
    has_netlog = True

    def send_message(self, msg_id, msg_data):
        return _send_message(SessionS, self, msg_id, msg_data)

class SessionC(asynmsg.SessionC):
    message_packer = MessagePacker()
    has_netlog = True

    def send_message(self, msg_id, msg_data):
        return _send_message(SessionC, self, msg_id, msg_data)


