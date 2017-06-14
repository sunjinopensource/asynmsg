# -*- coding: utf8 -*-
import os
import sys
import socket
import errno
import time
import struct
import logging
import asyncore

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3:
    BinaryType = bytearray
elif PY2:
    BinaryType = str
else:
    raise RuntimeError('Unsupported python version.')

try:
    import cPickle as pickle
except ImportError:
    import pickle

__version__ = '0.1.15'
__all__ = [
    "Error",
    "SessionS",
    "SessionC",
    "Server",
    "Client",
    "ClientBlockConnect",
    "run_once",
    "run_forever",
    "Sleep",
    "logger",
    "AsynMsgException",
    "MessageSizeOverflowError",
    "with_message_handler_config",
    "message_handler_config",
    "SessionKeepAliveParams",
    "MessagePacker", "MessagePacker_Pickle", "MessagePacker_Struct",
]


def _str_system_error(code):
    return '%d:%s' % (code, errno.errorcode.get(code, 'unknown'))


def _connect_with_timeout(sock, address, timeout):
    sock.setblocking(False)
    end_time = time.clock() + timeout

    while True:
        time.sleep(0.001)
        code = sock.connect_ex(address)
        if code in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK) \
                or (code == errno.WSAEINVAL and os.name in ('nt', 'ce')):
            if end_time < time.clock():
                return 1, None  # timeout
            else:
                continue
        if code in (0, errno.EISCONN):
            return 0, None  # connected
        else:
            return -1, code  # error


def _is_valid_message_format(msg):
    if not isinstance(msg, tuple):
        return False
    if len(msg) != 2:
        return False
    if msg[0] is None:
        return False
    return True


def _wrapper_asyncore_log(msg, type):
    if type == "info":
        logger.info(msg)
    elif type == "warning":
        logger.warn(msg)
    elif type == "error":
        logger.error(msg)
    else:
        raise NotImplementedError


logger = logging.getLogger("asynmsg")


class Sleep:
    def __init__(self, seconds):
        self.seconds = seconds

    def __call__(self, *args, **kwargs):
        time.sleep(self.seconds)


_runner_list = []


def _run_once(runner_list, extra_tick, use_poll):
    if len(runner_list) > 0:
        asyncore.loop(0, use_poll, None, 1)
        for runner in runner_list:
            if not runner.tick():
                return runner
    if extra_tick is not None:
        code = extra_tick()
        if code is False:
            return False
    return True


def run_once(runner_list=None, extra_tick=Sleep(0.001), use_poll=False, auto_stop=True):
    if runner_list is None:
        runner_list = _runner_list

    code = _run_once(runner_list, extra_tick, use_poll)
    if code is True:  # no error
        return True
    elif code is False:  # extra tick error
        if auto_stop:
            for runner in list(runner_list):
                runner.stop()
        return False
    else:  # runner tick error
        if code.only_stop_self_when_tick_error:
            if auto_stop:
                code.stop()
            return True
        else:
            if auto_stop:
                for runner in list(runner_list):
                    runner.stop()
            return False
    return True


def run_forever(runner_list=None, extra_tick=Sleep(0.001), use_poll=False, auto_stop=True):
    if runner_list is None:
        runner_list = _runner_list

    while True:
        if not run_once(runner_list, extra_tick, use_poll, auto_stop):
            break


