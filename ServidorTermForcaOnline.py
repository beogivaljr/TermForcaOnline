import logging
import threading
import time
import socket
import os

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080        # Port to listen on (non-privileged ports are > 1023)

def thread_conn(conn, addr):
    logging.info("Thread: Connected by:" + repr(addr))
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
                
            pathStr = "." + repr(data).split('GET ')[1].split(' HTTP')[0]
            fileExt = pathStr.split('.')[-1]
            
            try:
                
                time.sleep(10) ## Simular arquivo grande
                
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
    logging.info("Thread: Disconnected by:" + repr(addr))

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
            s.listen()
            while True:
                logging.info("Main: Waiting for new connection...")
                conn, addr = s.accept() #Trava o programa esperando conexao
                x = threading.Thread(target=thread_conn, args=(conn, addr))
                x.start()
        except:
            logging.info("Main: Crash")

    logging.info("Main: Socket closed")


    logging.info("Main: All done")
