#!/usr/bin/python3


# Constantes globais
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080  # Port to listen on (non-privileged ports are > 1023)
__ENCODING = 'utf-8'  # '__' Para representar que é para uso interno

# Comandos API

# Tudo o que vier depois dessa tag será interpretado como entrada do usuário e não pode ser lido como comando
API_USER_INPUT = 'USER_INPUT '

# Usada para requisitar dados
API_GET = 'GET '

# Usada para enviar dados
API_POST = 'POST '

# Usada para indicar o primeiro contato com o servidor
API_TOUCH = 'TOUCH '

# Usada para marcar a comunicação com o primeiro jogador
API_FIRST = 'FIRST '

# Mensagem padrão de sucesso
API_SUCCESS = 'HTTP/1.1 200 OK\r\n'

# Mensagem padrão de erro
API_ERROR_500 = 'HTTP/1.1 500 ERROR\r\n'

# Final padrão do cabeçalho
API_END = 'HTTP/1.1\r\n'

# Exemplos de requisições
# 'POST TOUCH HTTP/1.1\r\n'
# 'POST USER_INPUT HTTP/1.1\r\nQualquer texto inserido pelo usuário'
# 'FIRST HTTP/1.1 200 OK\r\n'


# Recebe uma string
# Devolve ela codificada
def encode(string):
    return bytes(string, __ENCODING)


# Recebe uma string
# Devolve ela decodificada
def decode(data):
    return data.decode(__ENCODING)
