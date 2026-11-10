#!/usr/bin/env python3
"""
Robô de vagas em TI e Dados.

Fontes:
  • Gupy (API pública do portal): estágios em TI/Dados.
  • Google Vagas (via SerpApi): estágios em TI/Dados de LinkedIn, Catho, InfoJobs, Indeed etc.
  • LinkedIn (páginas públicas indexadas pelo Google, via SerpApi):
      - vagas de TI de qualquer área e nível (foco principal);
      - publicações de recrutadores anunciando vagas de TI.

As buscas pagas (SerpApi) são distribuídas automaticamente conforme a cota restante do mês,
priorizando as de TI.

Uso:
    python vagas_bot.py          -> busca e envia o e-mail
    python vagas_bot.py --teste  -> busca e só mostra no terminal (não envia nem salva)

Sem as credenciais de e-mail configuradas, o robô roda automaticamente em modo teste.
"""
import html
import json
import os
import re
import smtplib
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
ARQ_VISTAS = BASE / "vagas_vistas.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (robo-vagas-estagio)"}
DIAS_HISTORICO = 90
BRASILIA = timezone(timedelta(hours=-3))  # o Brasil não tem horário de verão desde 2019
SERPAPI = "https://serpapi.com/search.json"
GUPY_ENDERECOS = [
    "https://portal.gupy.io/api/job-search/jobs",   # endereço atual (desde out/2026)
    "https://portal.api.gupy.io/api/job",           # antigo, mantido como reserva
]

# Ordem e títulos das seções do e-mail
SECOES = [
    ("ti", "Vagas de TI no LinkedIn", "💼"),
    ("estagio", "Estágios em TI e Dados", "🎓"),
    ("publicacao_ti", "Publicações de recrutadores · TI", "📣"),
]
ROTULO_CURTO = {"ti": "vagas de TI", "estagio": "estágios", "publicacao_ti": "publicações"}


# ================================================================ texto e filtros
def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    return texto.encode("ascii", "ignore").decode().lower()


def tem_termo(texto, termos, prefixo=False):
    """Procura termos como palavras inteiras (ou início de palavra, se prefixo=True).
    Aceita termos com símbolos, como 'c#', '.net' e 'front-end'."""
    t = normalizar(texto)
    for termo in termos:
        padrao = r"(?<![a-z0-9])" + re.escape(normalizar(termo))
        if not prefixo:
            padrao += r"(?![a-z0-9])"
        if re.search(padrao, t):
            return True
    return False


def e_vaga_desejada(titulo, ja_e_estagio=False):
    """Estágio em TI/Dados (usado na Gupy e no Google Vagas)."""
    if tem_termo(titulo, CONFIG["termos_excluir"]):
        return False
    if not ja_e_estagio and not tem_termo(titulo, CONFIG["termos_estagio"], prefixo=True):
        return False
    return tem_termo(titulo, CONFIG["termos_area"])


def e_ti(texto):
    """Qualquer área de tecnologia, qualquer nível (usado no LinkedIn)."""
    return (tem_termo(texto, CONFIG["termos_ti_amplo"])
            and not tem_termo(texto, CONFIG["termos_excluir"]))


def e_publicacao_de_vaga(texto):
    """Publicação anunciando vaga, e não de alguém procurando emprego."""
    return (tem_termo(texto, CONFIG["termos_sinal_vaga"])
            and not tem_termo(texto, CONFIG["termos_candidato"]))


def idade_em_dias(texto):
    """Converte 'há 3 dias', '5 hours ago', 'Just posted' etc. em dias. Retorna None se não souber."""
    t = normalizar(texto).strip()
    if not t:
        return None
    if any(p in t for p in ["agora", "hoje", "just posted", "today", "recente"]):
        return 0
    if "ontem" in t or "yesterday" in t:
        return 1
    m = re.search(r"(\d+)\s*\+?\s*([a-z]+)", t)
    if not m:
        return 0 if re.search(r"\b(um|uma|an?)\s+(hora|minuto|hour|minute)", t) else None
    n, unidade = int(m.group(1)), m.group(2)
    if unidade.startswith(("min", "hor", "hour", "h")):
        return 0
    if unidade.startswith(("dia", "day", "d")):
        return n
    if unidade.startswith(("seman", "week")):
        return n * 7
    if unidade.startswith(("mes", "month")):
        return n * 30
    if unidade.startswith(("ano", "year")):
        return n * 365
    return None


