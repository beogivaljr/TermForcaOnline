#!/usr/bin/python3
# Python 3.7 or higher required

from shared_descubra_palavra import *
import logging
import threading
import time
import socket


# Modelo de jogador
class Player:
    def __init__(self, connection, address):
        self.connection = connection  # socket object
        self.address = address  # (ip, port)

    def get_ip(self):
        return self.connection[0]

    thread_id = 0
    nickname = 'Sem Apelido'
    words_guessed: [str] = []
    won = False


# Mensagens para o servidor
TITLE_MAIN = 'Servidor:'
TITLE_MAIN_GAME = 'Jogo:'
TITLE_PLAYER = 'Jogador'
MSG_WAITING_NEW_PLAYERS = 'Esperando novos jogadores...'
MSG_CONNECTED = 'Conectado'
MSG_TOTAL_CONNECTED_PLAYERS = 'Total de jogadores ->'
MSG_DISCONNECTED = 'Desconectado.'
MSG_SERVER_INTERRUPT = 'Partida iniciada, não aceitando mais conexões.'
MSG_GAME_STARTED = 'Jogo iniciado'
MSG_CHOSEN_WORD = 'A palavra escolhida foi'
MSG_PLAYER_GUESSED = 'Chutou'

# Mensagens para o cliente
CLT_MSG_BAR = '##########'
CLT_MSG_TOO_LONG_WORD = 'Palavra muito longa, por favor escolha uma palavra mais curta.'
CLT_MSG_CHOSEN_WORD = 'A palavra escolhida foi:'
CLT_MSG_FIRST_PLAYER_WON = 'O jogador quem escolheu a palavra ganhou!'
CLT_MSG_FIRST_PLAYER_LOST = 'O jogador quem escolheu a palavra perdeu.'
CLT_MSG_OTHER_WINNING_PLAYERS = 'Os jogadores que acertaram foram:'
CLT_MSG_NO_WINNING_PLAYERS = 'Ninguém acertou.'
CLT_MSG_GAME_OVER = 'Fim de Jogo!'

# Constantes do servidor
TOTAL_GAME_TIME = 10  # Tempo total de jogo em segundos
STOP_RECEIVING = 'STOP_RECEIVING '
WRONG_GUESS = 'WRONG_GUESS '

# Variáveis globais do servidor
connected_players: [Player] = []  # Lista com os jogadores ativos
main_thread_id = 0
main_game_thread_id = 0
game_word = None
current_game_time = TOTAL_GAME_TIME
game_status_needs_update = False


# Recebe um socket que possa servir de porta de entrada para acietar novas conexões
# Aguarda novas conexões através desse socket
# Devolve um novo jogador (Player), já adicionado à lista de jogadores conectados
def get_new_players_from(active_socket: socket):
    (connection, address) = active_socket.accept()  # Aguarda conexões

    new_connected_player = Player(connection, address)
    connected_players.append(new_connected_player)
    return new_connected_player


# Devolve um títuo adequada para esta thread atual
def get_thread_title():
    current_thread_id = threading.current_thread().ident

    if current_thread_id is main_thread_id:
        return TITLE_MAIN

    elif current_thread_id is main_game_thread_id:
        return TITLE_MAIN_GAME

    else:
        for player in connected_players:
            if player.thread_id == current_thread_id:
                return f'{TITLE_PLAYER} {player.nickname}:'

    return f'Thread {current_thread_id}:'


# Imprime log com o horário e um apelido para a thread
def log(any_object):
    form = '%(asctime)s - %(message)s'
    logging.basicConfig(format=form, level=logging.INFO, datefmt='%H:%M:%S')

    logging.info(f'{get_thread_title()} {any_object}')


# Devolve o total de jogadores conectados
def total_connected_players():
    return len(connected_players)


# Imprime o todal de jogadores conectados
def log_total_players():
    log(f'{MSG_TOTAL_CONNECTED_PLAYERS} {total_connected_players()}')


# Disconecta o jogador e o remove da lista de jogadores
def disconnect(player: Player):
    if player in connected_players:
        player.connection.close()
        log(MSG_DISCONNECTED)
        connected_players.remove(player)
        log_total_players()  # Vai aparecer com o id da thread, pois o jogador já não estará mais conectado


# TODO: Função que gera dicas
# Gera uma 'str' de dica a partir da palavra do jogo (game_word)
# A dica deve conter exatamente duas letras e '#' indicando letras escondidas
# A escolha das letras a serem escondidas deve ser aleatória
def get_word_tip():
    while game_word is None:  # Aguarda, se necessário, a palavra do jogo ser escolhida
        pass
    return 'D##a'


