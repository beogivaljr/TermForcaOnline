#!/usr/bin/python3


class GlobalConstants:
    # Constantes globais
    HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
    PORT = 8080  # Port to listen on (non-privileged ports are > 1023)
    ENCODING = 'utf-8'

    # Comandos API
    API_USER_INPUT = 'USER_INPUT '
    API_GET = 'GET '
    API_POST = 'POST '
    API_TOUCH = 'TOUCH '
    API_FIRST = 'FIRST '
    API_SUCCESS = ''
    API_ERROR_500 = 'HTTP/1.1 500 ERROR\r\n\r\n'
    API_END = 'HTTP/1.1\r\n\r\n'