class Error:
    ERROR_OK = 0
    ERROR_SELECT = 1
    ERROR_REMOTE_CLOSED = 2
    ERROR_FORCE_CLOSE = 3
    ERROR_KEEP_ALIVE_TIMEOUT = 4
    ERROR_UNPACK_INVALID_MESSAGE_SIZE = 5
    ERROR_UNPACK_DECODE_MESSAGE = 6
    ERROR_RECV_MESSAGE_FORMAT = 7
    ERROR_HANDLE_MESSAGE = 8
    ERROR_CONNECT_SYSTEM = 9
    ERROR_CONNECT_TIMEOUT = 10
    ERROR_CONNECT_OPEN = 11
    ERROR_CONNECT_REFUSED = 12

    BASE_STR_ERROR_MAP = {
        ERROR_OK: 'ERROR_OK',
        ERROR_SELECT: 'ERROR_SELECT',
        ERROR_REMOTE_CLOSED: 'ERROR_REMOTE_CLOSED',
        ERROR_FORCE_CLOSE: 'ERROR_FORCE_CLOSE',
        ERROR_KEEP_ALIVE_TIMEOUT: 'ERROR_KEEP_ALIVE_TIMEOUT',
        ERROR_UNPACK_INVALID_MESSAGE_SIZE: 'ERROR_UNPACK_INVALID_MESSAGE_SIZE',
        ERROR_UNPACK_DECODE_MESSAGE: 'ERROR_UNPACK_DECODE_MESSAGE',
        ERROR_RECV_MESSAGE_FORMAT: 'ERROR_RECV_MESSAGE_FORMAT',
        ERROR_HANDLE_MESSAGE: 'ERROR_HANDLE_MESSAGE',
        ERROR_CONNECT_SYSTEM: 'ERROR_CONNECT_SYSTEM',
        ERROR_CONNECT_TIMEOUT: 'ERROR_CONNECT_TIMEOUT',
        ERROR_CONNECT_OPEN: 'ERROR_CONNECT_OPEN',
        ERROR_CONNECT_REFUSED: 'ERROR_CONNECT_REFUSED',
    }

    @staticmethod
    def str_error(code):
        return '%d:%s' % (code, Error.BASE_STR_ERROR_MAP.get(code, 'unknown'))

    def __init__(self):
        self._error = Error.ERROR_OK
        self._system_error = 0

    def __str__(self):
        s = Error.str_error(self.get_error())
        if self.has_system_error():
            s += ':'
            s += _str_system_error(self.get_system_error())
        return s

    def copy(self, other):
        self._error = other._error
        self._system_error = other._system_error

    def clear(self):
        self._error = Error.ERROR_OK
        self._system_error = 0

    def set_error(self, error, system_error=0):
        if self.has_error():
            return
        self._error = error
        self._system_error = system_error

    def get_error(self):
        return self._error

    def has_error(self):
        return self._error != Error.ERROR_OK

    def get_system_error(self):
        return self._system_error

    def has_system_error(self):
        return self._system_error != 0


class AsynMsgException(Exception):
    pass


class MessageSizeOverflowError(AsynMsgException):
    def __init__(self, msg_id, size, max_size):
        self.msg_id = msg_id
        self.size = size
        self.max_size = max_size

    def __str__(self):
        return 'MessageSizeOverflowError: msg_id=%s size=%d max_size=%d' % (self.msg_id, self.size, self.max_size)


class SessionKeepAliveParams:
    def __init__(self, idle_time=30, interval=10, probes=3, ping_id='keep_alive_ping', pong_id='keep_alive_pong'):
        self.idle_time = idle_time
        self.interval = interval
        self.probes = probes
        self.ping_id = ping_id
        self.pong_id = pong_id


class MessagePacker:
    def __init__(self, size_fmt='H'):
        self._size_fmt = size_fmt

    def pack(self, msg_id, msg_data):
        """ Pack to bytes, msg_data may be any type(including None)"""
        raise NotImplementedError

    def unpack(self, bytes):
        """Unpack to pair of (msg_id, msg_data)"""
        raise NotImplementedError

    @property
    def size_fmt(self):
        return self._size_fmt


class MessagePacker_Pickle(MessagePacker):
    def __init__(self, size_fmt='H'):
        super(MessagePacker_Pickle, self).__init__(size_fmt)

    def pack(self, msg_id, msg_data):
        return pickle.dumps((msg_id, msg_data))

    def unpack(self, bytes):
        return pickle.loads(bytes)


