import logging
import asynmsg


logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)-4.4s] %(message)s',
    datefmt='%H:%M:%S'
)

history_visited_count = 0

@asynmsg.with_message_handler_config
class ServerSession(asynmsg.SessionS):
    def __init__(self, sock, address):
        asynmsg.SessionS.__init__(self, sock, address)
        self.client_no = -1

    @asynmsg.message_handler_config('Login')
    def recv_Login(self, msg_id, msg_data):
        global history_visited_count
        history_visited_count += 1
        self.client_no = msg_data
        logging.info("client %-4d: welcome, the No.%d guest", msg_data, history_visited_count)
        self.send_message('LoginAck', 'login success with No.%d' % history_visited_count)

    @asynmsg.message_handler_config('Ping')
    def recv_Ping(self, msg_id, msg_data):
        logging.info("client %-4d: recv Ping %-4s, send Pong", self.client_no, str(msg_data))
        self.send_message('Pong', msg_data)


class Server(asynmsg.Server):
    session_class = ServerSession


def main():
    server = Server()
    server.set_listen_address(('127.0.0.1', 12345))
    server.start()
    asynmsg.run_forever()


if __name__ == '__main__':
    main()
