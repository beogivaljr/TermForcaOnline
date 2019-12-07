#!/usr/bin/python3
# Python 3.7 or higher required

from shared_descubra_palavra import *
import logging
import threading
import time
import socket


# Mensagens para o servidor
TITLE_SERVER = 'Servidor:'
TITLE_SERVER_RECEIVER = 'Receptor de conexões:'
TITLE_GAME = 'Jogo:'
MSG_SERVER_STARTED = 'Servidor iniciado'
MSG_PRESS_TO_STOP = 'Pressione ENTER para encerrar o servidor: '
MSG_WAITING_NEW_PLAYERS = 'Esperando novos jogadores...'
MSG_CONNECTED = 'conectado'
MSG_HANDLING = 'Tratando'
MSG_TOTAL_CONNECTED_PLAYERS = 'Total de jogadores na fila ->'
MSG_DISCONNECTED = 'Desconectado.'
MSG_SERVER_INTERRUPT = 'Servidor interrompido.'
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


# Modelo de jogador
class Player:
    def __init__(self, connected_server, connection: socket, address):
        self.thread_id = threading.get_ident()  # Saves the id of the thread
        self.server = connected_server  # Server where he/she is connected
        self.connection = connection  # Socket object
        self.address = address  # (ip, port)

    def __enter__(self):
        server.connected_players.append(self)
        server.log(MSG_HANDLING)
        server.log_total_players()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        server.connected_players.remove(self)
        server.log(MSG_DISCONNECTED)
        server.log_total_players()
        self.connection.shutdown(socket.SHUT_RDWR)
        self.connection.close()

    thread_id = 0
    nickname = None
    words_guessed: [str] = []
    won = False

    def get_ip(self):
        return self.address[0]


# Modelo do Jogo em andamento
class Game:
    def __init__(self, thread_id, chosen_word):
        self.thread_id = thread_id
        self.chosen_word = chosen_word

    timer = 10  # Tempo total de jogo em segundos


# Modelo do Servidor
class Server:
    def __init__(self):
        self.thread_id = threading.get_ident()  # Saves the id of the thread of the caller of the start

    _input_prompt = None  # Any input promt being requested from the server master
    server_receiver_thread_id = None  # Id for the receiver thread
    connected_players: [Player] = []  # Active players list
    running_game: Game = None

    # MARK - Flow methods

    def start(self):
        # Create new thread, bind it to this thread and start it
        self.log(MSG_SERVER_STARTED)
        connection_receiver_thread = threading.Thread(target=self._receive_connections)
        connection_receiver_thread.daemon = True
        connection_receiver_thread.start()

        # Waits for the server master to stop execution
        self._input_prompt = MSG_PRESS_TO_STOP
        input(f'{self._input_prompt}\n')
        self._input_prompt = None

        self.log(MSG_SERVER_INTERRUPT)

    def _receive_connections(self):
        self.server_receiver_thread_id = threading.get_ident()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, PORT))
                s.listen()
                while True:
                    self.log(MSG_WAITING_NEW_PLAYERS)
                    (connection, address) = s.accept()  # Blocks until connection

                    # After connection succeded
                    self.log(f'{address} {MSG_CONNECTED}')
                    t = threading.Thread(target=self._handle, args=(connection, address))
                    t.daemon = True
                    t.start()

            except Exception as e:
                self.log(e)

    # First responder to direct and handle player connections
    def _handle(self, connection, address):
        with Player(self, connection, address) as player:
            if len(self.connected_players) == 1:
                self.handle_as_first(player)
            else:
                self.handle_guessing(player)

    # Trata o primeiro usuário, responsável por digitar a palavra que vão tentar adivinhar
    # Temos uma thread dessas só para o primeiro usuário
    def handle_as_first(self, player: Player):
        player.thread_id = threading.get_ident()  # Captura o id da thread do primeiro jogador
        try:
            while True:
                request = decode(player.connection.recv(MAX_PACK_LENGTH))  # Aguarda a receber a requisição

                # Após a resposta bem sucedida
                if API_END in request:  # Checa se a requisição tem fim no cabeçalho
                    response = translate_first_players(request,
                                                       player)  # Traduz a requisição e gera uma resposta
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

    # Thread paralela que trata os usuários que vão tentar adivinhar a palavra proposta pelo primeiro jogador
    # Temos uma thread dessas por usuário
    def handle_guessing(self, player: Player):
        player.thread_id = threading.get_ident()  # Captura o id da thread do jogador
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

    # MARK - Helper methods

    # Imprime log com o horário e um apelido para a thread
    def log(self, any_object):
        form = '\033[F%(asctime)s - %(message)s'
        logging.basicConfig(format=form, level=logging.INFO, datefmt='%H:%M:%S')

        if self._input_prompt:
            logging.info(f'{self._get_thread_title()} {any_object}\033[K\n{self._input_prompt}')
        else:
            print()
            logging.info(f'{self._get_thread_title()} {any_object}')

    # Devolve um títuo adequada para esta thread atual
    def _get_thread_title(self):
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        if thread_id == self.thread_id:
            return TITLE_SERVER
        elif self.server_receiver_thread_id and thread_id == self.server_receiver_thread_id:
            return TITLE_SERVER_RECEIVER
        elif self.running_game and thread_id == self.running_game.thread_id:
            return TITLE_GAME
        else:
            for player in self.connected_players:
                if player.thread_id == thread_id:
                    if player.nickname:
                        return f'{thread_name} ({player.nickname}):'
                    else:
                        return f'{thread_name} ({player.get_ip()}):'

        # If could not identify thread user it's name
        return f'{thread_name}:'

    # Imprime o todal de jogadores conectados
    def log_total_players(self):
        self.log(f'{MSG_TOTAL_CONNECTED_PLAYERS} {len(self.connected_players)}')


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
    while chosen_word is None:  # Aguarda, se necessário, a palavra do jogo ser escolhida
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
            if guessed_word.lower() == chosen_word.lower():
                player.won = True
                game_status_needs_update = True  # Atualiza o jogo
                return f'{API_POST}{API_WON}{API_END}'
            else:
                player.words_guessed.append(guessed_word)
                game_status_needs_update = True  # Atualiza o jogo
                return WRONG_GUESS

    else:
        return f'{API_POST}{API_FIRST}{API_BAD_REQUEST}'





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
    global game_thread_id
    game_thread_id = threading.get_ident()
    global chosen_word
    chosen_word = word
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
    last_status_description += f'\n{CLT_MSG_CHOSEN_WORD} {chosen_word}'
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
    server = Server()
    server.start()
