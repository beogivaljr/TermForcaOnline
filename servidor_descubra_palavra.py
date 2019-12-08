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
MSG_SERVER_STARTED = 'Servidor iniciado'
MSG_PRESS_TO_STOP = 'Pressione ENTER para encerrar o servidor: '
MSG_WAITING_NEW_PLAYERS = 'Esperando novos jogadores...'
MSG_NOT_WAITING_NEW_PLAYERS = 'Bloqueando conexões'
MSG_CONNECTED = 'Conectado'
MSG_HANDLING = 'Tratando'
MSG_TOTAL_CONNECTED_PLAYERS = 'Total de jogadores na fila ->'
MSG_DISCONNECTED = 'Desconectado.'
MSG_SERVER_INTERRUPT = 'Servidor interrompido.'
MSG_GAME_STARTED = 'Jogo iniciado'
MSG_CHOSEN_WORD = 'A palavra escolhida foi'
MSG_PLAYER_GUESSED = 'Chutou'
MSG_NO_RUNNING_GAME = 'Nenhum jogo ativo'
MSG_TIMER_ON = 'Timer iniciado'
MSG_TIMER_OFF = 'Timer finalizado'
MSG_TIMER_INVALIDATED = 'Timer invalidado'

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
    def __init__(self, connection: socket, address):
        self.thread_id = threading.get_ident()  # Saves the id of the thread
        self.connection = connection  # Socket object
        self.address = address  # (ip, port)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.send_disconnection_message()
        self.connection.close()

    thread_id = 0
    nickname = None
    words_guessed: [str] = []
    won = False

    # MARK - Helper methods

    def get_ip(self):
        return self.address[0]

    # Try to send and error msg to the client before disconnection
    def send_disconnection_message(self, m=''):
        try:  # Tries to warn the player of the internal server error
            self.connection.sendall(encode(m))
            self.connection.shutdown(socket.SHUT_RDWR)
        except BrokenPipeError:
            return
        except ConnectionResetError:
            return
        except OSError:
            return
        except Exception as e:
            logging.exception(e)


# Modelo do Jogo em andamento
class Game:
    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for player in self.connected_players:
            player.send_disconnection_message()
            player.connection.close()
            self.connected_players.remove(player)

    connected_players: [Player] = []  # Active players list
    chosen_word = None
    timer = 20  # Total time for each game
    is_done = False

    # Get master game
    def get_first_player(self):
        return self.connected_players[0]

    # Returns the status of the current game
    def get_status(self):
        return 'Game status'


