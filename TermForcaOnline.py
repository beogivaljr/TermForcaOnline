#!/usr/bin/env python3

import socket

PORT = 8080        # The port used by the server

print("Digite o Nome ou IP do host:")
host = input()
hostIp = socket.gethostbyname(host)

print("Digite a porta:")
portStr = input()
port = int(portStr)

print("Digite o caminho do arquivo:")
filePath = input()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((hostIp, port))
    s.sendall(bytes('GET ' + filePath + ' HTTP/1.1\r\n\r\n','utf-8'))
    data = s.recv(1024)
    file = s.recv(1025)

print()
print("Message:")
print("----------------------------------------------------")
print(repr(data))
print("----------------------------------------------------")
print()
print("File:")
print("----------------------------------------------------")
print(file)
print("----------------------------------------------------")
s.close()