SINAIS_DATA = r"\bha\b|\bago\b|postad|publicad|\bhoje\b|\bontem\b|just posted|today|yesterday"


def data_da_vaga_google(j):
    """Procura a data de postagem no campo detectado pelo SerpApi e, se faltar,
    nas etiquetas da vaga (ex.: ['há 2 dias', 'Tempo integral'])."""
    candidatos = [(j.get("detected_extensions") or {}).get("posted_at", "")]
    candidatos += [e for e in (j.get("extensions") or []) if isinstance(e, str)]
    for texto in candidatos:
        if texto and re.search(SINAIS_DATA, normalizar(texto)):
            idade = idade_em_dias(texto)
            if idade is not None:
                return texto, idade
    return "", None


MESES_EN = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def formatar_data(texto):
    """'Oct 29, 2026' ou '2026-10-29' -> '29/10/2026'; outros formatos ficam como estão."""
    t = (texto or "").strip()
    m = re.match(r"^([A-Za-z]{3})[a-z]*\.? (\d{1,2}), (\d{4})", t)
    if m and m.group(1).lower() in MESES_EN:
        return f"{int(m.group(2)):02d}/{MESES_EN[m.group(1).lower()]:02d}/{m.group(3)}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return t


def resumir(texto, limite=260):
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


def chave(vaga):
    if vaga.get("chave"):
        return vaga["chave"]
    return normalizar(f"{vaga['titulo']}|{vaga['empresa']}").strip()


# ================================================================ Gupy
def buscar_gupy():
    vagas = []
    limite = datetime.now(timezone.utc) - timedelta(days=CONFIG["dias_maximos"])
    for termo in CONFIG["gupy_termos"]:
        offset = 0
        while offset < 500:
            dados, erro = None, None
            for endereco in GUPY_ENDERECOS:
                try:
                    r = requests.get(
                        endereco,
                        params={"jobName": termo, "limit": 100, "offset": offset},
                        headers=HEADERS, timeout=30,
                    )
                    r.raise_for_status()
                    dados = r.json().get("data", []) or []
                    break
                except Exception as e:
                    erro = e
            if dados is None:
                print(f"[Gupy] erro em '{termo}': {erro}")
                break

            for j in dados:
                titulo = j.get("name", "")
                tipo = (j.get("type") or "").lower()
                if not e_vaga_desejada(titulo, ja_e_estagio="intern" in tipo):
                    continue
                publicada = j.get("publishedDate") or ""
                try:
                    data_pub = datetime.fromisoformat(publicada.replace("Z", "+00:00"))
                    if data_pub < limite:
                        continue
                    publicada = data_pub.astimezone(BRASILIA).strftime("%d/%m/%Y")
                except ValueError:
                    pass
                local = ", ".join(x for x in [j.get("city"), j.get("state")] if x)
                modelo = (j.get("workplaceType") or "").lower()
                if j.get("isRemoteWork") or modelo == "remote":
                    local = (local + " · Remoto").strip(" ·")
                elif modelo == "hybrid":
                    local = (local + " · Híbrido").strip(" ·")
                vagas.append({
                    "titulo": titulo,
                    "empresa": j.get("careerPageName", ""),
                    "local": local,
                    "fonte": "Gupy",
                    "publicada": publicada,
                    "link": j.get("jobUrl", ""),
                    "categoria": "estagio",
                })

            if len(dados) < 100:
                break
            offset += 100
            time.sleep(1)
    print(f"[Gupy] {len(vagas)} vagas compatíveis")
    return vagas


# ================================================================ cota da SerpApi
def proxima_renovacao(hoje, dia):
    """Próxima data de renovação da cota mensal (dia do mês em que a conta foi criada)."""
    def no_mes(ano, mes):
        ultimo = (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)).day
        return date(ano, mes, min(dia, ultimo))
    candidata = no_mes(hoje.year, hoje.month)
    if candidata <= hoje:
        ano, mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)
        candidata = no_mes(ano, mes)
    return candidata


