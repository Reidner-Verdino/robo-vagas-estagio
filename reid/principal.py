"""Execução completa do REID.

Uso:
    python -m reid               coleta, envia o e-mail e salva o histórico
    python -m reid --teste       coleta e mostra no terminal, sem enviar nem salvar
    python -m reid --validar     só valida o config.json
    python -m reid --teste --previa previa.html   grava também o e-mail em HTML

Códigos de saída: 0 sucesso · 1 falha na execução · 2 configuração inválida.
"""

import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import NOME, __version__, config, cota, envio, historico, relatorio
from .classificacao import classificar
from .fontes import google_vagas, gupy, linkedin, remotive, serpapi, sites
from .historico import HistoricoInvalido
from .rede import ErroRede
from .texto import BRASILIA

RAIZ = Path(__file__).resolve().parent.parent


def log(mensagem=""):
    print(mensagem, flush=True)


def anotar(tipo, mensagem, env):
    """Mostra avisos e erros em destaque na aba Actions do GitHub."""
    if env.get("GITHUB_ACTIONS") == "true":
        print(f"::{tipo} title={NOME}::{mensagem}", flush=True)


def agenda_paga(cfg):
    """Buscas que consomem cota da SerpApi, com seus pesos."""
    buscas = []
    fontes = cfg["fontes"]
    if fontes["linkedin"]["ativa"]:
        for b in linkedin.buscas_configuradas(fontes["linkedin"]):
            buscas.append({**b, "tipo": "linkedin"})
    if fontes["sites"]["ativa"]:
        for site in fontes["sites"]["lista"]:
            buscas.append({**site, "tipo": "sites", "peso": fontes["sites"]["peso"]})
    if fontes["google_vagas"]["ativa"]:
        for i, consulta in enumerate(fontes["google_vagas"]["consultas"], 1):
            buscas.append({"id": f"google_vagas_{i}", "tipo": "google_vagas", "q": consulta,
                           "peso": fontes["google_vagas"]["peso"]})
    return buscas


def coletar(cfg, env, agora):
    """Consulta todas as fontes ativas. Uma fonte com falha nunca interrompe as outras."""
    fontes = cfg["fontes"]
    hoje = agora.astimezone(BRASILIA).date()
    candidatos, falhas, descartes_endereco = [], [], []
    tentadas, responderam = [], set()
    restantes = None

    for nome, ativa, funcao in (("Gupy", fontes["gupy"]["ativa"], lambda: gupy.buscar(fontes["gupy"], agora)),
                                ("Remotive", fontes["remotive"]["ativa"],
                                 lambda: remotive.buscar(fontes["remotive"], agora))):
        if not ativa:
            continue
        tentadas.append(nome)
        try:
            recebidos, parciais = funcao()
        except ErroRede as e:
            falhas.append(f"{nome}: {e}")
            log(f"[{nome}] falhou: {e}")
            continue
        responderam.add(nome)
        candidatos += recebidos
        falhas += parciais
        log(f"[{nome}] {len(recebidos)} vagas recebidas" + (f" ({len(parciais)} consultas com falha)" if parciais else ""))

    pagas = agenda_paga(cfg)
    api_key = (env.get("SERPAPI_KEY") or "").strip()
    if pagas and not api_key:
        log("[SerpApi] SERPAPI_KEY não definida: LinkedIn e Google Vagas não foram consultados")
        falhas.append("SerpApi: chave SERPAPI_KEY não definida")
    elif pagas:
        try:
            restantes = serpapi.saldo(api_key)
        except ErroRede as e:
            quantidade = cfg["serpapi"]["buscas_por_execucao_padrao"]
            falhas.append(f"SerpApi (saldo): {e}")
            log(f"[Cota] não consegui consultar o saldo ({e}); usando {quantidade} buscas")
        else:
            quantidade, renovacao, execucoes = cota.buscas_permitidas(restantes, agora, cfg["serpapi"])
            log(f"[Cota] {restantes} buscas restantes até {renovacao:%d/%m} (~{execucoes} execuções) "
                f"-> {quantidade} nesta execução")
        escolhidas = cota.escolher(pagas, quantidade, agora)
        if escolhidas:
            tentadas.append("SerpApi")
        for busca in escolhidas:
            try:
                if busca["tipo"] == "google_vagas":
                    recebidos = google_vagas.buscar(busca["q"], fontes["google_vagas"], api_key, hoje)
                elif busca["tipo"] == "sites":
                    recebidos, descartes = sites.buscar(busca, fontes["sites"], api_key, hoje)
                    descartes_endereco += descartes
                else:
                    recebidos, descartes = linkedin.buscar(busca, fontes["linkedin"], api_key, hoje)
                    descartes_endereco += descartes
            except ErroRede as e:
                falhas.append(f"{busca['id']}: {e}")
                log(f"[{busca['id']}] falhou: {e}")
                continue
            responderam.add("SerpApi")
            candidatos += recebidos
            log(f"[{busca['id']}] {len(recebidos)} resultados aproveitáveis")
        if restantes is not None:
            restantes = max(0, restantes - len(escolhidas))

    for motivo, titulo, link in descartes_endereco[:8]:
        log(f"    descartado ({motivo}): {titulo[:80]} | {link[:80]}")

    todas_falharam = bool(tentadas) and not responderam
    return candidatos, falhas, restantes, todas_falharam