# Modelo do Servidor
class Server:
    def __init__(self):
        self.thread_id = threading.get_ident()  # Saves the id of the thread of the caller of the start

    _input_prompt = None  # Any input promt being requested from the server master
    _server_receiver_thread_id = None  # Id for the receiver thread
    _running_game: Game = None
    _accepting_connections = True

    # MARK - Flow methods

    # Timer for each game
    def run_game_timer(self):
        self.log(MSG_TIMER_ON)
        while not self._running_game.is_done:
            if self._running_game.timer > 0:
                time.sleep(1)
                self._running_game.timer -= 1
            else:
                self.log(MSG_TIMER_OFF)
                self._game_over()
                break
        else:
            self.log(MSG_TIMER_INVALIDATED)

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
        self._server_receiver_thread_id = threading.get_ident()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, PORT))
                s.listen()
                while True:
                    if self._accepting_connections:
                        self.log(MSG_WAITING_NEW_PLAYERS)
                        (connection, address) = s.accept()  # Blocks until connection

                        # After connection succeded
                        if self._accepting_connections:  # Check if still allowed
                            self.log(f'{address} {MSG_CONNECTED}')
                            threading.Thread(target=self._handle, args=(connection, address)).start()
                        else:
                            connection.close()
                            self.log(MSG_NOT_WAITING_NEW_PLAYERS)

            except Exception as e:
                logging.exception(e)

    # First responder to direct and handle player connections
    def _handle(self, connection, address):
        if not self._running_game or self._running_game.is_done:
            with Game() as new_game:  # Will tie the game to the first player
                with Player(connection, address) as player:
                    new_game.connected_players.append(player)
                    player.thread_id = threading.get_ident()  # Saves player's thread id
                    self._running_game = new_game  # Saves new game as the servers running game

                    self._handle_as_first(player)
                self.log(MSG_DISCONNECTED)
            self.log_total_players()
            self._running_game.is_done = True
            self._accepting_connections = True
        else:
            pass  # self.handle_guessing(player)

    # Handles this player as the first, which means he is going to chose the game word
    def _handle_as_first(self, player: Player):
        try:
            while True:
                req = decode(player.connection.recv(MAX_PACK_LENGTH))  # Waits for request

                # After successful request
                if is_valid(req):  # Check if request is valid
                    response = self._translate_first_players(req, player)  # Translate request and generate response
                    player.connection.sendall(encode(response))  # Send response

                else:  # Send bad request and closes connection
                    player.send_disconnection_message(API_BAD_REQUEST)
                    break

        except BrokenPipeError:
            return
        except ConnectionResetError:
            return
        except OSError:
            return
        except Exception as e:
            logging.exception(e)
            player.send_disconnection_message(API_ERROR_500)

    # Receives the first client's request as a String
    # Process request and generates a response
    # Returns the response
    def _translate_first_players(self, request: str, player: Player):
        if API_POST in request:
            if API_NICKNAME in request:
                nickname = get_content_from(request)
                if len(nickname) <= MAX_INPUT_LENGTH:
                    player.nickname = nickname  # Saves player name
                    self.log(MSG_HANDLING)
                    return f'{API_SUCCESS}{API_NICKNAME}'
                else:
                    return f'{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

            elif API_USER_INPUT in request:
                chosen_word = get_content_from(request)
                if len(chosen_word) <= MAX_INPUT_LENGTH:
                    self._running_game.chosen_word = chosen_word
                    self.log(f'{MSG_CHOSEN_WORD} \'{chosen_word}\'')
                    return API_SUCCESS
                else:
                    return f'{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'
            elif API_START_GAME in request:
                self._start_game()
                return API_SUCCESS
            else:
                return API_BAD_REQUEST

        elif API_GET in request:
            if API_STATUS in request:
                return self._running_game.get_status()

    # Starts the game
    def _start_game(self):
        self._send_start_warning()  # Warn players that the game has started
        self._accepting_connections = False
        threading.Thread(target=self.run_game_timer).start()
        self.log(MSG_GAME_STARTED)

    # Finishes the game
    def _game_over(self):
        for player in self._running_game.connected_players:
            player.send_disconnection_message(API_GAME_OVER)
            player.connection.close()
        self.log(CLT_MSG_GAME_OVER)

    # MARK - Helper methods

    # Attempts to send all players a command
    def _send_start_warning(self):
        for player in self._running_game.connected_players:
            if player is not self._running_game.get_first_player():
                try:
                    player.connection.sendall(encode(f'{API_POST}{API_START_GAME}{API_END}'))
                except BrokenPipeError:
                    pass
                except ConnectionResetError:
                    pass
                except OSError:
                    pass
                except Exception as e:
                    logging.exception(e)
                    player.send_disconnection_message(API_ERROR_500)

    # Prints log
    def log(self, any_object):
        form = '\033[F%(asctime)s - %(message)s'
        logging.basicConfig(format=form, level=logging.INFO, datefmt='%H:%M:%S')

        if self._input_prompt:
            logging.info(f'{self._get_thread_title()} {any_object}\033[K\n{self._input_prompt}')
        else:
            print()
            logging.info(f'{self._get_thread_title()} {any_object}')

    # Returns title for this thread
    def _get_thread_title(self):
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        if thread_id == self.thread_id:
            return TITLE_SERVER
        elif self._server_receiver_thread_id and thread_id == self._server_receiver_thread_id:
            return TITLE_SERVER_RECEIVER
        else:
            for player in self._running_game.connected_players:
                if player.thread_id == thread_id:
                    if player.nickname:
                        return f'{thread_name} ({player.nickname}):'
                    else:
                        return f'{thread_name} ({player.get_ip()}):'

        # If could not identify thread user it's name
        return f'{thread_name}:'

    # Prints total connected players
    def log_total_players(self):
        if self._running_game:
            self.log(f'{MSG_TOTAL_CONNECTED_PLAYERS} {len(self._running_game.connected_players)}')
        else:
            self.log(MSG_NO_RUNNING_GAME)

# # Thread paralela que trata os usuários que vão tentar adivinhar a palavra proposta pelo primeiro jogador
# # Temos uma thread dessas por usuário
# def handle_guessing(self, player: Player):
#     send = player.connection.sendall
#     try:
#         while True:
#             request = decode(player.connection.recv(MAX_PACK_LENGTH))  # Aguarda a receber a requisição
#
#             # Após a resposta bem sucedida
#             if API_END in request:  # Checa se a requisição tem fim no cabeçalho
#                 response = translate_other_players(request, player)  # Traduz a requisição e gera uma resposta
#                 if API_TIP in response:
#                     send(encode(response))
#                     while current_game_time == TOTAL_GAME_TIME:
#                         pass  # Fica preso esperando o jogo começar para voltar a receber do usuário
#                 elif API_WON in response:
#                     send(encode(response))
#                     break  # Encerra essa thread e para de receber deste cliente
#                 elif API_USER_ERROR in response:
#                     send(encode(response))
#                 else:
#                     pass  # Não evia nada, pois o status já está sendo enviado por outra thread
#             else:
#                 # Envia 400 e encerra a conexão
#                 send(encode(API_BAD_REQUEST))
#                 disconnect(player)
#                 break
#
#     except BrokenPipeError as e:
#         log(f'{player.nickname} {e}')
#         disconnect(player)
#     except ConnectionResetError as e:
#         log(f'{player.nickname} {e}')
#         disconnect(player)
#     except Exception as e:
#         logging.exception(e)
#         send(encode(API_ERROR_500))
#         disconnect(player)

