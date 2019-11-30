#!/usr/bin/python3

from shared_descubra_palavra import *
import logging
import threading
import time
import socket

# Mensagens para o servidor
TITLE_MAIN = 'Main:'
TITLE_MAIN_GAME = 'Main Game:'
TITLE_FIRST_PLAYER = 'Primeiro jogador:'
TITLE_GUESSING_PLAYER = 'Jogador'
MSG_WAITING_NEW_PLAYERS = 'Esperando novos jogadores...'
MSG_CONNECTED = 'Conectado'
MSG_TOTAL_CONNECTED_PLAYERS = 'Total de jogadores ->'
MSG_DISCONNECTED = 'Desconectado.'
MSG_SERVER_CLOSED = 'Servidor encerrado.'
MSG_GAME_STARTED = 'Jogo iniciado'

# Mensagens para o cliente
CLT_MSG_TOO_LONG_WORD = 'Palavra muito longa, por favor escolha uma palavra mais curta.'

# Constantes do servidor
TOTAL_GAME_TIME = 9  # Tempo total de jogo em segundos
STOP_RECEIVING = 'STOP_RECEIVING '

# Variáveis globais do servidor
connected_players = []  # Lista com os jogadores ativos
main_thread_id = 0
first_player_thread_id = 0
main_game_thread_id = 0
game_word = None
current_game_time = TOTAL_GAME_TIME
game_status_needs_update = False


# Recebe o objeto usuário da connexão do socket {player = (connection, address)}
# Devolve o endereço da conexão do usuário {addr = (ip, port)}
def get_player_address(player):
    return player[1]


# Recebe o objeto usuário da connexão do socket {player = (connection, address)}
# Devolve o objeto conexão do usuário
def get_player_connection(player):
    return player[0]


# Recebe o objeto usuário da connexão do socket {player = (connection, address)}
# Devolve o ip do usuário
# Serve como identificador único!
def get_player_ip(player):
    return get_player_address(player)[0]


# Recebe um socket e aguarda uma nova connexão
# Devolve um novo jogador {player = (connection, address)}
def wait_new_player_from(sock):
    return sock.accept()


# Imprime log com o horário e um apelido para a thread
def log(any_object):
    form = '%(asctime)s - %(message)s'
    logging.basicConfig(format=form, level=logging.INFO, datefmt='%H:%M:%S')
    current_thread_id = threading.current_thread().ident
    current_thread_alias = current_thread_id % 1000
    if current_thread_id is main_thread_id:
        logging.info(f'{TITLE_MAIN} {any_object}')

    elif current_thread_id is main_game_thread_id:
        logging.info(f'{TITLE_MAIN_GAME} {any_object}')

    elif current_thread_id is first_player_thread_id:
        logging.info(f'{TITLE_FIRST_PLAYER} {any_object}')

    else:
        logging.info(f'{TITLE_GUESSING_PLAYER} {current_thread_alias}: {any_object}')


# Devolve o total de jogadores conectados
def total_connected_players():
    return len(connected_players)


# Imprime o todal de jogadores conectados
def log_total_players():
    log(f'{MSG_TOTAL_CONNECTED_PLAYERS} {total_connected_players()}')


# Disconecta o jogador e o remove da lista de jogadores
def disconnect(player):
    if player in connected_players:
        connected_players.remove(player)
        get_player_connection(player).close()
        log(f'{get_player_ip(player)} {MSG_DISCONNECTED}')
        log_total_players()


# TODO: Fluxo dos demais jogadores (jogadores adivinhadores)
# Thread paralela que trata os usuários que vão tentar adivinhar a palavra proposta pelo primeiro jogador
# Temos uma thread dessas por usuário
def treat_guessing(player):
    log(MSG_CONNECTED)
    with get_player_connection(player) as conn:
        try:
            print('TODO GUEST')
            time.sleep(20)
        finally:
            disconnect(player)


# Recebe a requisição (str) do primeiro jogador
# Traduz os comandos recebidos pelo cliente através da requisição
# Devolve a resposta adequada para ser enviada ao cliente
def translate_first_players(request):
    if f'{API_POST}{API_TOUCH}' in request:
        return f'{API_POST}{API_FIRST}{API_TOUCH}'

    elif f'{API_POST}{API_USER_INPUT}' in request:
        chosen_word = get_content_from(request)  # Nova string contendo a entrada do usuário
        if len(chosen_word) <= MAX_INPUT_LENGTH:
            main_game_tread = threading.Thread(target=setup_game_with, args=(chosen_word,))
            main_game_tread.start()
            log(MSG_GAME_STARTED)
            return API_SUCCESS
        else:
            return f'{API_POST}{API_FIRST}{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'
    elif f'{API_POST}{API_START}' in request:
        run_game_timer()
        return STOP_RECEIVING

    else:
        return f'{API_POST}{API_FIRST}{API_BAD_REQUEST}'