# Recebe a requisição (str) dos outros jogadores
# Traduz os comandos recebidos pelo cliente através da requisição
# Devolve a resposta adequada para ser enviada ao cliente
def translate_other_players(request: str, player: Player):
    global game_status_needs_update
    if f'{API_POST}{API_TOUCH}' in request:
        nickname = get_content_from(request)
        if len(nickname) <= MAX_INPUT_LENGTH:
            player.nickname = nickname
            log(MSG_CONNECTED)
            game_status_needs_update = True  # Atualiza o jogo
            word_tip = get_word_tip()
            return f'{API_POST}{API_TIP}{API_SUCCESS}{API_END}{word_tip}'
        else:
            return f'{API_POST}{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

    elif f'{API_POST}{API_USER_INPUT}' in request:
        guessed_word = get_content_from(request)  # Nova string contendo a entrada do usuário
        if len(guessed_word) <= MAX_INPUT_LENGTH:
            log(f'{MSG_PLAYER_GUESSED} {guessed_word}')
            if guessed_word.lower() == game_word.lower():
                player.won = True
                game_status_needs_update = True  # Atualiza o jogo
                return f'{API_POST}{API_WON}{API_END}'
            else:
                player.words_guessed.append(guessed_word)
                game_status_needs_update = True  # Atualiza o jogo
                return WRONG_GUESS

    else:
        return f'{API_POST}{API_FIRST}{API_BAD_REQUEST}'


# Thread paralela que trata os usuários que vão tentar adivinhar a palavra proposta pelo primeiro jogador
# Temos uma thread dessas por usuário
def handle_guessing(player: Player):
    player.thread_id = threading.current_thread().ident  # Captura o id da thread do jogador
    send = player.connection.sendall
    try:
        while True:
            request = decode(player.connection.recv(MAX_PACK_LENGTH))  # Aguarda a receber a requisição

            # Após a resposta bem sucedida
            if API_END in request:  # Checa se a requisição tem fim no cabeçalho
                response = translate_other_players(request, player)  # Traduz a requisição e gera uma resposta
                if API_TIP in response:
                    send(encode(response))
                    while current_game_time == TOTAL_GAME_TIME:
                        pass  # Fica preso esperando o jogo começar para voltar a receber do usuário
                elif API_WON in response:
                    send(encode(response))
                    break  # Encerra essa thread e para de receber deste cliente
                elif API_USER_ERROR in response:
                    send(encode(response))
                else:
                    pass  # Não evia nada, pois o status já está sendo enviado por outra thread
            else:
                # Envia 400 e encerra a conexão
                send(encode(API_BAD_REQUEST))
                disconnect(player)
                break

    except BrokenPipeError as e:
        log(f'{player.nickname} {e}')
        disconnect(player)
    except ConnectionResetError as e:
        log(f'{player.nickname} {e}')
        disconnect(player)
    except Exception as e:
        logging.exception(e)
        send(encode(API_ERROR_500))
        disconnect(player)


# Recebe a requisição (str) do primeiro jogador
# Traduz os comandos recebidos pelo cliente através da requisição
# Devolve a resposta adequada para ser enviada ao cliente
def translate_first_players(request: str, player: Player):
    if f'{API_POST}{API_TOUCH}' in request:
        nickname = get_content_from(request)
        if len(nickname) <= MAX_INPUT_LENGTH:
            player.nickname = nickname
            log(MSG_CONNECTED)
            return f'{API_POST}{API_FIRST}{API_TOUCH}{API_SUCCESS}'
        else:
            return f'{API_POST}{API_FIRST}{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

    elif f'{API_POST}{API_USER_INPUT}' in request:
        chosen_word = get_content_from(request)  # Nova string contendo a entrada do usuário
        if len(chosen_word) <= MAX_INPUT_LENGTH:
            main_game_tread = threading.Thread(target=setup_game_with, args=(chosen_word,))
            main_game_tread.start()
            log(f'{MSG_CHOSEN_WORD} \'{chosen_word}\'')
            return f'{API_POST}{API_FIRST}{API_SUCCESS}'
        else:
            return f'{API_POST}{API_FIRST}{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'
    elif f'{API_POST}{API_START}' in request:
        log(MSG_GAME_STARTED)
        send_all_players(API_START)  # Avisa todos os jogadores que o jogo começou
        run_game_timer()
        return STOP_RECEIVING

    else:
        return f'{API_POST}{API_FIRST}{API_BAD_REQUEST}'