class MessagePacker_Struct(MessagePacker):
    def __init__(self, size_fmt='H', id_fmt='H'):
        super(MessagePacker_Struct, self).__init__(size_fmt)
        self._id_fmt = id_fmt

    def pack(self, msg_id, msg_data):
        bytes = struct.pack(self._id_fmt, msg_id)
        if msg_data is not None:
            bytes += msg_data
        return bytes

    def unpack(self, bytes):
        msg_id = struct.unpack_from(self._id_fmt, bytes)[0]
        msg_data = bytes[2:]
        return (msg_id, msg_data)


def with_message_handler_config(cls):
    cls._command_factory = {}
    if cls.keep_alive_params is not None:
        def _on_keep_alive_ping(self, msg_id, msg_data):
            self.send_message(cls.keep_alive_params.pong_id)
        def _on_keep_alive_pong(self, msg_id, msg_data):
            pass
        cls.register_command_handler(cls.keep_alive_params.ping_id, _on_keep_alive_ping)
        cls.register_command_handler(cls.keep_alive_params.pong_id, _on_keep_alive_pong)

    order_map = {}

    for func in cls.__dict__.values():
        if hasattr(func,'_message_handler_index'):
            order_map[func._message_handler_index] = func

    # keys can't sort in python 3(the type is dict_keys)
    # so we first transform it to a list
    keys = order_map.keys()
    sort_keys = list(keys)
    sort_keys.sort()

    for k in sort_keys:
        func = order_map[k]
        cls.register_command_handler(func._message_handler_msg_id, func)

    return cls


class message_handler_config:
    total_count = 0

    def __init__(self, msg_id):
        self.msg_id = msg_id
        self.index = self.__class__.total_count
        self.__class__.total_count += 1

    def __call__(self, func):
        func._message_handler_index = self.index
        func._message_handler_msg_id = self.msg_id
        return func


