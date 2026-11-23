"""Montagem do e-mail (HTML e texto puro), do assunto e da planilha CSV.

O HTML usa tabelas e estilos inline, porque clientes de e-mail ignoram boa parte
do CSS moderno. Paleta: preto, branco, cinzas e um único laranja de destaque.
"""

import csv
import html
import io

from . import NOME, REPOSITORIO, __version__

COR = {
    "fundo": "#0a0a0a",
    "texto": "#fafafa",
    "secundario": "#a3a3a3",
    "terciario": "#737373",
    "linha": "#262626",
    "laranja": "#ff7a1a",
}
FONTE = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
PUBLICACOES = {"id": "publicacoes", "nome": "Publicações de recrutadores",
               "curriculo": "o da trilha indicada em cada publicação"}
COLUNAS_CSV = ["data_envio", "trilha", "curriculo", "vaga", "empresa", "local", "modalidade", "nivel",
               "fonte", "publicada", "link", "contato", "status", "proximo_passo"]


def nome_curto(trilha_nome):
    return trilha_nome.split()[0]


def secoes(vagas, cfg):
    """[(definição da seção, vagas ordenadas)] na ordem das trilhas; publicações por último."""
    ordem = lambda v: (-v.pontuacao, v.titulo.lower())  # noqa: E731
    resultado = []
    for t in cfg["trilhas"]:
        itens = sorted((v for v in vagas if not v.publicacao and v.trilha == t["id"]), key=ordem)
        if itens:
            resultado.append((t, itens))
    posts = sorted((v for v in vagas if v.publicacao), key=ordem)
    if posts:
        resultado.append((PUBLICACOES, posts))
    return resultado


def contagem(vagas, cfg):
    return [(nome_curto(s["nome"]) if s is not PUBLICACOES else "Publicações", len(itens))
            for s, itens in secoes(vagas, cfg)]


def assunto(vagas, cfg, agora_br):
    quando = agora_br.strftime("%d/%m %Hh")
    if not vagas:
        return f"{NOME} · nenhuma vaga nova · {quando}"
    partes = " · ".join(f"{nome} {n}" for nome, n in contagem(vagas, cfg))
    total = len(vagas)
    return f"{NOME} · {total} {'vaga nova' if total == 1 else 'vagas novas'} · {partes} · {quando}"


# ---------------------------------------------------------------- HTML
def _e(texto):
    return html.escape(str(texto or ""), quote=True)


def _item(v):
    meta = " · ".join(_e(x) for x in (v.empresa, v.local, v.publicada) if x)
    etiquetas = [v.fonte, v.nivel, v.modalidade]
    if v.curriculo.endswith("(versão em inglês)"):
        etiquetas.append("currículo em inglês")
    if v.publicacao:
        etiquetas.insert(1, nome_curto(v.trilha_nome))
    etiquetas_html = " · ".join(_e(x) for x in etiquetas if x)
    resumo = ""
    if v.publicacao and v.resumo:
        resumo = (f"<div style='margin:8px 0 0;padding-left:10px;border-left:2px solid {COR['laranja']};"
                  f"font-size:13px;line-height:1.5;color:{COR['secundario']}'>{_e(v.resumo)}</div>")
    alertas = "".join(f"<div style='margin-top:6px;font-size:12px;color:{COR['laranja']}'>Atenção: {_e(a)}</div>"
                      for a in v.alertas)
    rotulo = "Abrir publicação" if v.publicacao else "Abrir vaga"
    return (
        f"<tr><td style='padding:14px 0;border-top:1px solid {COR['linha']}'>"
        f"<a href='{_e(v.link)}' style='font-size:15px;line-height:1.4;font-weight:600;color:{COR['texto']};"
        f"text-decoration:none'>{_e(v.titulo)}</a>"
        f"<div style='margin-top:3px;font-size:13px;color:{COR['secundario']}'>{meta}</div>"
        f"<div style='margin-top:3px;font-size:12px;color:{COR['terciario']}'>{etiquetas_html}</div>"
        f"{resumo}{alertas}"
        f"<div style='margin-top:8px'><a href='{_e(v.link)}' style='font-size:13px;font-weight:600;"
        f"color:{COR['laranja']};text-decoration:none'>{rotulo} &rarr;</a></div>"
        f"</td></tr>"
    )


