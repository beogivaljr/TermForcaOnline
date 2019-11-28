#!/usr/bin/python3

import socket
import time

PORT = 8080        # The port used by the server
ENCODING = 'utf-8'
API_USER_INPUT = 'USER_INPUT '

print("Digite o Nome ou IP do host:")
#host = input()
host = '127.0.0.1'
hostIp = socket.gethostbyname(host)

print("Digite a porta:")
#portStr = input()
portStr = 8080
port = int(portStr)

print("Digite o caminho do arquivo:")
#filePath = input()
filePath = ""

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((hostIp, port))
    s.sendall(bytes(f'POST TOUCH ', 'utf-8'))
    data = s.recv(1024)
    command = data.decode(ENCODING)
    if 'FIRST' in command:
        print('Escolha a palavra:')
        s.sendall(bytes(f'{API_USER_INPUT}{input()}', 'utf-8'))