class _Session(asyncore.dispatcher):
    message_packer = MessagePacker_Pickle()
    keep_alive_params = SessionKeepAliveParams()  # set None to disable
    max_message_size = 16 * 1024
    max_send_size_once = 16 * 1024
    max_recv_size_once = 16 * 1024
    enable_nagle_algorithm = False

    @classmethod
    def register_command_handler(cls, cmd, handler):
        if cmd in cls._command_factory:
            raise RuntimeError("Can't register message handler with duplicate id '%s'." % cmd)
        cls._command_factory[cmd] = handler

    def __init__(self, sock, address):
        asyncore.dispatcher.__init__(self, sock)

        self._manage_owner = None

        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, not self.__class__.enable_nagle_algorithm)
        self._error = Error()

        self._in_buffer = BinaryType()
        self._out_buffer = BinaryType()

        self._last_read_time = time.clock()
        self._keep_alive_probe_count = 0

        self._force_close_time = -1
        self._force_wait_timeout = False

        self._ready = True

    def close(self):
        asyncore.dispatcher.close(self)

    # close on no data to send or timeout, like linger
    # if force_wait_timeout is True, wait even if no data to send
    def force_close(self, timeout=5, force_wait_timeout=False):
        self._force_close_time = time.clock() + timeout
        self._force_wait_timeout = force_wait_timeout

    def get_manage_owner(self):
        return self._manage_owner

    def set_ready(self, ready=True):
        self._ready = ready

    def is_ready(self):
        return self._ready

    def get_error(self):
        return self._error

    def get_remote_address(self):
        return self.addr

    def check_open(self):
        return True

    def on_opened(self):
        pass

    def on_closing(self):
        pass

    def on_closed(self):
        pass

    def tick(self):
        if not self._error.has_error():
            if self._force_close_time > 0:
                if (not self._force_wait_timeout and len(self._out_buffer) == 0) or self._force_close_time < time.clock():
                    self._error.set_error(Error.ERROR_FORCE_CLOSE)

        if not self._error.has_error():
            self._keep_alive_check()

        if not self._error.has_error():
            self._unpack_and_handle_messages()

        return not self._error.has_error()

    """ <<< asyncore.dispatcher interfaces """
    def log(self, message):
        _wrapper_asyncore_log(message, 'info')

    def log_info(self, message, type='info'):
        _wrapper_asyncore_log(message, type)

    def readable(self):
        return not self._error.has_error()

    def writable(self):
        return (not self._error.has_error()) and len(self._out_buffer) > 0

    def handle_read(self):
        if self._error.has_error():
            return

        data = self.recv(self.__class__.max_recv_size_once)
        if data:
            self._in_buffer += data
            self._last_read_time = time.clock()
            self._keep_alive_probe_count = 0

    def handle_write(self):
        if self._error.has_error():
            return

        num = self.send(self._out_buffer[:self.__class__.max_send_size_once])
        if num > 0:
            self._out_buffer = self._out_buffer[num:]

    def handle_close(self):
        if self._error.has_error():
            return

        self._error.set_error(Error.ERROR_REMOTE_CLOSED)
    """ >>> """

    def handle_message(self, msg_id, msg_data):
        handler = self.__class__._command_factory.get(msg_id)
        if handler is None:
            return self.on_unhandled_message(msg_id, msg_data)
        else:
            return handler(self, msg_id, msg_data)

    def on_unhandled_message(self, msg_id, msg_data):
        logger.warning("unhandled message '%s' from %s:%d", msg_id, self.addr[0], self.addr[1])

    def send_message(self, msg_id, msg_data=None):
        if self._error.has_error() or self._force_close_time > 0:
            return False

        byte_msg = self.message_packer.pack(msg_id, msg_data)
        length = struct.calcsize(self.__class__.message_packer.size_fmt) + len(byte_msg)

        if length > self.__class__.max_message_size:
            raise MessageSizeOverflowError(msg_id, length, self.__class__.max_message_size)

        self._out_buffer += struct.pack(self.__class__.message_packer.size_fmt, length)
        self._out_buffer += byte_msg
        return True

    def _unpack_and_handle_messages(self):
        while True:
            pair = self._unpack_message()
            if pair in (0, -1):
                break
            if not _is_valid_message_format(pair):
                try:
                    logger.error('invalid message format from %s:%d, %s', self.addr[0], self.addr[1], str(pair))
                except:
                    pass
                self._error.set_error(Error.ERROR_RECV_MESSAGE_FORMAT)
                break

            code = self.handle_message(pair[0], pair[1])
            if code is False and not self._error.has_error():
                logger.error('handle message(%s) error from %s:%d', pair[0], self.addr[0], self.addr[1])
                self._error.set_error(Error.ERROR_HANDLE_MESSAGE)

            if self._error.has_error():
                break

    # 0: retry
    # -1: error
    def _unpack_message(self):
        size_length = struct.calcsize(self.__class__.message_packer.size_fmt)
        buff_length = len(self._in_buffer)
        if buff_length < size_length:
            return 0
        length = struct.unpack_from(self.__class__.message_packer.size_fmt, self._in_buffer)[0]
        if length < size_length or length > self.__class__.max_message_size:
            logger.error('invalid message size from %s:%d, size=%d max_size=%d', self.addr[0], self.addr[1], length, self.__class__.max_message_size)
            self._error.set_error(Error.ERROR_UNPACK_INVALID_MESSAGE_SIZE)
            return -1
        if buff_length < length:
            return 0
        byte_msg = self._in_buffer[size_length:length]

        try:
            pair = self.message_packer.unpack(byte_msg)
        except:
            self._error.set_error(Error.ERROR_UNPACK_DECODE_MESSAGE)
            return -1

        self._in_buffer = self._in_buffer[length:]
        return pair

    def _keep_alive_check(self):
        if self.__class__.keep_alive_params is None:
            return

        if self._keep_alive_probe_count > self.__class__.keep_alive_params.probes:
            return

        check_time = self.__class__.keep_alive_params.idle_time + \
                     self._keep_alive_probe_count * self.__class__.keep_alive_params.interval
        if time.clock() - self._last_read_time > check_time:
            self._keep_alive_probe_count += 1
            if self._keep_alive_probe_count > self.__class__.keep_alive_params.probes:
                self._error.set_error(Error.ERROR_KEEP_ALIVE_TIMEOUT)
            else:
                self.send_message(self.__class__.keep_alive_params.ping_id)

    def _on_keep_alive_ping(self, msg_id, msg_data):
        self.send_message(self.__class__.keep_alive_params.pong_id)