def montar_html(vagas, cfg, agora_br, rodape):
    """rodape: dict com 'mais_citados' [(termo, n)], 'falhas' [str] e 'restantes' (int ou None)."""
    limite = cfg["email"]["max_por_secao"]
    total = len(vagas)
    resumo_topo = " · ".join(f"{nome} {n}" for nome, n in contagem(vagas, cfg))
    blocos = []
    for definicao, itens in secoes(vagas, cfg):
        mostrados, ocultos = itens[:limite], len(itens) - min(len(itens), limite)
        blocos.append(
            f"<tr><td style='padding:28px 0 6px'>"
            f"<div style='font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
            f"color:{COR['laranja']}'>{_e(definicao['nome'])} &nbsp;<span style='color:{COR['terciario']}'>"
            f"{len(itens)}</span></div>"
            f"<div style='margin-top:4px;font-size:12px;color:{COR['terciario']}'>"
            f"Currículo: {_e(definicao['curriculo'])}</div></td></tr>"
        )
        blocos.extend(_item(v) for v in mostrados)
        if ocultos:
            blocos.append(f"<tr><td style='padding:10px 0;border-top:1px solid {COR['linha']};font-size:12px;"
                          f"color:{COR['terciario']}'>+ {ocultos} nesta trilha na planilha anexa</td></tr>")

    linhas_rodape = []
    if rodape.get("mais_citados"):
        termos = " · ".join(f"{_e(t)} {n}" for t, n in rodape["mais_citados"])
        linhas_rodape.append(f"Mais citados em {MESES[agora_br.month - 1]}: {termos}")
    for falha in rodape.get("falhas") or []:
        linhas_rodape.append(f"<span style='color:{COR['laranja']}'>Fonte com falha: {_e(falha)}</span>")
    if rodape.get("restantes") is not None:
        linhas_rodape.append(f"Buscas SerpApi restantes: {rodape['restantes']}")
    linhas_rodape.append(f"{NOME} v{__version__} · <a href='{REPOSITORIO}' style='color:{COR['terciario']}'>"
                         f"código no GitHub</a>")
    rodape_html = "".join(f"<div style='margin-top:4px'>{linha}</div>" for linha in linhas_rodape)

    titulo = "Nenhuma vaga nova" if not total else f"{total} {'vaga nova' if total == 1 else 'vagas novas'}"
    return (
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta name='color-scheme' content='dark'><meta name='supported-color-schemes' content='dark'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'></head>"
        f"<body style='margin:0;padding:0;background:{COR['fundo']}' bgcolor='{COR['fundo']}'>"
        f"<div style='display:none;max-height:0;overflow:hidden'>{_e(resumo_topo)}</div>"
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0' bgcolor='{COR['fundo']}' "
        f"style='background:{COR['fundo']}'><tr><td align='center' style='padding:32px 16px'>"
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
        f"style='max-width:600px;font-family:{FONTE}'>"
        f"<tr><td style='font-size:12px;font-weight:700;letter-spacing:.3em;color:{COR['laranja']}'>{NOME}</td></tr>"
        f"<tr><td style='padding-top:10px;font-size:24px;font-weight:700;color:{COR['texto']}'>{titulo}</td></tr>"
        f"<tr><td style='padding-top:6px;font-size:13px;color:{COR['secundario']}'>"
        f"{agora_br.strftime('%d/%m/%Y · %Hh')}{' · ' + _e(resumo_topo) if resumo_topo else ''}</td></tr>"
        f"{''.join(blocos)}"
        f"<tr><td style='padding-top:28px;border-top:1px solid {COR['linha']};font-size:11px;line-height:1.6;"
        f"color:{COR['terciario']}'>{rodape_html}</td></tr>"
        "</table></td></tr></table></body></html>"
    )


# ---------------------------------------------------------------- texto puro
def montar_texto(vagas, cfg, agora_br, rodape):
    linhas = [f"{NOME} · {agora_br.strftime('%d/%m/%Y %Hh')}", ""]
    if not vagas:
        linhas.append("Nenhuma vaga nova.")
    for definicao, itens in secoes(vagas, cfg):
        linhas.append(f"== {definicao['nome']} ({len(itens)}) · Currículo: {definicao['curriculo']} ==")
        for v in itens:
            detalhes = " · ".join(x for x in (v.empresa, v.local, v.modalidade, v.nivel, v.fonte) if x)
            linhas.append(f"- {v.titulo} | {detalhes}")
            for alerta in v.alertas:
                linhas.append(f"  Atenção: {alerta}")
            linhas.append(f"  {v.link}")
        linhas.append("")
    for falha in rodape.get("falhas") or []:
        linhas.append(f"Fonte com falha: {falha}")
    return "\n".join(linhas).strip() + "\n"


# ---------------------------------------------------------------- planilha
def montar_csv(vagas, cfg, agora_br):
    """Planilha no formato do controle de candidaturas da consultoria.

    Separador ';' e codificação UTF-8 com BOM, para abrir certo no Excel em
    português e no Google Planilhas.
    """
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUNAS_CSV)
    data_envio = agora_br.strftime("%d/%m/%Y")
    for definicao, itens in secoes(vagas, cfg):
        for v in itens:
            escritor.writerow([data_envio, v.trilha_nome, v.curriculo, v.titulo, v.empresa, v.local,
                               v.modalidade, v.nivel, v.fonte, v.publicada, v.link, "", "", ""])
    return ("\ufeff" + saida.getvalue()).encode("utf-8")
