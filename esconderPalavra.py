import random

def esconderPalavra (palavra, qtMant):
    vector = list(palavra)
    qtSub = len(vector) - qtMant
    L = len(vector) - 1
    pronto = 0
    if(qtSub <= 0):
        return palavra
    while(pronto == 0):
        r = random.randint(0,L)
        vector[r] = '#'
        if(vector.count('#') >= qtSub or vector.count('#') == (L + 1)):
            pronto = 1
    secret = ''.join(vector)
    return secret