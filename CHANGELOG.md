# Changelog

## 0.2.2
+message_handler_config.allow_override

## 0.2.1
fix with_message_handler_config for sub class

## 0.1.15
+ MessagePacker
message_id_system_keep_alive_req, message_id_system_keep_alive_ack move to SessionKeepAliveParams

## 0.1.14
+ message_id_system_keep_alive_req, message_id_system_keep_alive_ack

## 0.1.13
+ only_stop_self_when_tick_error

## 0.1.12
fix id_system_keep_alive_req, id_system_keep_alive_ack

## 0.1.11
fix _is_valid_message_format: msg_id can be any type not None

## 0.1.10
fix message length serialize

## 0.1.9
+ configurable: message size pack format

## 0.1.8
PY3: binary_type from bytes to bytearray

## 0.1.7
+ Server.get_sessions Server.get_ready_sessions Client.get_ready_session

## 0.1.6
+ check_session_open,on_session_opened,on_session_closing,on_session_closed
+ Session.get_manage_owner

## 0.1.5
do not register message handler with duplicate id
fix all classes use the same message map bug

## 0.1.4
trivial: modify client in example - remove timeout when construct Client

## 0.1.3

Session.force_close add force_wait_timeout param
add Client.get_session & ClientBlockConnect.get_session
fix Session.handle_write assert error after Session.handle_read get close error

## 0.1.2

fix README.rst format.

## 0.1.1

fix README.rst format.

## 0.1.0

Initial release.


