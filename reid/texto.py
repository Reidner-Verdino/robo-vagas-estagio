"""Normalização de texto, busca de termos e interpretação de datas."""

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

BRASILIA = timezone(timedelta(hours=-3))  # o Brasil não tem horário de verão desde 2019


# ---------------------------------------------------------------- texto
def normalizar(texto):
    """Minúsculas, sem acentos e com espaços simples: 'Estágio  TI' -> 'estagio ti'."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", texto).strip()


@lru_cache(maxsize=8192)
def padrao(termo):
    """Expressão regular de um termo.

    O termo casa como palavra inteira; um '*' no fim casa o começo da palavra
    ('estagi*' pega estágio, estagiário e estagiária). As verificações antes e
    depois do termo aceitam termos com símbolos, como 'c#', '.net' e 'front-end'.
    """
    prefixo = termo.endswith("*")
    base = normalizar(termo[:-1] if prefixo else termo)
    if not base:
        raise ValueError(f"termo vazio ou inválido: {termo!r}")
    expressao = r"(?<![a-z0-9])" + re.escape(base)
    if not prefixo:
        expressao += r"(?![a-z0-9])"
    return re.compile(expressao)


def tem_termo(texto, termos):
    t = normalizar(texto)
    return any(padrao(termo).search(t) for termo in termos)


def termos_encontrados(texto, termos):
    """Lista, sem repetição e na ordem da lista, dos termos presentes no texto."""
    t = normalizar(texto)
    return [termo for termo in termos if padrao(termo).search(t)]


def resumir(texto, limite=260):
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0]
    return corte + "…"


def limpar_html(texto):
    texto = re.sub(r"<[^>]+>", " ", str(texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


# ---------------------------------------------------------------- datas
MESES_EN = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

_UNIDADE_UM = re.compile(r"\b(?:um|uma|an|a)\s+(?=(?:min|hora|hour|dia|day|semana|week|mes|month|ano|year))")


def data_absoluta(texto):
    """Reconhece 'Oct 29, 2026', '29 de out. de 2026', '2026-10-29' e '29/10/2026'."""
    t = normalizar(texto)
    if not t:
        return None
    try:
        m = re.search(r"\b([a-z]{3})[a-z]*\.? (\d{1,2}), (\d{4})\b", t)
        if m and m.group(1) in MESES_EN:
            return date(int(m.group(3)), MESES_EN.index(m.group(1)) + 1, int(m.group(2)))
        m = re.search(r"\b(\d{1,2}) de ([a-z]{3})[a-z]*\.? de (\d{4})\b", t)
        if m and m.group(2) in MESES_PT:
            return date(int(m.group(3)), MESES_PT.index(m.group(2)) + 1, int(m.group(1)))
        m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})", t)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t)
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:  # data impossível, como 31/02
        return None
    return None


def idade_relativa(texto):
    """'há 3 dias', '5 hours ago', 'ontem', 'Just posted' -> idade em dias; None se não souber."""
    t = normalizar(texto)
    if not t:
        return None
    if any(p in t for p in ("agora", "hoje", "just posted", "today", "recente")):
        return 0
    if "ontem" in t or "yesterday" in t:
        return 1
    t = _UNIDADE_UM.sub("1 ", t)
    for m in re.finditer(r"(\d+)\s*\+?\s*([a-z]+)", t):
        n, unidade = int(m.group(1)), m.group(2)
        if unidade in ("h", "hr", "hrs") or unidade.startswith(("min", "hora", "hour")):
            return 0
        if unidade == "d" or unidade.startswith(("dia", "day")):
            return n
        if unidade == "w" or unidade.startswith(("semana", "week")):
            return n * 7
        if unidade.startswith(("mes", "month")):
            return n * 30
        if unidade.startswith(("ano", "year")):
            return n * 365
    return None


def idade_em_dias(texto, hoje=None):
    """Idade de uma publicação a partir de um texto relativo ou de uma data absoluta."""
    relativa = idade_relativa(texto)
    if relativa is not None:
        return relativa
    absoluta = data_absoluta(texto)
    if absoluta is None:
        return None
    hoje = hoje or datetime.now(BRASILIA).date()
    return max(0, (hoje - absoluta).days)


def formatar_data(texto):
    """Mostra datas absolutas como 29/10/2026; textos relativos ficam como estão."""
    absoluta = data_absoluta(texto)
    if absoluta is not None and not idade_relativa(texto):
        return absoluta.strftime("%d/%m/%Y")
    return str(texto or "").strip()


def iso_para_datetime(texto):
    """'2026-10-29T12:00:00Z' -> datetime com fuso (UTC quando não informado)."""
    if not texto:
        return None
    try:
        valor = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor
