"""Distribuição da cota mensal da SerpApi entre as execuções e entre as buscas."""

from datetime import date, timedelta

from .texto import BRASILIA

JANELA_HORAS = 12


def janela(agora):
    """Número da janela de 12 horas: as execuções das 13h e das 22h caem em janelas diferentes."""
    return int(agora.timestamp() // (JANELA_HORAS * 3600))


def proxima_renovacao(hoje, dia):
    """Próxima data de renovação da cota (o dia do mês em que a conta foi criada)."""
    def no_mes(ano, mes):
        ultimo = (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)).day
        return date(ano, mes, min(dia, ultimo))
    candidata = no_mes(hoje.year, hoje.month)
    if candidata <= hoje:
        ano, mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)
        candidata = no_mes(ano, mes)
    return candidata


def buscas_permitidas(restantes, agora, cfg_serpapi):
    """Quantas buscas esta execução pode usar para o saldo durar até a renovação."""
    hoje = agora.astimezone(BRASILIA).date()
    renovacao = proxima_renovacao(hoje, cfg_serpapi["dia_renovacao"])
    execucoes = max(1, (renovacao - hoje).days * cfg_serpapi["execucoes_por_dia"])
    base, sobra = divmod(max(0, restantes), execucoes)
    extra = 1 if janela(agora) % execucoes < sobra else 0   # distribui a sobra de forma determinística
    return base + extra, renovacao, execucoes


def ciclo_ponderado(buscas):
    """Fila em que cada busca aparece proporcionalmente ao seu peso, bem intercalada
    (round-robin ponderado suave)."""
    total = sum(b["peso"] for b in buscas)
    atual = [0] * len(buscas)
    ciclo = []
    for _ in range(total):
        for i, b in enumerate(buscas):
            atual[i] += b["peso"]
        escolhida = max(range(len(buscas)), key=lambda i: atual[i])
        atual[escolhida] -= total
        ciclo.append(buscas[escolhida])
    return ciclo


def escolher(buscas, quantidade, agora):
    """Escolhe as buscas desta execução: um trecho do ciclo que avança a cada janela."""
    if quantidade <= 0 or not buscas:
        return []
    if quantidade >= len(buscas):
        return list(buscas)
    ciclo = ciclo_ponderado(buscas)
    inicio = (janela(agora) * quantidade) % len(ciclo)
    escolhidas, ids = [], set()
    for passo in range(len(ciclo)):
        b = ciclo[(inicio + passo) % len(ciclo)]
        if b["id"] not in ids:
            escolhidas.append(b)
            ids.add(b["id"])
        if len(escolhidas) == quantidade:
            break
    return escolhidas