class SessionS(_Session):
    def __init__(self, sock, address):
        _Session.__init__(self, sock, address)
        self._serial = -1
        pass

    def get_serial(self):
        return self._serial

    def on_opened(self):
        logger.info('open connection from %s:%d', self.addr[0], self.addr[1])

    def on_closing(self):
        logger.info('close connection from %s:%d (%s)', self.addr[0], self.addr[1], str(self._error))


class Server(asyncore.dispatcher):
    session_class = SessionS
    only_stop_self_when_tick_error = False

    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        self._session_map = {}
        self._next_serial = 0
        self._error = Error()

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(address)
        self.listen(5)

        _runner_list.append(self)

    def stop(self):
        if not self.is_started():
            return

        _runner_list.remove(self)

        self._clear_sessions()
        self._error.clear()
        self.close()
        self.socket = None

    def tick(self):
        assert self.is_started()

        if self._error.has_error():  # by dispatcher
            return False

        for session in list(self._session_map.values()):
            if session.get_error().has_error():
                self._close_session(session)

        for session in self._session_map.values():
            session.tick()

        return True

    def is_started(self):
        return self.socket is not None

    """ <<< asyncore.dispatcher interfaces """
    def log(self, message):
        _wrapper_asyncore_log(message, 'info')

    def log_info(self, message, type='info'):
        _wrapper_asyncore_log(message, type)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            return
        sock, address = pair

        if not self._open_session(sock, address):
            sock.close()

    def handle_close(self):
        self._error.set_error(Error.ERROR_SELECT)
    """ >>> """

    def get_error(self):
        return self._error

    def find_session(self, serial):
        return self._session_map.get(serial)

    def get_sessions(self):
        result = []
        for session in self._session_map.values():
            result.append(session)
        return result

    def get_ready_sessions(self):
        result = []
        for session in self._session_map.values():
            if session.is_ready():
                result.append(session)
        return result

    def broadcast(self, msg_id, msg_data=None):
        for session in self._session_map.values():
            if session.is_ready():
                session.send_message(msg_id, msg_data)

    def check_session_open(self, session):
        return session.check_open()

    def on_session_opened(self, session):
        session.on_opened()

    def on_session_closing(self, session):
        session.on_closing()

    def on_session_closed(self, session):
        session.on_closed()

    def _clear_sessions(self):
        for session in list(self._session_map.values()):
            self._close_session(session)
        self._session_map.clear()

    def _open_session(self, sock, address):
        session = self.__class__.session_class(sock, address)
        if not self.check_session_open(session):
            session.del_channel()
            return False
        session._manage_owner = self
        session._serial = self._next_serial
        self._next_serial += 1
        self._session_map[session.get_serial()] = session
        self.on_session_opened(session)
        return True

    def _close_session(self, session):
        self.on_session_closing(session)
        del self._session_map[session.get_serial()]
        session._manage_owner = None
        session.close()
        self.on_session_closed(session)


class SessionC(_Session):
    def __init__(self, sock, address):
        _Session.__init__(self, sock, address)

    def on_opened(self):
        logger.info('open connection to %s:%d', self.addr[0], self.addr[1])

    def on_closing(self):
        logger.info('close connection to %s:%d (%s)', self.addr[0], self.addr[1], str(self._error))