# Thread paralela que trata o primeiro usuário, responsável por digitar a palavra que vão tentar adivinhar
# Temos uma thread dessas só para o primeiro usuário
def handle_first(player: Player):
    player.thread_id = threading.current_thread().ident  # Captura o id da thread do primeiro jogador
    try:
        while True:
            request = decode(player.connection.recv(MAX_PACK_LENGTH))  # Aguarda a receber a requisição

            # Após a resposta bem sucedida
            if API_END in request:  # Checa se a requisição tem fim no cabeçalho
                response = translate_first_players(request, player)  # Traduz a requisição e gera uma resposta
                if STOP_RECEIVING in response:
                    break
                else:
                    player.connection.sendall(encode(response))  # Envia a resposta ao cliente
            else:
                # Envia 400 e encerra a conexão
                player.connection.sendall(encode(API_BAD_REQUEST))
                disconnect(player)
                break

    except BrokenPipeError as e:
        log(f'{player.nickname} {e}')
        disconnect(player)
    except ConnectionResetError as e:
        log(f'{player.nickname} {e}')
        disconnect(player)
    except Exception as e:
        logging.exception(e)
        player.connection.sendall(encode(API_ERROR_500))
        disconnect(player)


# Envia o 'status_description' do jogo para todas as conexões ativas
def send_all_players(message: str, is_last: bool = False):
    for player in connected_players:
        send = player.connection.sendall
        try:
            if is_last:
                send(encode(f'{API_POST}{API_GAME_OVER}{API_DIRECT_MSG}{API_END}{message}'))
            else:
                send(encode(f'{API_POST}{API_DIRECT_MSG}{API_END}{message}'))
        except BrokenPipeError as e:
            log(f'{player.nickname} {e}')
            disconnect(player)
        except ConnectionResetError as e:
            log(f'{player.nickname} {e}')
            disconnect(player)
        except Exception as e:
            logging.exception(e)
            send(encode(API_ERROR_500))
            disconnect(player)


# TODO: Função que monta uma str com o do status do jogo
# IMPORTANTE - Só pode ser chamada por uma thread pois será fonte de conflitos
# Função responsável por montar e enviar a descrição do status do jogo
def update_game_status():
    status_description = 'Status do jogo'
    send_all_players(status_description)


# Thread responsável pelo jogo corrente
def setup_game_with(word):
    global main_game_thread_id
    main_game_thread_id = threading.current_thread().ident
    global game_word
    game_word = word
    global game_status_needs_update

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
    s.close()
    global current_game_time
    global game_status_needs_update
    if current_game_time > 0:
        current_game_time -= 1
        threading.Timer(1, function=run_game_timer).start()

        # Pede atualização do status a cada dois segundos
        if current_game_time % 2 == 0:
            game_status_needs_update = True


# Checa se o primeiro jogador ganhou
# Devolve mensagem dizendo se sim ou se não
def did_first_player_won():
    total_hits = 1  # Para desconsiderar a vitória do primeiro jogador

    for player in connected_players:
        if player.won:
            total_hits += 1

    if 1 < total_hits < total_connected_players():
        return CLT_MSG_FIRST_PLAYER_WON
    else:
        return CLT_MSG_FIRST_PLAYER_LOST


# Checa os jogadores adivinhadores ganhadores
# Devolve uma mensagem parabenizando os ganhadores
def congratulate_other_wining_players():
    congrats_msg = CLT_MSG_OTHER_WINNING_PLAYERS

    for player in connected_players:
        if player.won:
            congrats_msg += f'\n{player.nickname}'

    if congrats_msg is CLT_MSG_OTHER_WINNING_PLAYERS:
        return CLT_MSG_NO_WINNING_PLAYERS
    else:
        return congrats_msg


# Finaliza o jogo
# Gera e envia o ultimo status do jogo, contendo ganhadores e aviso de fim de jogo
# Disconecta todos os jogadores
def finish_game():
    last_status_description = f'\n{CLT_MSG_BAR}'
    last_status_description += f'\n{CLT_MSG_GAME_OVER}'
    last_status_description += f'\n{CLT_MSG_CHOSEN_WORD} {game_word}'
    last_status_description += f'\n{did_first_player_won()}'
    last_status_description += f'\n{congratulate_other_wining_players()}'
    last_status_description += f'\n{CLT_MSG_BAR}'

    send_all_players(last_status_description, is_last=True)

    global current_game_time
    current_game_time = TOTAL_GAME_TIME  # Reseta o timer
    # Disconecta todos os jogadores
    while total_connected_players() > 0:
        disconnect(connected_players[0])
    log(CLT_MSG_GAME_OVER)


# Execussão principal do programa
if __name__ == '__main__':
    main_thread_id = threading.current_thread().ident  # Captura o id da main thread para futura identificação
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
            s.listen()
            while True:
                log(MSG_WAITING_NEW_PLAYERS)
                new_player = get_new_players_from(s)  # Aguarda novas conexões

                # Após conexão bem sucedida
                if total_connected_players() == 1:
                    t = threading.Thread(target=handle_first, args=(new_player,))
                else:
                    t = threading.Thread(target=handle_guessing, args=(new_player,))
                t.start()
                log_total_players()
        except ConnectionAbortedError:
            log(MSG_SERVER_INTERRUPT)