# # TODO: Função que gera dicas
# # Gera uma 'str' de dica a partir da palavra do jogo (game_word)
# # A dica deve conter exatamente duas letras e '#' indicando letras escondidas
# # A escolha das letras a serem escondidas deve ser aleatória
# def get_word_tip():
#     while chosen_word is None:  # Aguarda, se necessário, a palavra do jogo ser escolhida
#         pass
#     return 'D##a'
#
#
# # Recebe a requisição (str) dos outros jogadores
# # Traduz os comandos recebidos pelo cliente através da requisição
# # Devolve a resposta adequada para ser enviada ao cliente
# def translate_other_players(request: str, player: Player):
#     global game_status_needs_update
#     if f'{API_POST}{API_NICKNAME}' in request:
#         nickname = get_content_from(request)
#         if len(nickname) <= MAX_INPUT_LENGTH:
#             player.nickname = nickname
#             log(MSG_CONNECTED)
#             game_status_needs_update = True  # Atualiza o jogo
#             word_tip = get_word_tip()
#             return f'{API_POST}{API_TIP}{API_SUCCESS}{API_END}{word_tip}'
#         else:
#             return f'{API_POST}{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'
#
#     elif f'{API_POST}{API_USER_INPUT}' in request:
#         guessed_word = get_content_from(request)  # Nova string contendo a entrada do usuário
#         if len(guessed_word) <= MAX_INPUT_LENGTH:
#             log(f'{MSG_PLAYER_GUESSED} {guessed_word}')
#             if guessed_word.lower() == chosen_word.lower():
#                 player.won = True
#                 game_status_needs_update = True  # Atualiza o jogo
#                 return f'{API_POST}{API_WON}{API_END}'
#             else:
#                 player.words_guessed.append(guessed_word)
#                 game_status_needs_update = True  # Atualiza o jogo
#                 return WRONG_GUESS
#
#     else:
#         return f'{API_POST}{API_FIRST}{API_BAD_REQUEST}'

# # Checa se o primeiro jogador ganhou
# # Devolve mensagem dizendo se sim ou se não
# def did_first_player_won():
#     total_hits = 1  # Para desconsiderar a vitória do primeiro jogador
#
#     for player in connected_players:
#         if player.won:
#             total_hits += 1
#
#     if 1 < total_hits < total_connected_players():
#         return CLT_MSG_FIRST_PLAYER_WON
#     else:
#         return CLT_MSG_FIRST_PLAYER_LOST
#
#
# # Checa os jogadores adivinhadores ganhadores
# # Devolve uma mensagem parabenizando os ganhadores
# def congratulate_other_wining_players():
#     congrats_msg = CLT_MSG_OTHER_WINNING_PLAYERS
#
#     for player in connected_players:
#         if player.won:
#             congrats_msg += f'\n{player.nickname}'
#
#     if congrats_msg is CLT_MSG_OTHER_WINNING_PLAYERS:
#         return CLT_MSG_NO_WINNING_PLAYERS
#     else:
#         return congrats_msg


# # Finaliza o jogo
# # Gera e envia o ultimo status do jogo, contendo ganhadores e aviso de fim de jogo
# # Disconecta todos os jogadores
# def finish_game():
#     last_status_description = f'\n{CLT_MSG_BAR}'
#     last_status_description += f'\n{CLT_MSG_GAME_OVER}'
#     last_status_description += f'\n{CLT_MSG_CHOSEN_WORD} {chosen_word}'
#     last_status_description += f'\n{did_first_player_won()}'
#     last_status_description += f'\n{congratulate_other_wining_players()}'
#     last_status_description += f'\n{CLT_MSG_BAR}'
#
#     send_all_players(last_status_description, is_last=True)
#
#     global current_game_time
#     current_game_time = TOTAL_GAME_TIME  # Reseta o timer
#     # Disconecta todos os jogadores
#     while total_connected_players() > 0:
#         disconnect(connected_players[0])
#     log(CLT_MSG_GAME_OVER)


# Execussão principal do programa
if __name__ == '__main__':
    server = Server()
    server.start()
