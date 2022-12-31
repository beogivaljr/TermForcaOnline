#!/usr/bin/python3


# Global constants
HOST = ''  # Standard loopback interface address (localhost)
PORT = 9000  # Port to listen on (non-privileged ports are > 1023)
_ENCODING = 'utf-8'
MAX_INPUT_LENGTH = 32
MAX_PACK_LENGTH = 256
TOTAL_GAME_TIME = 60

# API tags
API_GET = 'GET '
API_POST = 'POST '

API_USER_INPUT = 'USER_INPUT '
API_NICKNAME = 'NICKNAME '
API_STATUS = 'STATUS '
API_FIRST = 'FIRST '
API_START_GAME = 'START_GAME '
API_GAME_OVER = 'GAME_OVER '
API_WON = 'WON '
API_SUCCESS = 'HTTP/1.1 200 OK\r\n'
API_USER_ERROR = 'HTTP/1.1 403 ERROR\r\n'
API_BAD_REQUEST = 'HTTP/1.1 400 ERROR\r\n'
API_ERROR_500 = 'HTTP/1.1 500 ERROR\r\n'
API_END = 'HTTP/1.1\r\n'


def encode(string):
    return bytes(string, _ENCODING)


def decode(data):
    return data.decode(_ENCODING)


# Returns content of requests
def get_request_content(response):
    return response.split(API_END)[1]


# Returns content of requests
def get_success_content(response):
    return response.split(API_SUCCESS)[1]


# Check if the request is valid
def is_valid(request: str):
    if (API_POST in request or API_GET in request) and API_END in request:
        return True
    else:
        return False
