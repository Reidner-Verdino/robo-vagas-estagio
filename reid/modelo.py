"""Estruturas de dados do REID.

Cada fonte devolve Candidatos (dados brutos, ainda não avaliados). A
classificação transforma cada Candidato aceito em uma Vaga, com trilha, nível,
modalidade, currículo sugerido e pontuação.
"""

import unicodedata
from dataclasses import dataclass, field


def _normalizar_chave(texto):
    """Mesma normalização usada no histórico desde a primeira versão (compatibilidade)."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return texto.encode("ascii", "ignore").decode().lower().strip()


@dataclass
class Candidato:
    titulo: str
    empresa: str
    link: str
    fonte: str
    texto: str                      # o que é avaliado para trilha, nível e exclusões
    local: str = ""
    publicada: str = ""             # data exibida no e-mail
    resumo: str = ""                # trecho exibido em publicações
    publicacao: bool = False        # True para posts de recrutadores
    idade: int | None = None        # idade em dias; None quando a fonte não informa
    idade_max: int = 7
    aceitar_sem_data: bool = True
    modalidade_hint: str = ""       # "remoto", "hibrido" ou "presencial", quando a fonte informa
    nivel_hint: str = ""            # "estagio", "trainee" ou "excluido", quando a fonte informa
    exterior: bool = False          # vaga remota de empresa de fora do Brasil
    regiao_exterior: str = ""       # onde o candidato pode morar ("Worldwide", "LATAM"...)
    chave_por_link: bool = False    # True quando a fonte não informa a empresa (sites via buscador)


@dataclass
class Vaga:
    titulo: str
    empresa: str
    link: str
    fonte: str
    local: str = ""
    publicada: str = ""
    resumo: str = ""
    publicacao: bool = False
    trilha: str = ""
    trilha_nome: str = ""
    curriculo: str = ""
    nivel: str = ""
    modalidade: str = ""
    alertas: list = field(default_factory=list)
    termos_stack: list = field(default_factory=list)
    pontuacao: int = 0
    chave_por_link: bool = False

    @property
    def chave(self):
        """Identidade da vaga no histórico (mesmo formato das versões anteriores)."""
        if self.publicacao or self.chave_por_link:
            return _normalizar_chave(self.link.split("?")[0])
        return _normalizar_chave(f"{self.titulo}|{self.empresa}")
