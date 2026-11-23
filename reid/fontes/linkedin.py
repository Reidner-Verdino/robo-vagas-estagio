"""LinkedIn: vagas e publicações públicas encontradas por um buscador via SerpApi.

O REID não acessa o LinkedIn diretamente nem usa conta logada: os termos de uso
proíbem a raspagem. Ele consulta o índice público de um buscador (DuckDuckGo
por padrão, porque o Google ignorava a restrição 'site:' em buscas de emprego)
e só aceita resultados cujo endereço seja de fato do LinkedIn.
"""

import re

from ..modelo import Candidato
from ..texto import formatar_data, idade_em_dias, resumir
from . import serpapi


def limpar_titulo(titulo):
    """Remove sufixos como ' | LinkedIn', ' - LinkedIn Jobs' e ' | LinkedIn Brasil'."""
    return re.sub(r"\s*[|\-–—]\s*LinkedIn(?:\s+\w+)?\s*$", "", titulo or "", flags=re.I).strip()


def interpretar_vaga(titulo):
    """Título de página de vaga -> (cargo, empresa, local).

    Formatos reconhecidos:
      'Data Engineer na empresa EY – São Paulo, SP | LinkedIn Jobs'
      'Acme contratando Desenvolvedor Python em Recife, PE | LinkedIn'
      'Acme hiring Data Engineer in Rio de Janeiro, RJ | LinkedIn'
      'Cargo - Empresa - LinkedIn'
    """
    t = limpar_titulo(titulo)
    m = re.match(r"^(?P<cargo>.+?) na empresa (?P<emp>.+?)(?:\s+[–—-]\s+(?P<local>.+))?$", t)
    if m:
        return m.group("cargo").strip(), m.group("emp").strip(), (m.group("local") or "").strip()
    for padrao in (r"^(?P<emp>.+?) (?:está )?contratando (?P<cargo>.+) em (?P<local>[^|]+)$",
                   r"^(?P<emp>.+?) (?:is )?hiring (?P<cargo>.+) in (?P<local>[^|]+)$",
                   r"^(?P<emp>.+?) (?:está )?contratando (?P<cargo>.+)$",
                   r"^(?P<emp>.+?) (?:is )?hiring (?P<cargo>.+)$"):
        m = re.match(padrao, t)
        if m:
            return m.group("cargo").strip(), m.group("emp").strip(), (m.groupdict().get("local") or "").strip()
    partes = [p.strip() for p in re.split(r"\s+[|\-–—]\s+", t) if p.strip()]
    if len(partes) >= 2:
        return partes[0], partes[1], ""
    return t, "", ""


def interpretar_publicacao(titulo):
    """'Fulano no LinkedIn: texto…' -> (autor, texto)."""
    t = limpar_titulo(titulo)
    m = re.match(r"^(?P<autor>.+?) (?:no|on) LinkedIn:\s*(?P<texto>.*)$", t)
    if m:
        return m.group("autor").strip(), m.group("texto").strip()
    m = re.match(r"^(?P<texto>.*?)\s*\|\s*(?P<autor>[^|]+?) (?:posted on the topic|publicou sobre o tema)", t)
    if m:
        return m.group("autor").strip(), m.group("texto").strip()
    return "", t


def buscas_configuradas(cfg_fonte):
    """Buscas do config.json mais a busca dos recrutadores favoritos, quando houver."""
    buscas = [dict(b) for b in cfg_fonte["buscas"]]
    nomes = [n.strip() for n in cfg_fonte["recrutadores"] if n.strip()]
    if nomes:
        lista = " OR ".join(f'"{n}"' for n in nomes)
        buscas.append({"id": "recrutadores_favoritos", "peso": cfg_fonte["recrutadores_peso"],
                       "site": "linkedin.com", "q": f"inurl:posts ({lista}) (estágio OR estagio OR vaga OR vagas)"})
    return buscas


def parametros(busca, cfg_fonte):
    consulta = f"site:{busca['site']} {busca['q']}"
    if cfg_fonte["motor"] == "google":
        return {"engine": "google", "q": consulta, "as_sitesearch": busca["site"].split("/")[0],
                "google_domain": "google.com.br", "gl": "br", "hl": "pt", "tbs": cfg_fonte["periodo_google"]}
    return {"engine": "duckduckgo", "q": consulta, "kl": cfg_fonte["regiao_duckduckgo"],
            "df": cfg_fonte["periodo_duckduckgo"]}


def buscar(busca, cfg_fonte, api_key, hoje=None):
    """Devolve (candidatos, descartes_de_endereço) de uma busca."""
    resposta = serpapi.buscar(parametros(busca, cfg_fonte), api_key)
    candidatos, descartes = [], []
    for r in resposta.get("organic_results") or []:
        if not isinstance(r, dict):
            continue
        link = str(r.get("link") or "").strip()
        titulo = str(r.get("title") or "")
        trecho = str(r.get("snippet") or "")
        data = str(r.get("date") or "")
        comum = dict(fonte="LinkedIn", idade=idade_em_dias(data, hoje), idade_max=cfg_fonte["dias_maximos"],
                     aceitar_sem_data=True, publicada=formatar_data(data) or "data não informada")
        if not re.match(r"^https?://([a-z]{2,3}\.|www\.)?linkedin\.com/", link):
            descartes.append(("não é do LinkedIn", titulo, link))
        elif "/jobs/view" in link:
            cargo, empresa, local = interpretar_vaga(titulo)
            candidatos.append(Candidato(titulo=cargo, empresa=empresa, link=link, texto=cargo,
                                        local=local, resumo=resumir(trecho, 180), **comum))
        elif "/posts/" in link or "/feed/update/" in link:
            autor, texto_titulo = interpretar_publicacao(titulo)
            candidatos.append(Candidato(titulo=resumir(texto_titulo, 110) or "Publicação de vaga", empresa=autor,
                                        link=link, texto=f"{texto_titulo} {trecho}", resumo=resumir(trecho),
                                        publicacao=True, **comum))
        else:
            descartes.append(("endereço não é vaga nem publicação", titulo, link))
    return candidatos, descartes
