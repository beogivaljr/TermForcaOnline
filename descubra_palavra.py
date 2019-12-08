#!/usr/bin/python3

from shared_descubra_palavra import *
import socket
import threading
import time


# Variaveis globais
should_wait_game_start = True
has_not_won = True
game_is_not_over = True
word_tip = 'D#c#'


# Recebe uma erro vindo do servidor
# Devolve o conteúdo sem o cabeçalho
def get_erro_message_from(server_response):
    return server_response.split(API_USER_ERROR)[1]


# TODO: Função display(message)
# Recebe uma 'str' a ser imprimida.
# Caso o terminal esteja aguardando alguma entrada do usuário,
# imprime a string recebida seguida da ultima pergunta feita ao usuário.
def display(message):
    print(message)


# TODO: Função ask(question)
# Recebe uma 'str' a ser imprimida como a pergunta ao usuário.
# A 'str' deve ser menor que MAX_INPUT_LENGTH, caso contrário imprimir erro e pedir novamente
# Guarda a pergunta na variável global.
# Pede uma entrada ao usuário 'input()'.
# Devolve a 'str' entrada pelo usuário e seta a variável global da pergunta para None.
def ask(question: str):
    display(question)
    return input()


# Joga como jogador adivinhador
# Recebe dica e envia 'chutes' até acertar a palavra correta
def play_as_guessing(connected_socket: socket):
    status_receiver_thread = threading.Thread(target=recurring_status_receiving, args=(connected_socket,))
    status_receiver_thread.start()
    while should_wait_game_start:  # Espera o sinal de inicio de jogo
        pass

    while has_not_won and game_is_not_over:
        guess = ask(f'Sua dica é \'{word_tip}\', chute uma palavra:')
        connected_socket.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}{guess}'))  # Envia chute


# Joga como primeiro jogador
# Escolhe a palavra, escolhe quando inicia o jogo e assiste até o fim
def play_as_first(connected_socket: socket):
    # Pede ao jogador a palavra a ser adivinhada
    chosen_word = ask('Escolha uma palavra para ser adivinhada:')
    while True:
        connected_socket.sendall(encode(f'{API_POST}{API_USER_INPUT}{API_END}{chosen_word}'))
        server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))  # Recebe confirmação
        while API_DIRECT_MSG in server_response:  # Repete a recepção caso receba um status por engano
            server_response = decode(connected_socket.recv(MAX_PACK_LENGTH))

        if API_SUCCESS in server_response:
            status_receiver_thread = threading.Thread(target=recurring_status_receiving, args=(connected_socket,))
            status_receiver_thread.start()
            ask('Quando estiver pronto para começar o jogo pressione \'enter\'')
            connected_socket.sendall(encode(f'{API_POST}{API_START_GAME}{API_END}'))
            time.sleep(100)
            break

        else:
            display(get_erro_message_from(response))
            chosen_word = ask('Escolha outra palavra:')


# Recebe e printa o status do jogo constantemente
# Fecha a conexão e encerra a thread caso não venha uma mensagem direta
def recurring_status_receiving(receiving_socket: socket):
    while False:
        try:
            server_response = decode(receiving_socket.recv(MAX_PACK_LENGTH))
            if API_END in server_response:
                if API_DIRECT_MSG in server_response:
                    display(get_content_from(server_response))
                    if API_TIP in server_response:
                        global word_tip
                        word_tip = get_content_from(server_response)
                    if API_START_GAME in server_response:
                        global should_wait_game_start
                        should_wait_game_start = False

                elif API_WON in server_response:
                    global has_not_won
                    has_not_won = False

                elif API_GAME_OVER in server_response:
                    global game_is_not_over
                    game_is_not_over = False
                    receiving_socket.close()
                    return

            else:
                receiving_socket.close()
                return

        except Exception as e:
            receiving_socket.close()
            if e is not None:
                pass
            return


# Execussão principal do programa
if __name__ == '__main__':
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))  # Aguarda conexão bem sucedida

        # Após conexão bem sucedida
        nickname = ask('Bem vindo, diga nos seu apelido:')
        while True:
            s.sendall(encode(f'{API_POST}{API_NICKNAME}{API_END}{nickname}'))  # Envia primeiro contato com o apelido
            response = decode(s.recv(MAX_PACK_LENGTH))  # Recebe confirmação, ou pedido de nome mais curto
            while API_DIRECT_MSG in response:  # Repete a recepção caso receba um status por engano
                response = decode(s.recv(MAX_PACK_LENGTH))

            if API_SUCCESS in response:
                play_as_first(s)

                # if API_TIP in response:
                #     word_tip = get_content_from(response)
                #     play_as_guessing(s)
                # else:  # Se não vier dica calcelar a conexão
                #     pass
                break

            else:
                display(get_erro_message_from(response))
                nickname = ask('Escolha outro apelido:')
    except ConnectionRefusedError:
        display('Ops, servidor fechado =(')
