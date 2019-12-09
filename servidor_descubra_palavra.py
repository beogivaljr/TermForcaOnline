#!/usr/bin/python3
# Python 3.7 or higher required

from shared_descubra_palavra import *
import logging
import threading
import time
import socket
import random


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
CLT_MSG_BAR = '####################'
CLT_MSG_TOO_LONG_WORD = 'Palavra muito longa, por favor escolha uma palavra mais curta.'
CLT_MSG_CHOSEN_WORD = 'A palavra escolhida foi:'
CLT_MSG_FIRST_PLAYER_WON = 'O jogador quem escolheu a palavra ganhou!'
CLT_MSG_FIRST_PLAYER_LOST = 'O jogador quem escolheu a palavra perdeu.'
CLT_MSG_OTHER_WINNING_PLAYERS = 'Os jogadores que acertaram foram:'
CLT_MSG_NO_WINNING_PLAYERS = 'Ninguém acertou.'
CLT_MSG_GAME_OVER = 'Fim de Jogo!'
CLT_MSG_GAME_TITLE = 'Tempo restante: '
CLT_MSG_TIP = 'Sua dica é '


# Modelo de jogador
class Player:
    def __init__(self, connection: socket, address):
        self.thread_id = threading.get_ident()  # Saves the id of the thread
        self.connection = connection  # Socket object
        self.address = address  # (ip, port)

        self.nickname = None
        self.words_guessed: [str] = []
        self.word_tip = None
        self.won = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.send_disconnection_message()
        self.connection.close()

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
    def __init__(self):
        self.connected_players: [Player] = []  # Active players list
        self.chosen_word = None
        self.timer = 20  # Total time for each game
        self.is_done = False
        self.last_status = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for player in self.connected_players:
            player.send_disconnection_message()
            player.connection.close()
            self.connected_players.remove(player)

    # Get master game
    def get_first_player(self):
        return self.connected_players[0]

    # Returns the status of the current game
    def get_status(self, with_tip=None):
        if self.is_done:
            while not self.last_status:
                pass
            return self.last_status
        else:
            status_description = f'\n{CLT_MSG_BAR}'
            status_description += f'\n{CLT_MSG_GAME_TITLE}{self.timer}s'
            if with_tip:
                status_description += f'\n{CLT_MSG_TIP}\'{with_tip}\''
            for player in self.connected_players:
                if player is not self.get_first_player():
                    status_description += f'\n'
                    status_description += f'\n{player.nickname} chutou:'
                    for word in player.words_guessed:
                        status_description += f'\n{word}'
            status_description += f'\n{CLT_MSG_BAR}\n'
            return status_description

    # returns the last status description of the game
    def generate_last_status(self):
        last_status_description = f'\n{CLT_MSG_BAR}'
        last_status_description += f'\n{CLT_MSG_GAME_OVER}'
        last_status_description += f'\n{CLT_MSG_CHOSEN_WORD} {self.chosen_word}'
        last_status_description += f'\n{self._did_first_player_won()}'
        last_status_description += f'\n{self._congratulate_other_wining_players()}'
        last_status_description += f'\n{CLT_MSG_BAR}\n'
        self.last_status = last_status_description

    def _did_first_player_won(self):
        total_hits = 1  # To disconsider first player

        for player in self.connected_players:
            if player.won:
                total_hits += 1

        if 1 < total_hits < len(self.connected_players):
            return CLT_MSG_FIRST_PLAYER_WON
        else:
            return CLT_MSG_FIRST_PLAYER_LOST

    # Check for winning players
    # Return message congratulating them
    def _congratulate_other_wining_players(self):
        congrats_msg = CLT_MSG_OTHER_WINNING_PLAYERS
        for player in self.connected_players:
            if player.won:
                congrats_msg += f'\n{player.nickname}'

        if congrats_msg is CLT_MSG_OTHER_WINNING_PLAYERS:
            return CLT_MSG_NO_WINNING_PLAYERS
        else:
            return congrats_msg

    def generate_all_word_tips(self, amount_letters_to_keep=2):
        for player in self.connected_players:
            word = self.chosen_word
            vector = list(word)
            amount_letters_to_hide = len(vector) - amount_letters_to_keep
            L = len(vector) - 1
            done = False
            if amount_letters_to_hide <= 0:
                return word
            while not done:
                r = random.randint(0, L)
                vector[r] = '#'
                if vector.count('#') >= amount_letters_to_hide or vector.count('#') == (L + 1):
                    done = True
            secret = ''.join(vector)
            player.word_tip = secret

    def force_drop_all_players(self):
        for player in self.connected_players:
            try:  # Tries to warn the player of the internal server error
                player.connection.shutdown(socket.SHUT_RDWR)
                player.connection.close()
            except BrokenPipeError:
                return
            except ConnectionResetError:
                return
            except OSError:
                return
            except Exception as e:
                logging.exception(e)