def buscas_disponiveis(api_key, agora):
    """Quantas buscas esta execução pode gastar para a cota durar até a renovação."""
    try:
        conta = requests.get("https://serpapi.com/account.json",
                             params={"api_key": api_key}, timeout=30).json()
        restantes = conta.get("total_searches_left", conta.get("plan_searches_left"))
        restantes = int(restantes)
    except Exception as e:
        padrao = CONFIG.get("buscas_por_execucao_padrao", 4)
        print(f"[Cota] não consegui consultar a conta SerpApi ({e}); usando {padrao} buscas")
        return padrao, None

    hoje = agora.astimezone(BRASILIA).date()
    renovacao = proxima_renovacao(hoje, CONFIG.get("serpapi_dia_renovacao", 15))
    execucoes = max(1, (renovacao - hoje).days * CONFIG.get("execucoes_por_dia", 2))
    base, sobra = divmod(max(0, restantes), execucoes)
    # distribui a sobra entre as execuções de forma determinística
    janela = int(agora.timestamp() // (12 * 3600))
    extra = 1 if (janela % execucoes) < sobra else 0
    permitidas = base + extra
    print(f"[Cota] {restantes} buscas restantes até {renovacao:%d/%m} "
          f"(~{execucoes} execuções) -> {permitidas} nesta execução")
    return permitidas, restantes


def agenda_de_buscas():
    """Todas as buscas pagas com seus pesos (quanto maior, mais frequente)."""
    buscas = [dict(b) for b in CONFIG["linkedin_buscas"]]
    recrutadores = CONFIG.get("linkedin_recrutadores") or []
    if recrutadores:
        nomes = " OR ".join(f'"{n}"' for n in recrutadores)
        buscas.append({"id": "recrutadores_favoritos", "tipo": "linkedin", "site": "linkedin.com",
                       "peso": CONFIG.get("linkedin_recrutadores_peso", 3),
                       "q": f"inurl:posts ({nomes}) (estágio OR estagio OR vaga OR vagas)"})
    for i, consulta in enumerate(CONFIG["google_consultas"]):
        buscas.append({"id": f"google_vagas_{i + 1}", "tipo": "google_vagas",
                       "q": consulta, "peso": CONFIG.get("google_vagas_peso", 1)})
    return buscas


def ciclo_ponderado(buscas):
    """Sequência em que cada busca aparece proporcionalmente ao seu peso, bem intercalada."""
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


def escolher_buscas(quantidade, agora):
    buscas = agenda_de_buscas()
    if quantidade >= len(buscas):
        return buscas
    ciclo = ciclo_ponderado(buscas)
    janela = int(agora.timestamp() // (12 * 3600))
    inicio = (janela * max(quantidade, 1)) % len(ciclo)
    escolhidas, ids = [], set()
    for passo in range(len(ciclo)):
        b = ciclo[(inicio + passo) % len(ciclo)]
        if b["id"] not in ids:
            escolhidas.append(b)
            ids.add(b["id"])
        if len(escolhidas) >= quantidade:
            break
    return escolhidas


# ================================================================ Google Vagas
def buscar_google_vagas(consulta, api_key):
    vagas = []
    try:
        r = requests.get(SERPAPI, params={
            "engine": "google_jobs", "q": consulta,
            "location": CONFIG["google_localizacao"],
            "hl": "pt", "gl": "br", "api_key": api_key,
        }, timeout=60)
        resposta = r.json()
        if resposta.get("error"):
            print(f"[Google] '{consulta}': aviso do SerpApi -> {resposta['error']}")
        r.raise_for_status()
        resultados = resposta.get("jobs_results", []) or []
    except Exception as e:
        print(f"[Google] erro em '{consulta}': {e}")
        return vagas

    fora_area = antigas = sem_data = 0
    for j in resultados:
        titulo = j.get("title", "")
        if not e_vaga_desejada(titulo):
            fora_area += 1
            continue
        postada, idade = data_da_vaga_google(j)
        if idade is None and not CONFIG.get("google_enviar_sem_data", False):
            sem_data += 1
            continue
        if idade is not None and idade > CONFIG.get("google_dias_maximos", 3):
            antigas += 1
            continue
        opcoes = j.get("apply_options") or []
        link = (opcoes[0].get("link") if opcoes else None) or j.get("share_link", "")
        fonte = re.sub(r"^via\s+", "", j.get("via") or "Google", flags=re.I)
        vagas.append({
            "titulo": titulo,
            "empresa": j.get("company_name", ""),
            "local": j.get("location", ""),
            "fonte": fonte,
            "publicada": postada or "data não informada",
            "link": link,
            "categoria": "estagio",
        })
    print(f"[Google] '{consulta}': {len(resultados)} resultados | fora da área: {fora_area} | "
          f"mais antigas que o limite: {antigas} | sem data: {sem_data}")
    return vagas


# ================================================================ LinkedIn
def limpar_titulo_linkedin(titulo):
    """Remove sufixos como ' | LinkedIn', ' - LinkedIn Jobs' e ' | LinkedIn Brasil'."""
    return re.sub(r"\s*[|\-–—]\s*LinkedIn(?:\s+\w+)?\s*$", "", titulo or "", flags=re.I).strip()


def interpretar_vaga_linkedin(titulo):
    """'Empresa contratando Cargo em Cidade | LinkedIn' -> (cargo, empresa, local)."""
    t = limpar_titulo_linkedin(titulo)
    m = re.match(r"^(?P<cargo>.+?) na empresa (?P<emp>.+?)(?:\s+[–—-]\s+(?P<local>.+))?$", t)
    if m:
        return m.group("cargo").strip(), m.group("emp").strip(), (m.group("local") or "").strip()
    m = (re.match(r"^(?P<emp>.+?) (?:está )?contratando (?P<cargo>.+) em (?P<local>[^|]+)$", t)
         or re.match(r"^(?P<emp>.+?) (?:is )?hiring (?P<cargo>.+) in (?P<local>[^|]+)$", t)
         or re.match(r"^(?P<emp>.+?) (?:está )?contratando (?P<cargo>.+)$", t)
         or re.match(r"^(?P<emp>.+?) (?:is )?hiring (?P<cargo>.+)$", t))
    if m:
        return m.group("cargo").strip(), m.group("emp").strip(), (m.groupdict().get("local") or "").strip()
    partes = [p.strip() for p in re.split(r"\s+[|\-–—]\s+", t) if p.strip()]
    if len(partes) >= 2:
        return partes[0], partes[1], ""
    return t, "", ""


def interpretar_publicacao_linkedin(titulo):
    """'Fulano no LinkedIn: texto…' -> (autor, texto)."""
    t = limpar_titulo_linkedin(titulo)
    m = re.match(r"^(?P<autor>.+?) (?:no|on) LinkedIn:\s*(?P<texto>.*)$", t)
    if m:
        return m.group("autor").strip(), m.group("texto").strip()
    m = re.match(r"^(?P<texto>.*?)\s*\|\s*(?P<autor>[^|]+?) (?:posted on the topic|publicou sobre o tema)", t)
    if m:
        return m.group("autor").strip(), m.group("texto").strip()
    return "", t


def parametros_linkedin(busca, api_key):
    """Monta a consulta no motor configurado. O padrão é o DuckDuckGo, que respeita o
    operador site:. O Google tende a ignorá-lo em buscas de emprego e devolver agregadores."""
    site = busca.get("site", "linkedin.com")
    consulta = f"site:{site} {busca['q']}"
    motor = busca.get("motor", CONFIG.get("linkedin_motor", "duckduckgo"))
    if motor == "google":
        return {"engine": "google", "q": consulta, "as_sitesearch": site.split("/")[0],
                "google_domain": "google.com.br", "gl": "br", "hl": "pt",
                "tbs": CONFIG.get("linkedin_periodo", "qdr:w"), "api_key": api_key}
    return {"engine": "duckduckgo", "q": consulta,
            "kl": CONFIG.get("linkedin_regiao_duckduckgo", "br-pt"),
            "df": CONFIG.get("linkedin_periodo_duckduckgo", "w"), "api_key": api_key}


def buscar_linkedin(busca, api_key):
    vagas = []
    try:
        r = requests.get(SERPAPI, params=parametros_linkedin(busca, api_key), timeout=60)
        resposta = r.json()
        if resposta.get("error"):
            print(f"[LinkedIn] '{busca['id']}': aviso do SerpApi -> {resposta['error']}")
        r.raise_for_status()
        resultados = resposta.get("organic_results", []) or []
    except Exception as e:
        print(f"[LinkedIn] erro em '{busca['id']}': {e}")
        return vagas

    descartes, antigas = [], 0
    for res in resultados:
        link = res.get("link", "")
        titulo = res.get("title", "")
        trecho = res.get("snippet", "")
        idade = idade_em_dias(res.get("date", ""))
        if idade is not None and idade > CONFIG.get("linkedin_dias_maximos", 7):
            antigas += 1
            continue
        publicada = formatar_data(res.get("date", "")) or "data não informada"

        if "linkedin.com" not in link:
            descartes.append(("não é do LinkedIn", titulo, link))
            continue
        if "/jobs/view" in link:
            cargo, empresa, local = interpretar_vaga_linkedin(titulo)
            # a consulta já exige termos de TI; aqui o título ou o trecho precisam confirmar
            if not e_ti(f"{cargo} {trecho}"):
                descartes.append(("vaga não parece de TI", titulo, link))
                continue
            vagas.append({"titulo": cargo, "empresa": empresa, "local": local,
                          "fonte": "LinkedIn", "publicada": publicada, "link": link,
                          "categoria": "ti", "resumo": resumir(trecho, 180)})

        elif "/posts/" in link or "/feed/update/" in link:
            autor, texto_titulo = interpretar_publicacao_linkedin(titulo)
            texto = f"{texto_titulo} {trecho}"
            if tem_termo(texto, CONFIG["termos_candidato"]):
                descartes.append(("candidato procurando vaga", titulo, link))
                continue
            # a consulta já exige palavras de anúncio de vaga; aqui basta confirmar que é de TI
            if not e_ti(texto):
                descartes.append(("publicação não parece de TI", titulo, link))
                continue
            vagas.append({"titulo": resumir(texto_titulo, 110) or "Publicação de vaga",
                          "empresa": autor, "local": "", "fonte": "Publicação no LinkedIn",
                          "publicada": publicada, "link": link, "categoria": "publicacao_ti",
                          "resumo": resumir(trecho), "publicacao": True,
                          "chave": normalizar(link.split("?")[0])})
        else:
            descartes.append(("endereço não é vaga nem publicação", titulo, link))

    print(f"[LinkedIn] '{busca['id']}': {len(resultados)} resultados | "
          f"aproveitados: {len(vagas)} | descartados: {len(descartes)} | antigos: {antigas}")
    for motivo, titulo, link in descartes[:8]:
        print(f"    descartado ({motivo}): {titulo[:90]} | {link[:80]}")
    return vagas


def buscar_pagas(agora):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("[SerpApi] SERPAPI_KEY não definida: pulando LinkedIn e Google Vagas")
        return [], None
    quantidade, restantes = buscas_disponiveis(api_key, agora)
    if quantidade <= 0:
        print("[SerpApi] cota do mês esgotada ou muito baixa: só a Gupy será consultada")
        return [], restantes
    vagas = []
    for busca in escolher_buscas(quantidade, agora):
        if busca["tipo"] == "google_vagas":
            vagas += buscar_google_vagas(busca["q"], api_key)
        else:
            vagas += buscar_linkedin(busca, api_key)
        time.sleep(1)
    if restantes is not None:
        restantes = max(0, restantes - quantidade)
    return vagas, restantes


# ================================================================ histórico
def carregar_vistas():
    try:
        return json.loads(ARQ_VISTAS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_vistas(vistas):
    corte = (datetime.now(BRASILIA) - timedelta(days=DIAS_HISTORICO)).strftime("%Y-%m-%d")
    vistas = {k: v for k, v in vistas.items() if v >= corte}
    ARQ_VISTAS.write_text(json.dumps(vistas, ensure_ascii=False, indent=1), encoding="utf-8")


# ================================================================ e-mail
COR = {
    "fundo": "#0b0b0c", "cartao": "#151517", "borda": "#26262a", "laranja": "#ff7a1a",
    "laranja_suave": "#2a1a0e", "texto": "#f2f2f3", "suave": "#a1a1aa", "apagado": "#6b6b73",
}


def contagem(vagas):
    return {cat: sum(1 for v in vagas if v["categoria"] == cat) for cat, _, _ in SECOES}


def cartao_html(v):
    e = html.escape
    meta = " · ".join(e(x) for x in [v.get("empresa"), v.get("local"), v.get("publicada")] if x)
    resumo = ""
    if v.get("resumo") and v.get("publicacao"):
        resumo = (f"<p style='margin:10px 0 0;font-size:13px;line-height:1.55;color:{COR['suave']};"
                  f"border-left:2px solid {COR['laranja']};padding-left:10px'>{e(v['resumo'])}</p>")
    rotulo = "Ver publicação" if v.get("publicacao") else "Ver vaga"
    botao = (f"<a href='{e(v['link'])}' style='display:inline-block;padding:9px 18px;border-radius:8px;"
             f"background:{COR['laranja']};color:#111111;font-size:13px;font-weight:700;"
             f"text-decoration:none'>{rotulo} →</a>")
    return (
        f"<tr><td style='padding:0 0 12px'>"
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0' bgcolor='{COR['cartao']}' "
        f"style='background:{COR['cartao']};border:1px solid {COR['borda']};border-radius:12px'>"
        f"<tr><td style='padding:16px 18px'>"
        f"<div style='font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:{COR['laranja']};"
        f"font-weight:700;margin-bottom:6px'>{e(v['fonte'])}</div>"
        f"<a href='{e(v['link'])}' style='font-size:16px;line-height:1.35;font-weight:700;color:{COR['texto']};"
        f"text-decoration:none'>{e(v['titulo'])}</a>"
        f"<div style='font-size:13px;color:{COR['apagado']};margin-top:5px'>{meta}</div>"
        f"{resumo}"
        f"<div style='margin-top:14px'>{botao}</div>"
        f"</td></tr></table></td></tr>"
    )


def montar_html(vagas, restantes=None):
    e = html.escape
    qtd = contagem(vagas)
    hoje = datetime.now(BRASILIA).strftime("%d/%m/%Y")
    chips = "".join(
        f"<span style='display:inline-block;margin:0 6px 6px 0;padding:5px 11px;border-radius:999px;"
        f"background:{COR['laranja_suave']};color:{COR['laranja']};font-size:12px;font-weight:600'>"
        f"{icone} {qtd[cat]} {ROTULO_CURTO[cat]}</span>"
        for cat, nome, icone in SECOES if qtd[cat]
    )
    secoes = []
    for cat, nome, icone in SECOES:
        itens = [v for v in vagas if v["categoria"] == cat]
        if not itens:
            continue
        secoes.append(
            f"<tr><td style='padding:22px 0 10px'>"
            f"<div style='font-size:13px;font-weight:700;color:{COR['texto']};letter-spacing:.02em'>"
            f"<span style='color:{COR['laranja']}'>{icone}</span>&nbsp; {e(nome)}"
            f"<span style='color:{COR['apagado']};font-weight:500'>&nbsp; {len(itens)}</span></div>"
            f"</td></tr>"
            + "".join(cartao_html(v) for v in itens)
        )
    rodape_cota = (f" · {restantes} buscas restantes no SerpApi" if restantes is not None else "")
    preheader = " · ".join(f"{qtd[c]} {ROTULO_CURTO[c]}" for c, _, _ in SECOES if qtd[c])
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark">
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:{COR['fundo']}" bgcolor="{COR['fundo']}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{COR['fundo']}" style="background:{COR['fundo']}">
<tr><td align="center" style="padding:28px 14px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
<tr><td style="padding:0 0 4px"><div style="height:4px;width:56px;background:{COR['laranja']};border-radius:4px"></div></td></tr>
<tr><td style="padding:14px 0 4px;font-size:24px;font-weight:800;color:{COR['texto']}">Radar de vagas</td></tr>
<tr><td style="padding:0 0 14px;font-size:13px;color:{COR['apagado']}">{hoje} · {len(vagas)} novidade(s) desde o último envio</td></tr>
<tr><td>{chips}</td></tr>
{''.join(secoes)}
<tr><td style="padding:22px 0 0;border-top:1px solid {COR['borda']};font-size:11px;color:{COR['apagado']}">
Enviado pelo seu robô de vagas{e(rodape_cota)}</td></tr>
</table></td></tr></table></body></html>"""


def montar_texto(vagas):
    linhas = []
    for cat, nome, _ in SECOES:
        itens = [v for v in vagas if v["categoria"] == cat]
        if itens:
            linhas.append(f"== {nome} ==")
            linhas += [f"{v['titulo']} – {v['empresa']} ({v['fonte']})\n{v['link']}\n" for v in itens]
    return "\n".join(linhas) or "Nenhuma vaga nova."


def assunto(vagas):
    qtd = contagem(vagas)
    hoje = datetime.now(BRASILIA).strftime("%d/%m")
    if not vagas:
        return f"Nenhuma vaga nova – {hoje}"
    ti = qtd["ti"] + qtd["estagio"]
    partes = []
    if ti:
        partes.append(f"{ti} vaga(s) de TI")
    if qtd["publicacao_ti"]:
        partes.append(f"{qtd['publicacao_ti']} publicação(ões)")
    return f"🎯 {' · '.join(partes)} – {hoje}"


def enviar_email(vagas, restantes=None):
    remetente = os.environ["EMAIL_REMETENTE"]
    senha = os.environ["EMAIL_SENHA_APP"]
    destino = os.getenv("EMAIL_DESTINO") or remetente

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto(vagas)
    msg["From"] = remetente
    msg["To"] = destino
    msg.attach(MIMEText(montar_texto(vagas), "plain", "utf-8"))
    msg.attach(MIMEText(montar_html(vagas, restantes), "html", "utf-8"))

    servidor = os.getenv("SMTP_SERVIDOR", "smtp.gmail.com")
    porta = int(os.getenv("SMTP_PORTA", "465"))
    with smtplib.SMTP_SSL(servidor, porta) as smtp:
        smtp.login(remetente, senha)
        smtp.send_message(msg)
    print(f"E-mail enviado para {destino}")


# ================================================================ principal
def main():
    teste = "--teste" in sys.argv
    if not teste and not (os.getenv("EMAIL_REMETENTE") and os.getenv("EMAIL_SENHA_APP")):
        print("Credenciais de e-mail não configuradas: rodando em modo teste (sem envio).")
        teste = True

    agora = datetime.now(timezone.utc)
    vistas = carregar_vistas()
    hoje = agora.astimezone(BRASILIA).strftime("%Y-%m-%d")

    pagas, restantes = buscar_pagas(agora)
    novas, chaves_rodada = [], set()
    for v in buscar_gupy() + pagas:
        k = chave(v)
        if not v["link"] or k in vistas or k in chaves_rodada:
            continue
        chaves_rodada.add(k)
        novas.append(v)
    ordem = {cat: i for i, (cat, _, _) in enumerate(SECOES)}
    novas.sort(key=lambda v: ordem.get(v["categoria"], 99))

    resumo = ", ".join(f"{n}: {q}" for (c, n, _), q in zip(SECOES, contagem(novas).values()))
    print(f"Total de novidades: {len(novas)} ({resumo})")

    if teste:
        for v in novas:
            print(f"- [{v['categoria']}] [{v['fonte']}] {v['titulo']} | {v['empresa']} | {v['local']}\n  {v['link']}")
        return

    if novas or CONFIG.get("enviar_email_sem_vagas"):
        enviar_email(novas, restantes)
    for k in chaves_rodada:
        vistas[k] = hoje
    salvar_vistas(vistas)


if __name__ == "__main__":
    main()
