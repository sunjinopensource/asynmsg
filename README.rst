asynmsg
=======

A library based on asyncore, used to build tcp server/client application communicating each other with customized messages.

Examples
--------

Server::

    import asynmsg

    @asynmsg.with_message_handler_config
    class ServerSession(asynmsg.SessionS):

        @asynmsg.message_handler_config('Login')
        def on_Login(self, msg_id, msg_data):
            self.send_message('LoginAck', 'login success')

    class Server(asynmsg.Server):
        session_class = ServerSession

    Server(('127.0.0.1', 12345))
    asynmsg.run_forever()

Client::

    import asynmsg

    @asynmsg.with_message_handler_config
    class ClientSession(asynmsg.SessionC):
        def on_opened(self):
            asynmsg.SessionC.on_opened(self)
            self.send_message('Login', 'test1')

        @asynmsg.message_handler_config('LoginAck')
        def on_LoginAck(self, msg_id, msg_data):
            pass

    class Client(asynmsg.ClientBlockConnect):
        session_class = ClientSession

    client = Client(('127.0.0.1', 12345))
    if client.is_started():
        asynmsg.run_forever()
