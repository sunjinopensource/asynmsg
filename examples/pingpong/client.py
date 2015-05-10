import random
import time
import logging
import asynmsg


logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)-4.4s] %(message)s',
    datefmt='%H:%M:%S'
)

client_number = random.randint(1, 10000)
ping_interval = 1

@asynmsg.with_message_handler_config
class ClientSession(asynmsg.SessionC):
    def __init__(self, sock, address):
        asynmsg.SessionC.__init__(self, sock, address)
        self.ping_time = -1

    def on_opened(self):
        asynmsg.SessionC.on_opened(self)
        self.send_message('Login', client_number)

    @asynmsg.message_handler_config('LoginAck')
    def on_LoginAck(self, msg_id, msg_data):
        logging.info("%s", msg_data)
        self.send_ping()

    @asynmsg.message_handler_config('Pong')
    def on_Pong(self, msg_id, msg_data):
        logging.info("recv Pong %-4s, send Ping after %d seconds", msg_data, ping_interval)
        self.ping_time = time.clock() + ping_interval

    def tick(self):
        asynmsg.SessionC.tick(self)

        if self.ping_time > 0 and self.ping_time < time.clock():
            self.ping_time = -1
            self.send_ping()

    def send_ping(self):
        value = random.randint(1, 10000)
        logging.info("send Ping %d", value)
        self.send_message('Ping', value)


class Client(asynmsg.ClientBlockConnect):
    session_class = ClientSession


def main():
    logging.info("========= client %d started =========", client_number)
    client = Client(('127.0.0.1', 12345), 5)
    if not client.is_started():
        logging.error('failed to connect server: %s', str(client.get_error()))
        return
    asynmsg.run_forever()


if __name__ == '__main__':
    main()