class Client(asyncore.dispatcher):
    session_class = SessionC
    only_stop_self_when_tick_error = False

    def __init__(self, address, timeout=5):
        asyncore.dispatcher.__init__(self)
        self._session = None
        self._error = Error()

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(address)
        self.connect_timeout_time = time.clock() + timeout

        _runner_list.append(self)
        self._started = True

    def stop(self):
        if not self.is_started():
            return

        _runner_list.remove(self)

        if self._session is None:
            self.close()
        else:
            self._close_session()

        self._error.clear()
        self._started = False

    def tick(self):
        assert self.is_started()

        if self._error.has_error():
            return False

        if self._session is None and self.connect_timeout_time < time.clock():
            self._error.set_error(Error.ERROR_CONNECT_TIMEOUT)
            return False

        if self._session is not None:
            if self._session.get_error().has_error():
                self._error.copy(self._session.get_error())
                return False

            self._session.tick()

        return True

    def is_started(self):
        return self._started

    def get_error(self):
        return self._error

    def get_session(self):
        return self._session

    def get_ready_session(self):
        return self._session if (self._session is not None and self._session.is_ready()) else None

    def check_session_open(self, session):
        return session.check_open()

    def on_session_opened(self, session):
        session.on_opened()

    def on_session_closing(self, session):
        session.on_closing()

    def on_session_closed(self, session):
        session.on_closed()

    def _open_session(self, sock, address):
        session = self.__class__.session_class(sock, address)
        if not self.check_session_open(session):
            session.del_channel()
            return False
        session._manage_owner = self
        self._session = session
        self.on_session_opened(session)
        return True

    def _close_session(self):
        session = self._session

        self.on_session_closing(session)
        self._session = None
        session._manage_owner = None
        session.close()
        self.on_session_closed(session)

    def handle_connect(self):
        self.del_channel()
        if not self._open_session(self.socket, self.addr):
            self._error.set_error(Error.ERROR_CONNECT_OPEN)
            return

    def handle_close(self):
        self._error.set_error(Error.ERROR_CONNECT_REFUSED)


class ClientBlockConnect:
    session_class = SessionC
    only_stop_self_when_tick_error = False

    def __init__(self, address, timeout=5):
        self._started = False
        self._session = None
        self._error = Error()

        self._start(address, timeout)

    def _start(self, address, timeout):
        assert not self.is_started()

        sock = socket.socket()
        code, err = _connect_with_timeout(sock, address, timeout)

        if code == -1:
            self._error.set_error(Error.ERROR_CONNECT_SYSTEM, err)
            sock.close()
            return False

        if code == 1:
            self._error.set_error(Error.ERROR_CONNECT_TIMEOUT)
            sock.close()
            return False

        if not self._open_session(sock, address):
            self._error.set_error(Error.ERROR_CONNECT_OPEN)
            sock.close()
            return False

        _runner_list.append(self)

        self._started = True
        return True

    def stop(self):
        if not self.is_started():
            return

        _runner_list.remove(self)

        self._close_session()
        self._error.clear()
        self._started = False

    def tick(self):
        assert self.is_started()
        if self._session.get_error().has_error():
            self._error.copy(self._session.get_error())
            return False

        self._session.tick()
        return True

    def is_started(self):
        return self._started

    def get_error(self):
        return self._error

    def get_session(self):
        return self._session

    def get_ready_session(self):
        return self._session if (self._session is not None and self._session.is_ready()) else None

    def check_session_open(self, session):
        return session.check_open()

    def on_session_opened(self, session):
        session.on_opened()

    def on_session_closing(self, session):
        session.on_closing()

    def on_session_closed(self, session):
        session.on_closed()

    def _open_session(self, sock, address):
        session = self.__class__.session_class(sock, address)
        if not self.check_session_open(session):
            session.del_channel()
            return False
        session._manage_owner = self
        self._session = session
        self.on_session_opened(session)
        return True

    def _close_session(self):
        session = self._session

        self.on_session_closing(session)
        self._session = None
        session._manage_owner = None
        session.close()
        self.on_session_closed(session)