# Modelo do Servidor
class Server:
    def __init__(self):
        self.thread_id = threading.get_ident()  # Saves the id of the thread of the caller of the start

        self._input_prompt = None  # Any input promt being requested from the server master
        self._server_receiver_thread_id = None  # Id for the receiver thread
        self._running_game = None
        self._accepting_connections = True

    # MARK - Flow methods

    def start(self):
        self.log(MSG_SERVER_STARTED)
        self._input_prompt = MSG_PRESS_TO_STOP
        # Create new thread
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            threading.Thread(target=self._receive_connections, args=(s,)).start()

            # Waits for the server master to stop execution
            input(f'{self._input_prompt}\n')
        self._input_prompt = None
        if not self._running_game:
            time.sleep(0.5)  # Waits for new game to finish starting
        self._running_game.force_drop_all_players()

        self.log(MSG_SERVER_INTERRUPT)

    def _receive_connections(self, s):
        self._server_receiver_thread_id = threading.get_ident()
        try:
            s.bind((HOST, PORT))
            s.listen()
            while self._input_prompt:
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

        except BrokenPipeError:
            return
        except ConnectionResetError:
            return
        except OSError:
            return
        except Exception as e:
            logging.exception(e)

    # First responder to direct and handle player connections
    def _handle(self, connection, address):
        if not self._running_game or self._running_game.is_done:
            with Game() as new_game:  # Will tie the game to the first player
                with Player(connection, address) as player:
                    new_game.connected_players.append(player)
                    self._running_game = new_game  # Saves new game as the servers running game
                    self._handle_as_first(player)

                    while len(new_game.connected_players) > 1:
                        pass

                self.log(MSG_DISCONNECTED)
            self.log_total_players()
            self._running_game.is_done = True
            self._accepting_connections = True
        else:
            with Player(connection, address) as player:
                self._running_game.connected_players.append(player)
                self._handle_guessing(player)

                # After handling
                self._running_game.connected_players.remove(player)

            self.log(MSG_DISCONNECTED)
            self.log_total_players()

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

    # Handles the connection for all onther players
    def _handle_guessing(self, player: Player):
        try:
            while not self._running_game:
                pass  # Waits for new game to finish starting
            while not self._running_game.is_done:
                req = decode(player.connection.recv(MAX_PACK_LENGTH))  # Waits for request

                # After successful request
                if is_valid(req):  # Check if request is valid
                    response = self._translate_guessing_players(req, player)  # Translate request and generate response
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
                nickname = get_request_content(request)
                if len(nickname) <= MAX_INPUT_LENGTH:
                    player.nickname = nickname  # Saves player name
                    self.log(MSG_HANDLING)
                    return f'{API_FIRST}{API_SUCCESS}'
                else:
                    return f'{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

            elif API_USER_INPUT in request:
                chosen_word = get_request_content(request)
                if len(chosen_word) <= MAX_INPUT_LENGTH:
                    self._running_game.chosen_word = chosen_word
                    self.log(f'{MSG_CHOSEN_WORD} \'{chosen_word}\'')
                    return API_SUCCESS
                else:
                    return f'{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

            elif API_START_GAME in request:
                self._start_game()
                return f'{API_SUCCESS}{self._running_game.get_status()}'

            else:
                return API_BAD_REQUEST

        elif API_GET in request:
            if API_STATUS in request:
                if self._running_game.is_done:
                    return f'{API_GAME_OVER}{API_SUCCESS}{self._running_game.get_status()}'
                else:
                    return f'{API_SUCCESS}{self._running_game.get_status()}'

    # Receives all other client's request as a String
    # Process request and generates a response
    # Returns the response
    def _translate_guessing_players(self, request: str, player: Player):
        if self._running_game.is_done:
            return f'{API_GAME_OVER}{API_SUCCESS}{self._running_game.get_status()}'
        else:
            if API_POST in request:
                if API_NICKNAME in request:
                    nickname = get_request_content(request)
                    if len(nickname) <= MAX_INPUT_LENGTH:
                        player.nickname = nickname  # Saves player name
                        self.log(MSG_HANDLING)
                        return API_SUCCESS
                    else:
                        return f'{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

                elif API_USER_INPUT in request:
                    guessed_word = get_request_content(request)
                    if len(guessed_word) <= MAX_INPUT_LENGTH:
                        self.log(f'{MSG_PLAYER_GUESSED} {guessed_word}')
                        if guessed_word.lower() == self._running_game.chosen_word.lower() \
                                and not self._running_game.is_done:
                            player.won = True
                            return f'{API_WON}{API_SUCCESS}{self._running_game.get_status(player.word_tip)}'
                        else:
                            player.words_guessed.append(guessed_word)
                            return f'{API_SUCCESS}{self._running_game.get_status(player.word_tip)}'
                    else:
                        return f'{API_USER_ERROR}{CLT_MSG_TOO_LONG_WORD}'

            elif API_GET in request:
                if API_STATUS in request:
                    if self._running_game.is_done:
                        return f'{API_GAME_OVER}{API_SUCCESS}{self._running_game.get_status(player.word_tip)}'
                    else:
                        return f'{API_SUCCESS}{self._running_game.get_status(player.word_tip)}'

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

    # Starts the game
    def _start_game(self):
        self._running_game.generate_all_word_tips()
        self._send_start_warning()  # Warn players that the game has started
        self._accepting_connections = False
        threading.Thread(target=self.run_game_timer).start()
        self.log(MSG_GAME_STARTED)

    # Finishes the game
    def _game_over(self):
        self._running_game.is_done = True
        self._running_game.generate_last_status()
        self.log(CLT_MSG_GAME_OVER)

    # MARK - Helper methods

    # Attempts to send all players a command
    def _send_start_warning(self):
        for player in self._running_game.connected_players:
            if player is not self._running_game.get_first_player():
                try:
                    status = self._running_game.get_status(player.word_tip)
                    player.connection.sendall(encode(f'{API_START_GAME}{API_SUCCESS}{status}'))
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


if __name__ == '__main__':
    server = Server()
    server.start()
