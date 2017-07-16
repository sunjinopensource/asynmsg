@echo off
protoc.exe --python_out=. proto2\main.proto
move /y proto2\main_pb2.py ..
pause