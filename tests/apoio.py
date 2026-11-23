"""Apoio comum aos testes: configuração real do projeto, fábricas e respostas falsas."""

import copy
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from reid import config, rede  # noqa: E402
from reid.modelo import Candidato  # noqa: E402

rede.ESPERA_BASE = 0          # sem esperas entre tentativas nos testes
_CFG = config.carregar(RAIZ / "config.json")


def cfg():
    """Cópia da configuração real, para cada teste poder alterá-la sem afetar os outros."""
    return copy.deepcopy(_CFG)


def candidato(**campos):
    base = dict(titulo="Estágio em Análise de Dados", empresa="Empresa Exemplo", link="https://exemplo.com/vaga/1",
                fonte="Gupy", texto=None, local="", publicada="", idade=1, idade_max=7, aceitar_sem_data=True)
    base.update(campos)
    if base["texto"] is None:
        base["texto"] = base["titulo"]
    return Candidato(**base)


class RespostaFalsa:
    def __init__(self, status=200, dados=None, reason="", json_invalido=False):
        self.status_code = status
        self._dados = dados
        self.reason = reason
        self._json_invalido = json_invalido

    def json(self):
        if self._json_invalido:
            raise ValueError("não é JSON")
        return self._dados
