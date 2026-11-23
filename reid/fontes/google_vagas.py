"""Google Vagas (motor google_jobs da SerpApi): agrega LinkedIn, Catho, InfoJobs e outros."""

import re

from ..modelo import Candidato
from ..texto import normalizar, idade_em_dias
from . import serpapi

SINAIS_DATA = r"\bha\b|\bago\b|postad|publicad|\bhoje\b|\bontem\b|just posted|today|yesterday"


def data_da_vaga(j, hoje=None):
    """Procura a data no campo estruturado e, se faltar, nas etiquetas da vaga.

    Só aceita textos que indicam publicação, para não confundir '6 horas por dia'
    com 'publicada há 6 horas'. Devolve (texto, idade) ou ('', None).
    """
    candidatos = [(j.get("detected_extensions") or {}).get("posted_at", "")]
    candidatos += [e for e in (j.get("extensions") or []) if isinstance(e, str)]
    for texto in candidatos:
        if texto and re.search(SINAIS_DATA, normalizar(texto)):
            idade = idade_em_dias(texto, hoje)
            if idade is not None:
                return texto, idade
    return "", None


def _candidato(j, cfg_fonte, hoje):
    titulo = str(j.get("title") or "").strip()
    postada, idade = data_da_vaga(j, hoje)
    opcoes = [o for o in (j.get("apply_options") or []) if isinstance(o, dict) and o.get("link")]
    link = opcoes[0]["link"] if opcoes else str(j.get("share_link") or "")
    fonte = re.sub(r"^via\s+", "", str(j.get("via") or "Google Vagas"), flags=re.I).strip() or "Google Vagas"
    remoto = (j.get("detected_extensions") or {}).get("work_from_home") is True
    return Candidato(
        titulo=titulo,
        empresa=str(j.get("company_name") or "").strip(),
        link=link,
        fonte=fonte,
        texto=titulo,
        local=str(j.get("location") or "").strip(),
        publicada=postada or "data não informada",
        idade=idade,
        idade_max=cfg_fonte["dias_maximos"],
        aceitar_sem_data=cfg_fonte["aceitar_sem_data"],
        modalidade_hint="remoto" if remoto else "",
    )


def buscar(consulta, cfg_fonte, api_key, hoje=None):
    resposta = serpapi.buscar({"engine": "google_jobs", "q": consulta, "location": cfg_fonte["localizacao"],
                               "hl": "pt", "gl": "br"}, api_key)
    resultados = resposta.get("jobs_results") or []
    return [_candidato(j, cfg_fonte, hoje) for j in resultados if isinstance(j, dict)]
