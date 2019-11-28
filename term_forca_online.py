#!/usr/bin/python3

from .ConstantesTermForcaOnline import GlobalConstants as C
import socket
import time

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((C.HOST, C.PORT))
    s.sendall(bytes(f'POST TOUCH ', 'utf-8'))
    data = s.recv(1024)
    command = data.decode(C.ENCODING)
    if 'FIRST' in command:
        print('Escolha a palavra:')
        s.sendall(bytes(f'{C.API_USER_INPUT}{input()}', C.ENCODING))
