#!/usr/bin/python3

from shared_descubra_palavra import *
import socket
import time


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(encode(f'POST TOUCH '))
        data = s.recv(1024)
        command = decode(data)
        if 'FIRST' in command:
            print('Escolha a palavra:')
            s.sendall(encode(f'{API_USER_INPUT}{input()}'))