# Thread paralela que trata o primeiro usuário, responsável por digitar a palavra que vão tentar adivinhar
# Temos uma thread dessas só para o primeiro usuário
def handle_first(player):
    global first_player_thread_id
    first_player_thread_id = threading.current_thread().ident  # Captura o id da thread do primeiro jogador
    log(MSG_CONNECTED)
    with get_player_connection(player) as conn:
        try:
            while True:
                request = decode(conn.recv(MAX_PACK_LENGTH))  # Aguarda a receber a requisição

                # Após a resposta bem sucedida
                if API_END in request:  # Checa se a requisição tem fim no cabeçalho
                    response = translate_first_players(request)  # Traduz a requisição e gera uma resposta
                    if STOP_RECEIVING in response:
                        break
                    else:
                        conn.sendall(encode(response))  # Envia a resposta ao cliente
                else:
                    # Envia 400 e encerra a conexão
                    conn.sendall(encode(API_BAD_REQUEST))
                    disconnect(player)
                    break

            # Aguarda o jogador encerrar a conexão ou ignora jogadores já desconectados
            while conn.fileno() is not -1:
                pass

        except BrokenPipeError as e:
            log(e)
        except ConnectionResetError as e:
            log(e)
        except Exception as e:
            logging.exception(e)
            conn.sendall(encode(API_ERROR_500))
        finally:
            disconnect(player)


# Envia o 'status_description' do jogo para todas as conexões ativas
def send_all_players(game_status):
    for player in connected_players:
        try:
            get_player_connection(player).sendall(encode(game_status))  # Envia status do jogo
        finally:  # Ignora quaisquer erros
            pass


# TODO: Função que monta uma str com o do status do jogo
# IMPORTANTE - Só pode ser chamada por uma thread pois será fonte de conflitos
# Função responsável por montar e enviar a descrição do status do jogo
def update_game_status():
    status_description = 'Status do jogo'
    send_all_players(status_description)


# TODO: Função que cuida do jogo corrente
# Thread responsável pelo jogo corrente
def setup_game_with(word):
    global main_game_thread_id
    main_game_thread_id = threading.current_thread().ident
    global game_word
    game_word = word
    global game_status_needs_update
    game_status_needs_update = True

    # Loop principal do jogo
    while current_game_time > 0:
        # Verifica se uma atualização é necessária
        if game_status_needs_update:
            update_game_status()
            game_status_needs_update = False
            time.sleep(0.5)  # Tempo mínimo até a próxima atualização

    # Após o fim do jogo
    finish_game()


# Subtrai um de current_timer até que chegue no zero
def run_game_timer():
    global current_game_time
    global game_status_needs_update
    if current_game_time > 0:
        current_game_time -= 1
        threading.Timer(1, function=run_game_timer).start()

        # Pede atualização do status a cada dois segundos
        if current_game_time % 2 == 0:
            game_status_needs_update = True


# TODO: Função que finaliza o jogo
# Finaliza o jogo
# Gera e envia o ultimo status do jogo, contendo ganhadores e aviso de fim de jogo
# Disconecta todos os jogadores
def finish_game():
    last_status_description = 'Fim de jogo'
    send_all_players(last_status_description)

    global current_game_time
    current_game_time = TOTAL_GAME_TIME  # Reseta o timer
    # Disconecta todos os jogadores
    while len(connected_players) > 0:
        disconnect(connected_players[0])


# Execussão principal do programa
if __name__ == '__main__':
    main_thread_id = threading.current_thread().ident  # Captura o id da main thread para futura identificação
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
            s.listen()
            while True:
                log(MSG_WAITING_NEW_PLAYERS)
                new_player = wait_new_player_from(s)

                # Após conexão bem sucedida
                connected_players.append(new_player)
                if total_connected_players() == 1:
                    t = threading.Thread(target=handle_first, args=(new_player,))
                else:
                    t = threading.Thread(target=treat_guessing, args=(new_player,))
                t.start()
                log_total_players()
        finally:
            s.close()
            log(MSG_SERVER_CLOSED)
