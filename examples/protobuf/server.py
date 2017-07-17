import logging
import asynmsg
import protobuftools
import main_pb2

logging.basicConfig(
	level=logging.DEBUG,
	format='[%(asctime)s][%(levelname)-4.4s] %(message)s',
	datefmt='%H:%M:%S'
)

history_visited_count = 0


@asynmsg.with_message_handler_config
class ServerSession(protobuftools.SessionS):
	def __init__(self, sock, address):
		protobuftools.SessionS.__init__(self, sock, address)
		self.client_no = -1

	@protobuftools.protobuf_handler_config(main_pb2.ID_Login, main_pb2.Login)
	def recv_Login(self, msg_id, msg_data):
		global history_visited_count
		history_visited_count += 1
		self.client_no = msg_data.client_number
		#logging.info("client %-4d: welcome, the No.%d guest", msg_data.client_number, history_visited_count)

		login_ack_data = main_pb2.LoginAck()
		login_ack_data.result = 'login success with No.%d' % history_visited_count
		self.send_message(main_pb2.ID_LoginAck, login_ack_data)

	@protobuftools.protobuf_handler_config(main_pb2.ID_Ping, main_pb2.Ping)
	def recv_Ping(self, msg_id, msg_data):
		#logging.info("client %-4d: recv Ping %-4s, send Pong", self.client_no, str(msg_data.data))

		pong_data = main_pb2.Pong()
		pong_data.data = msg_data.data
		self.send_message(main_pb2.ID_Pong, pong_data)


class Server(asynmsg.Server):
	session_class = ServerSession


def main():
	server = Server()
	server.set_listen_address(('127.0.0.1', 12345))
	server.start()
	asynmsg.run_forever()


if __name__ == '__main__':
	main()