def avaliar(candidatos, cfg, vistas):
    """Classifica, remove repetidas (no histórico e na própria execução) e registra os descartes."""
    aceitas, descartes, exemplos = [], Counter(), defaultdict(list)
    for c in candidatos:
        vaga, motivo = classificar(c, cfg)
        if vaga:
            aceitas.append(vaga)
        else:
            descartes[(c.fonte, motivo)] += 1
            if len(exemplos[(c.fonte, motivo)]) < 2:
                exemplos[(c.fonte, motivo)].append(c.titulo)
    aceitas.sort(key=lambda v: -v.pontuacao)          # entre repetidas, fica a de maior pontuação
    novas, chaves, repetidas = [], set(), 0
    for v in aceitas:
        if v.chave in vistas or v.chave in chaves:
            repetidas += 1
            continue
        chaves.add(v.chave)
        novas.append(v)
    for (fonte, motivo), n in sorted(descartes.items(), key=lambda item: (item[0][0], -item[1])):
        exemplo = "; ".join(t[:60] for t in exemplos[(fonte, motivo)])
        log(f"    {fonte}: {n} descartada(s) por '{motivo}'" + (f" (ex.: {exemplo})" if exemplo else ""))
    log(f"Aceitas: {len(aceitas)} · já enviadas ou repetidas: {repetidas} · novas: {len(novas)}")
    return novas


def definir_modo(args, env):
    remetente = (env.get("EMAIL_REMETENTE") or "").strip()
    senha = (env.get("EMAIL_SENHA_APP") or "").strip()
    if args.teste:
        return "teste"
    if remetente and senha:
        return "producao"
    if remetente or senha:
        raise config.ConfigInvalida("credenciais incompletas: defina EMAIL_REMETENTE e EMAIL_SENHA_APP juntos")
    log("Credenciais de e-mail não configuradas: rodando em modo teste (sem envio e sem salvar).")
    return "teste"


