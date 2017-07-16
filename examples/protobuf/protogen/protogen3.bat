@echo off
protoc.exe --python_out=. proto3\main.proto
move /y proto3\main_pb2.py ..
pause