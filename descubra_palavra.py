#!/usr/bin/python3

from shared_descubra_palavra import *
import socket
import threading
import time


# Variaveis globais
should_wait_game_start = True
has_not_won = True
game_is_not_over = True
input_prompt = None


# Returns the content of a request of type 'API_USER_ERROR'
def get_user_error_content(server_response):
    return server_response.split(API_USER_ERROR)[1]


# Play as a guessing player
def play_as_guessing(connected_socket: socket):
    while True:
        print('Pronto!\nAguardando o jogo começar...')
        server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))

        if API_SUCCESS in server_response:
            if API_START_GAME in server_response:
                print('\n\n############\nJogo iniciado!\n############\n\n')
                print(get_success_content(server_response))
                while API_GAME_OVER not in server_response:
                    guess = input('\nChute uma palavra: ')
                    s.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}{guess}'))  # Send guess
                    server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))
                    print(get_success_content(server_response))
                    if API_WON in server_response:
                        print('\n\n\n############\nAcertou!\n############\n\n\n')
                        break

                break
            else:
                print(server_response)

        elif API_USER_ERROR in server_response:
            print(get_user_error_content(server_response))
        else:
            print('Erro desconhecido:\n\n' + server_response)
            break

    while API_GAME_OVER not in server_response:
        time.sleep(1)
        connected_socket.sendall(encode(f'{API_GET}{API_STATUS}{API_END}'))
        server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))
        if API_SUCCESS in server_response:
            print(get_success_content(server_response))
        else:
            print(server_response)


# Playe as the first player
def play_as_first(connected_socket: socket):
    chosen_word = input('Escolha uma palavra para ser adivinhada: ')
    while True:
        connected_socket.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}{chosen_word}'))
        server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))

        if API_SUCCESS in server_response:
            global input_prompt
            input_prompt = 'Pressione \'ENTER\' para atualizar ou envie \'s\' para começar: '
            while True:
                command = input(input_prompt)
                if command.lower() == 's':
                    input_prompt = None
                    connected_socket.sendall(encode(f'{API_POST}{API_START_GAME}{API_END}'))
                    server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))
                    if API_SUCCESS in server_response:
                        print(get_success_content(server_response))
                        while API_GAME_OVER not in server_response:
                            time.sleep(1)
                            connected_socket.sendall(encode(f'{API_GET}{API_STATUS}{API_END}'))
                            server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))
                            if API_SUCCESS in server_response:
                                print(get_success_content(server_response))
                            else:
                                print(server_response)
                    else:
                        print(server_response)
                    break
                else:
                    connected_socket.sendall(encode(f'{API_GET}{API_STATUS}{API_END}'))
                    server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))
                    if API_SUCCESS in server_response:
                        print(get_success_content(server_response))
                    else:
                        print(server_response)

            break

        elif API_USER_ERROR in server_response:
            print(get_user_error_content(server_response))
            chosen_word = input('Escolha outra palavra: ')
        else:
            print('Erro desconhecido:\n\n' + server_response)
            break


if __name__ == '__main__':
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))

            # After successful connection
            nickname = input('Bem vindo, diga nos seu apelido: ')
            while True:
                s.sendall(encode(f'{API_POST}{API_NICKNAME}{API_END}{nickname}'))  # Send nickname
                response = decode(s.recv(MAX_PACK_LENGTH))  # Receive

                if API_SUCCESS in response:
                    if API_FIRST in response:
                        play_as_first(s)
                        break
                    else:
                        play_as_guessing(s)
                        break

                elif API_USER_ERROR in response:
                    print(get_user_error_content(response))
                    nickname = input('Escolha outro apelido: ')

                elif API_ERROR_500 in response:
                    print('Erro no servidor:\n\n' + response)
                    break

    except ConnectionRefusedError:
        print('Ops, servidor fechado =(')