def main(argv=None, env=None, raiz=None, agora=None):
    env = dict(os.environ) if env is None else env
    raiz = Path(raiz or RAIZ)
    parser = argparse.ArgumentParser(prog="reid", description=f"{NOME} v{__version__}")
    parser.add_argument("--teste", action="store_true", help="não envia e-mail nem salva histórico")
    parser.add_argument("--validar", action="store_true", help="só valida o config.json")
    parser.add_argument("--previa", metavar="ARQUIVO", help="grava o e-mail em HTML (útil com --teste)")
    args = parser.parse_args(argv)

    log(f"{NOME} v{__version__}")
    try:
        cfg = config.carregar(raiz / "config.json")
        if args.validar:
            log("config.json válido.")
            return 0
        modo = definir_modo(args, env)
    except config.ConfigInvalida as e:
        log(f"ERRO: {e}")
        anotar("error", str(e).replace("\n", " "), env)
        return 2

    agora = agora or datetime.now(timezone.utc)
    agora_br = agora.astimezone(BRASILIA)
    caminho_vistas, caminho_estat = raiz / "vagas_vistas.json", raiz / "estatisticas.json"
    try:
        vistas = historico.carregar_vistas(caminho_vistas)
        estatisticas = historico.carregar_estatisticas(caminho_estat)
    except HistoricoInvalido as e:
        log(f"ERRO: {e}")
        anotar("error", str(e), env)
        return 1

    candidatos, falhas, restantes, todas_falharam = coletar(cfg, env, agora)
    for falha in falhas:
        anotar("warning", falha, env)
    if todas_falharam:
        log("ERRO: todas as fontes consultadas falharam; nada foi enviado nem salvo.")
        anotar("error", "todas as fontes consultadas falharam", env)
        return 1

    novas = avaliar(candidatos, cfg, vistas)
    historico.registrar_estatisticas(estatisticas, novas, agora_br.date())
    rodape = {"mais_citados": historico.mais_citados(estatisticas, agora_br.date()),
              "falhas": falhas, "restantes": restantes}
    html = relatorio.montar_html(novas, cfg, agora_br, rodape)
    if args.previa:
        Path(args.previa).write_text(html, encoding="utf-8")
        log(f"Prévia do e-mail gravada em {args.previa}")

    if modo == "teste":
        for definicao, itens in relatorio.secoes(novas, cfg):
            log(f"\n== {definicao['nome']} ({len(itens)}) · Currículo: {definicao['curriculo']}")
            for v in itens:
                log(f"- [{v.pontuacao}] {v.titulo} | {v.empresa} | {v.modalidade} | {v.nivel} | {v.fonte}")
                log(f"  {v.link}")
        log("\nModo teste: nada foi enviado nem salvo.")
        return 0

    if novas or cfg["email"]["enviar_sem_vagas"]:
        remetente = env["EMAIL_REMETENTE"].strip()
        destino = (env.get("EMAIL_DESTINO") or "").strip() or remetente
        csv_bytes = relatorio.montar_csv(novas, cfg, agora_br) if cfg["email"]["anexar_csv"] and novas else None
        mensagem = envio.montar_mensagem(
            remetente, destino, relatorio.assunto(novas, cfg, agora_br),
            relatorio.montar_texto(novas, cfg, agora_br, rodape), html,
            csv_bytes, f"reid_vagas_{agora_br:%Y-%m-%d_%Hh}.csv")
        try:
            envio.enviar(mensagem, remetente, env["EMAIL_SENHA_APP"].strip(),
                         env.get("SMTP_SERVIDOR") or envio.SERVIDOR_PADRAO,
                         int(env.get("SMTP_PORTA") or envio.PORTA_PADRAO))
        except Exception as e:  # noqa: BLE001 — qualquer falha de envio deve aparecer e impedir o salvamento
            log(f"ERRO ao enviar o e-mail: {e.__class__.__name__}: {e}")
            anotar("error", f"falha ao enviar o e-mail: {e.__class__.__name__}", env)
            return 1
        log(f"E-mail enviado com {len(novas)} vaga(s).")
    else:
        log("Nenhuma vaga nova: e-mail não enviado.")

    historico.registrar_vistas(vistas, [v.chave for v in novas], agora_br.date())
    historico.salvar_vistas(caminho_vistas, vistas, agora_br.date(), cfg["historico"]["dias"])
    historico.salvar_estatisticas(caminho_estat, estatisticas)
    log("Histórico salvo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
