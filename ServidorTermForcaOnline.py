#!/usr/bin/python3

import logging
import threading
import time
import socket

# Comandos API
API_USER_INPUT = 'USER_INPUT '
API_GET = 'GET '
API_POST = 'POST '
API_TOUCH = 'TOUCH '
API_FIRST = 'FIRST '
API_SUCCESS = ''
API_ERROR_500 = 'HTTP/1.1 500 ERROR\r\n\r\n'
API_END = 'HTTP/1.1\r\n\r\n'

# Constantes globais
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080  # Port to listen on (non-privileged ports are > 1023)
ENCODING = 'utf-8'

# Mensagens
TITLE_MAIN = 'Main:'
TITLE_FIRST_PLAYER = 'Primeiro jogador:'
TITLE_GUESSING_PLAYER = 'Jogador'
MSG_WAITING_NEW_PLAYERS = 'Esperando novos jogadores...'
MSG_CONNECTED = 'Conectado'
MSG_TOTAL_CONNECTED_PLAYERS = 'Total de jogadores ->'
MSG_DISCONNECTED = 'Desconectado.'
MSG_SERVER_CLOSED = 'Servidor encerrado.'

# Variáveis globais
connected_players = []  # Lista com os jogadores ativos
main_thread_id = 0
first_player_thread_id = 0


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
    log(MSG_DISCONNECTED)
    log_total_players()


# Thread paralela que trata os usuários que vão tentar adivinhar a palavra proposta pelo primeiro jogador
# Temos uma thread dessas por usuário
def treat_guessing(player):
    log(MSG_CONNECTED)
    with get_player_connection(player) as conn:
        try:
            print('TODO GUEST')
            time.sleep(5)
        finally:
            disconnect(player)


# Recebe a requisição (str) do primeiro jogador
# Traduz os comandos recebidos pelo cliente através da requisição
# Devolve a resposta adequada para ser enviada ao cliente
def translate_first_players(request):
    if API_USER_INPUT in request:  # Deve ignorar qualquer outro tipo de comando case tenha entrada do usuário
        print(request)
        return request
    elif API_POST in request:
        if API_TOUCH in request:
            return f'{API_POST}{API_FIRST}{API_END}'  # Comando para avisar o cliente que este jogador foi o primeiro
        elif API_GET in request:
            return API_GET
    return 'response'


# Thread paralela que trata o primeiro usuário, responsável por digitar a palavra que vão tentar adivinhar
# Temos uma thread dessas só para o primeiro usuário
def treat_first(player):
    global first_player_thread_id
    first_player_thread_id = threading.current_thread().ident  # Captura o id da thread do primeiro jogador
    log(MSG_CONNECTED)
    with get_player_connection(player) as conn:
        try:
            while True:
                r = conn.recv(1024)  # Aguarda a receber a requisição

                # Após a resposta bem sucedida
                response = translate_first_players(r.decode(ENCODING))  # Traduz a requisição e gera a resposta
                conn.sendall(bytes(response, ENCODING))  # Envia a resposta
        except BrokenPipeError as e:
            log(e)
        except ConnectionResetError as e:
            log(e)
        except Exception as e:
            logging.exception(e)
            conn.sendall(bytes(API_ERROR_500, ENCODING))
        finally:
            disconnect(player)


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
                    t = threading.Thread(target=treat_first, args=(new_player,))
                else:
                    t = threading.Thread(target=treat_guessing, args=(new_player,))
                t.start()
                log_total_players()
        finally:
            s.close()
            log(MSG_SERVER_CLOSED)
