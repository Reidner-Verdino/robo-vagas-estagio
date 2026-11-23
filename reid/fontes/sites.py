"""Sites de vagas prioritários (Catho, InfoJobs, Nerdin, Sólides, Eureca, Cia de Talentos...).

Assim como no LinkedIn, o REID não acessa esses sites diretamente: consulta o
índice público do DuckDuckGo pela SerpApi, restrito ao domínio de cada site, e
confere no código se cada resultado é mesmo daquele domínio e se é a página de
uma vaga (e não uma página de listagem, como "120 vagas de estágio em TI").
"""

import re
from urllib.parse import urlparse

from ..modelo import Candidato
from ..texto import formatar_data, idade_em_dias, normalizar, resumir
from . import serpapi

LISTAGEM = re.compile(r"^\s*(\+?\d[\d.]*\+?\s+(novas\s+)?vagas?\b|vagas de emprego\b|vagas para\b|vagas em\b)", re.I)
UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
# "Cidade, UF" ou "Cidade/UF". O hífen fica de fora de propósito: "Estágio em TI - RJ" não é uma cidade.
LOCAL = re.compile(r"\b([A-ZÀ-Ý][a-zà-ÿ'.]{2,}(?:\s+(?:de|do|da|dos|das|[A-ZÀ-Ý][a-zà-ÿ'.]+))*)\s*[,/]\s*([A-Z]{2})\b")


def dominio_confere(link, dominio):
    """True se o link é do domínio (ou de um subdomínio dele), por exemplo empresa.vagas.solides.com.br."""
    try:
        host = (urlparse(link).hostname or "").lower()
    except ValueError:
        return False
    dominio = dominio.lower().lstrip(".")
    return urlparse(link).scheme in ("http", "https") and (host == dominio or host.endswith("." + dominio))


def limpar_titulo(titulo, nome_site):
    """Tira o nome do site e prefixos genéricos: 'Vaga de Estágio em TI - Catho' -> 'Estágio em TI'."""
    t = str(titulo or "").strip()
    partes = [p.strip() for p in re.split(r"\s+[|–—-]\s+", t) if p.strip()]
    site = normalizar(nome_site).replace(" ", "")
    partes = [p for p in partes if normalizar(p).replace(" ", "") != site]
    t = partes[0] if partes else t
    return re.sub(r"^(vaga\s+(de|para)\s+)", "", t, flags=re.I).strip()


def extrair_local(texto):
    """Primeira ocorrência de 'Cidade, UF', 'Cidade - UF' ou 'Cidade/UF' no texto."""
    for m in LOCAL.finditer(str(texto or "")):
        if m.group(2) in UFS:
            return f"{m.group(1).strip()}, {m.group(2)}"
    return ""


def buscar(site, cfg_fonte, api_key, hoje=None):
    """Devolve (candidatos, descartes) de uma busca em um site."""
    params = {"engine": "duckduckgo", "q": f"site:{site['dominio']} {site['q']}",
              "kl": cfg_fonte["regiao_duckduckgo"], "df": cfg_fonte["periodo_duckduckgo"]}
    resposta = serpapi.buscar(params, api_key)
    candidatos, descartes = [], []
    for r in resposta.get("organic_results") or []:
        if not isinstance(r, dict):
            continue
        link = str(r.get("link") or "").strip()
        titulo_bruto = str(r.get("title") or "")
        trecho = str(r.get("snippet") or "")
        if not dominio_confere(link, site["dominio"]):
            descartes.append((f"não é do {site['nome']}", titulo_bruto, link))
            continue
        titulo = limpar_titulo(titulo_bruto, site["nome"])
        if LISTAGEM.search(titulo) or LISTAGEM.search(titulo_bruto):
            descartes.append(("página de listagem, não de vaga", titulo_bruto, link))
            continue
        data = str(r.get("date") or "")
        candidatos.append(Candidato(
            titulo=titulo,
            empresa="",
            link=link,
            fonte=site["nome"],
            texto=titulo,
            local=extrair_local(f"{titulo_bruto} {trecho}"),
            publicada=formatar_data(data) or "data não informada",
            resumo=resumir(trecho, 180),
            idade=idade_em_dias(data, hoje),
            idade_max=cfg_fonte["dias_maximos"],
            aceitar_sem_data=cfg_fonte["aceitar_sem_data"],
            chave_por_link=True,
        ))
    return candidatos, descartes
