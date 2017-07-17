import random
import time
import logging
import asynmsg
import protobuftools
import main_pb2

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)-4.4s] %(message)s',
    datefmt='%H:%M:%S'
)

client_number = random.randint(1, 10000)
ping_interval = 1

@asynmsg.with_message_handler_config
class ClientSession(protobuftools.SessionC):
    def __init__(self, sock, address):
        protobuftools.SessionC.__init__(self, sock, address)
        self.ping_time = -1

    def on_opened(self):
        protobuftools.SessionC.on_opened(self)

        login_data = main_pb2.Login()
        login_data.client_number = client_number
        self.send_message(main_pb2.ID_Login, login_data)

    @protobuftools.protobuf_handler_config(main_pb2.ID_LoginAck, main_pb2.LoginAck)
    def recv_LoginAck(self, msg_id, msg_data):
        #logging.info("%s", msg_data.result)
        self.send_ping()

    @protobuftools.protobuf_handler_config(main_pb2.ID_Pong, main_pb2.Pong)
    def recv_Pong(self, msg_id, msg_data):
        #logging.info("recv Pong %-4s, send Ping after %d seconds", msg_data.data, ping_interval)
        self.ping_time = time.clock() + ping_interval

    def tick(self):
        protobuftools.SessionC.tick(self)

        if self.ping_time > 0 and self.ping_time < time.clock():
            self.ping_time = -1
            self.send_ping()

    def send_ping(self):
        value = random.randint(1, 10000)
        #logging.info("send Ping %d", value)

        ping_data = main_pb2.Ping()
        ping_data.data = value
        self.send_message(main_pb2.ID_Ping, ping_data)


class Client(asynmsg.ClientInfinite):
    session_class = ClientSession


def main():
    logging.info("========= client %d started =========", client_number)
    client = Client()
    client.set_connect_address(('127.0.0.1', 12345))
    if not client.start():
        return
    asynmsg.run_forever()


if __name__ == '__main__':
    main()
