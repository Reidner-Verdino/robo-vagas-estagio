"""Chamadas à SerpApi (Google Vagas e buscas do LinkedIn) e consulta de saldo."""

from ..rede import ErroRede, get_json

ENDERECO = "https://serpapi.com/search.json"
CONTA = "https://serpapi.com/account.json"
SEM_RESULTADOS = ("hasn't returned any results", "has not returned any results", "no results")


def buscar(params, api_key):
    """Executa uma busca. Uma busca sem resultados devolve {} (não é falha)."""
    resposta = get_json(ENDERECO, params={**params, "api_key": api_key}, timeout=60)
    if not isinstance(resposta, dict):
        raise ErroRede("resposta inesperada da SerpApi")
    erro = resposta.get("error")
    if erro:
        if any(s in str(erro).lower() for s in SEM_RESULTADOS):
            return {}
        raise ErroRede(f"SerpApi: {erro}")
    return resposta


def saldo(api_key):
    """Buscas restantes no plano. A consulta de conta não consome buscas."""
    conta = get_json(CONTA, params={"api_key": api_key})
    if not isinstance(conta, dict):
        raise ErroRede("resposta inesperada da conta SerpApi")
    if conta.get("error"):
        raise ErroRede(f"SerpApi: {conta['error']}")
    for chave in ("total_searches_left", "plan_searches_left"):
        valor = conta.get(chave)
        if isinstance(valor, int) and not isinstance(valor, bool):
            return max(0, valor)
    raise ErroRede("a conta SerpApi não informou o saldo de buscas")
