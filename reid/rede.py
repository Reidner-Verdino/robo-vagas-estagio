"""Requisições HTTP com novas tentativas em falhas temporárias."""

import time

import requests

from . import __version__

USER_AGENT = f"REID/{__version__} (+https://github.com/Reidner-Verdino/robo-vagas-estagio)"
TENTATIVAS = 3
ESPERA_BASE = 2          # segundos; os testes usam 0
TEMPORARIOS = {429, 500, 502, 503, 504}


class ErroRede(Exception):
    def __init__(self, mensagem, status=None):
        super().__init__(mensagem)
        self.status = status


def _mensagem_de_erro(resposta):
    try:
        corpo = resposta.json()
        if isinstance(corpo, dict) and corpo.get("error"):
            return str(corpo["error"])
    except ValueError:
        pass
    return resposta.reason or "erro"


def get_json(url, params=None, timeout=30):
    """GET que devolve o JSON da resposta.

    Repete até TENTATIVAS vezes quando a falha é temporária (tempo esgotado,
    conexão, 429 ou 5xx). Outros erros HTTP e respostas que não são JSON viram
    ErroRede imediatamente, com o status e a mensagem do servidor.
    """
    ultimo_erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(url, params=params, timeout=timeout,
                                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        except (requests.Timeout, requests.ConnectionError) as e:
            ultimo_erro = ErroRede(f"falha de conexão: {e.__class__.__name__}")
        else:
            if resposta.status_code in TEMPORARIOS:
                ultimo_erro = ErroRede(f"HTTP {resposta.status_code}: {_mensagem_de_erro(resposta)}",
                                       resposta.status_code)
            elif resposta.status_code >= 400:
                raise ErroRede(f"HTTP {resposta.status_code}: {_mensagem_de_erro(resposta)}",
                               resposta.status_code)
            else:
                try:
                    return resposta.json()
                except ValueError:
                    raise ErroRede("a resposta não é JSON válido", resposta.status_code) from None
        if tentativa < TENTATIVAS:
            time.sleep(ESPERA_BASE * tentativa)
    raise ultimo_erro
