import logging
import threading
import time
import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080        # Port to listen on (non-privileged ports are > 1023)

connectedPlayers = [] ## Lista com os jogadores ativos

## Recebe o objeto usuário da connexão do socket {player = (connection, address)}
## Devolve o endereço da conexão do usuário {addr = (ip, port)}
def getPlayerAddress(player):
    return player[1]


## Recebe o objeto usuário da connexão do socket {player = (connection, address)}
## Devolve o objeto conexão do usuário
def getPlayerConnection(player):
    return player[0]


## Recebe o objeto usuário da connexão do socket {player = (connection, address)}
## Devolve o ip do usuário
## Serve como identificador único!
def getPlayerIp(player):
    return getPlayerAddress(player)[0]


## Recebe a dupla (ip, porta) da connexão do socket
## Devolve os ultimos dígitos do ip apenas para servir de apelido para usuários
## Não serve como identificador único!
def getPlayerAlias(player):
    return getPlayerIp(player).split('.')[-1]


## Recebe um socket e aguarda uma nova connexão
## Devolve um novo jogador {player = (connection, address)}
def waitNewPlayerFrom(sock):
    return sock.accept()


## Thread paralela que lida com cada usuário
## Temos uma função dessas por usuário
def thread_conn(player):
    logging.info("Thread "  + getPlayerAlias(player) +  ": conectado.")
    with getPlayerConnection(player) as conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
                
            pathStr = "." + repr(data).split('GET ')[1].split(' HTTP')[0]
            fileExt = pathStr.split('.')[-1]
            
            try:

                time.sleep(10) ## Simular arquivo grande

                playersIpList.remove(addr[0])

                sizeInt = os.stat(pathStr).st_size
                sizeStr = str(sizeInt)
                
                result = 'HTTP/1.1 200 OK\r\nContent-Lenght: ' + sizeStr + '\r\nContent-Type: ' + fileExt + '\r\n\r\n'
                
                conn.sendall(bytes(result, 'utf-8'))
                
                file = open(pathStr, 'rb')
                conn.send(file.read(1025))
                file.close()
            
            except:
                conn.sendall(bytes('HTTP/1.1 400 ERRO\r\n\r\n', 'utf-8'))
                break
    if player in connectedPlayers:
        connectedPlayers.remove(player)
    print(connectedPlayers)
    logging.info("Thread " + getPlayerAlias(player) + ": " +  "desconectado.")


## Execussão principal do programa
if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # try:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            logging.info("Main: Esperando novos jogadores")
            player = waitNewPlayerFrom(s)
            connectedPlayers.append(player)
            x = threading.Thread(target=thread_conn, args=(player,))
            x.start()

            if len(connectedPlayers) == 0:
                setMasterPlayer(ip)
            else:
                logging.info("Main: Novo jogador adivinhador conectado")
            print(len(connectedPlayers))
        # except:
        #     logging.info("Main: Crash")
    logging.info("Main: Socket fechado")
