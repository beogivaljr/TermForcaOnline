#!/usr/bin/python3

from shared_descubra_palavra import *
import socket
import time


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        s.sendall(encode(f'{API_POST}{API_TOUCH}{API_END}Beo'))  # Envia primeiro contato com o apelido
        command = decode(s.recv(1024))  # Recebe confirmação, ou pedido de nome mais curto

        if 'FIRST' in command:
            # Envia 'exemplo' para ser adivinhado
            s.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}exemplo'))
            print(decode(s.recv(1024)))  # Recebe confirmação

            # Em um thread paralela
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status

            # Avisa o servidor que o jogo já pode começar
            s.sendall(encode(f'{API_POST}{API_START}{API_END}'))

            # Em um thread paralela
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status

            # Servidor avisa que o jogo acabou e mostra o resultado
            print(decode(s.recv(1024)))  # Recebe status

        else:
            # Na thread principal
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status

            # Servidor avisa que o jogo começou
            print(decode(s.recv(1024)))

            # Jogador começa a enviar chutes em uma thread paralela
            s.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}evento'))  # Envia chute
            print(decode(s.recv(1024)))  # Recebe status na principal
            print(decode(s.recv(1024)))  # Recebe status na principal
            s.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}elenco'))  # Envia chute
            print(decode(s.recv(1024)))  # Recebe status na principal
            print(decode(s.recv(1024)))  # Recebe status na principal
            s.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}exemplo'))  # Envia chute
            print(decode(s.recv(1024)))  # Recebe aviso de vitória e para thread paralela

            print(decode(s.recv(1024)))  # Recebe status
            print(decode(s.recv(1024)))  # Recebe status

            # Servidor avisa que o jogo acabou e mostra o resultado
            print(decode(s.recv(1024)))  # Recebe status
