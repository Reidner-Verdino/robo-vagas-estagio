"""Leitura e validação do config.json.

A validação é estrita de propósito: qualquer chave faltando, tipo errado ou valor
fora do intervalo interrompe a execução com uma mensagem clara, em vez de deixar
o robô rodar com uma configuração que produziria resultados errados.
"""

import json
from pathlib import Path

from .texto import padrao


class ConfigInvalida(Exception):
    pass


def _lista_de_termos(valor, caminho, erros, vazia_ok=False):
    if not isinstance(valor, list) or (not valor and not vazia_ok):
        erros.append(f"{caminho}: deve ser uma lista {'de textos' if vazia_ok else 'não vazia de textos'}")
        return
    for i, termo in enumerate(valor):
        if not isinstance(termo, str) or not termo.strip():
            erros.append(f"{caminho}[{i}]: deve ser um texto não vazio")
            continue
        try:
            padrao(termo)
        except ValueError as e:
            erros.append(f"{caminho}[{i}]: {e}")


def _inteiro(valor, caminho, erros, minimo, maximo):
    if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
        erros.append(f"{caminho}: deve ser um número inteiro entre {minimo} e {maximo}")


def _booleano(valor, caminho, erros):
    if not isinstance(valor, bool):
        erros.append(f"{caminho}: deve ser true ou false")


def _texto(valor, caminho, erros):
    if not isinstance(valor, str) or not valor.strip():
        erros.append(f"{caminho}: deve ser um texto não vazio")


def _secao(cfg, nome, erros):
    valor = cfg.get(nome)
    if not isinstance(valor, dict):
        erros.append(f"{nome}: seção obrigatória ausente ou inválida")
        return {}
    return valor


def validar(cfg):
    erros = []
    if not isinstance(cfg, dict):
        raise ConfigInvalida("o config.json deve conter um objeto JSON")

    perfil = _secao(cfg, "perfil", erros)
    _lista_de_termos(perfil.get("cidades_presencial"), "perfil.cidades_presencial", erros)
    _lista_de_termos(perfil.get("regioes_exterior_aceitas"), "perfil.regioes_exterior_aceitas", erros)
    _booleano(perfil.get("aceitar_nivel_nao_informado"), "perfil.aceitar_nivel_nao_informado", erros)
    _lista_de_termos(perfil.get("locais_prioritarios"), "perfil.locais_prioritarios", erros, vazia_ok=True)
    _inteiro(perfil.get("bonus_local_prioritario"), "perfil.bonus_local_prioritario", erros, 0, 50)
    _lista_de_termos(perfil.get("sites_prioritarios"), "perfil.sites_prioritarios", erros, vazia_ok=True)
    _inteiro(perfil.get("bonus_site_prioritario"), "perfil.bonus_site_prioritario", erros, 0, 50)

    trilhas = cfg.get("trilhas")
    if not isinstance(trilhas, list) or not trilhas:
        erros.append("trilhas: deve ser uma lista não vazia")
        trilhas = []
    ids = set()
    for i, t in enumerate(trilhas):
        base = f"trilhas[{i}]"
        if not isinstance(t, dict):
            erros.append(f"{base}: deve ser um objeto")
            continue
        _texto(t.get("id"), f"{base}.id", erros)
        if t.get("id") in ids:
            erros.append(f"{base}.id: '{t.get('id')}' repetido")
        ids.add(t.get("id"))
        if t.get("id") == "publicacoes":
            erros.append(f"{base}.id: 'publicacoes' é reservado")
        _texto(t.get("nome"), f"{base}.nome", erros)
        _texto(t.get("curriculo"), f"{base}.curriculo", erros)
        _inteiro(t.get("peso"), f"{base}.peso", erros, 0, 100)
        _booleano(t.get("aceita_publicacoes"), f"{base}.aceita_publicacoes", erros)
        _lista_de_termos(t.get("termos"), f"{base}.termos", erros)
        if "termos_somente_vagas" in t:
            _lista_de_termos(t.get("termos_somente_vagas"), f"{base}.termos_somente_vagas", erros)

    niveis = _secao(cfg, "niveis", erros)
    aceitos = niveis.get("aceitos")
    if not isinstance(aceitos, list) or not aceitos or \
            any(x not in ("estagio", "junior", "trainee") for x in aceitos):
        erros.append('niveis.aceitos: lista não vazia com "estagio", "junior" e/ou "trainee"')
    for nome in ("estagio", "trainee", "junior", "excluidos"):
        _lista_de_termos(niveis.get(nome), f"niveis.{nome}", erros)

    for nome in ("termos_excluir", "termos_remoto", "termos_hibrido", "termos_sinal_vaga",
                 "termos_candidato", "termos_alerta", "termos_stack"):
        _lista_de_termos(cfg.get(nome), nome, erros)

    fontes = _secao(cfg, "fontes", erros)
    gupy = fontes.get("gupy") if isinstance(fontes.get("gupy"), dict) else None
    if gupy is None:
        erros.append("fontes.gupy: seção obrigatória ausente")
    else:
        _booleano(gupy.get("ativa"), "fontes.gupy.ativa", erros)
        _inteiro(gupy.get("dias_maximos"), "fontes.gupy.dias_maximos", erros, 1, 60)
        _inteiro(gupy.get("paginas_por_termo"), "fontes.gupy.paginas_por_termo", erros, 1, 10)
        _lista_de_termos(gupy.get("termos"), "fontes.gupy.termos", erros)

    google = fontes.get("google_vagas") if isinstance(fontes.get("google_vagas"), dict) else None
    if google is None:
        erros.append("fontes.google_vagas: seção obrigatória ausente")
    else:
        _booleano(google.get("ativa"), "fontes.google_vagas.ativa", erros)
        _inteiro(google.get("peso"), "fontes.google_vagas.peso", erros, 1, 10)
        _inteiro(google.get("dias_maximos"), "fontes.google_vagas.dias_maximos", erros, 1, 60)
        _booleano(google.get("aceitar_sem_data"), "fontes.google_vagas.aceitar_sem_data", erros)
        _texto(google.get("localizacao"), "fontes.google_vagas.localizacao", erros)
        _lista_de_termos(google.get("consultas"), "fontes.google_vagas.consultas", erros)

    ids_busca = {"recrutadores_favoritos"}
    linkedin = fontes.get("linkedin") if isinstance(fontes.get("linkedin"), dict) else None
    if linkedin is None:
        erros.append("fontes.linkedin: seção obrigatória ausente")
    else:
        _booleano(linkedin.get("ativa"), "fontes.linkedin.ativa", erros)
        if linkedin.get("motor") not in ("duckduckgo", "google"):
            erros.append("fontes.linkedin.motor: deve ser \"duckduckgo\" ou \"google\"")
        for nome in ("regiao_duckduckgo", "periodo_duckduckgo", "periodo_google"):
            _texto(linkedin.get(nome), f"fontes.linkedin.{nome}", erros)
        _inteiro(linkedin.get("dias_maximos"), "fontes.linkedin.dias_maximos", erros, 1, 60)
        _lista_de_termos(linkedin.get("recrutadores"), "fontes.linkedin.recrutadores", erros, vazia_ok=True)
        _inteiro(linkedin.get("recrutadores_peso"), "fontes.linkedin.recrutadores_peso", erros, 1, 10)
        buscas = linkedin.get("buscas")
        if not isinstance(buscas, list):
            erros.append("fontes.linkedin.buscas: deve ser uma lista")
            buscas = []
        for i, b in enumerate(buscas):
            base = f"fontes.linkedin.buscas[{i}]"
            if not isinstance(b, dict):
                erros.append(f"{base}: deve ser um objeto")
                continue
            for nome in ("id", "site", "q"):
                _texto(b.get(nome), f"{base}.{nome}", erros)
            _inteiro(b.get("peso"), f"{base}.peso", erros, 1, 10)
            if b.get("id") in ids_busca:
                erros.append(f"{base}.id: '{b.get('id')}' repetido ou reservado")
            ids_busca.add(b.get("id"))
            if isinstance(b.get("site"), str) and "linkedin.com" not in b["site"]:
                erros.append(f"{base}.site: deve ser um endereço do linkedin.com")

    sites = fontes.get("sites") if isinstance(fontes.get("sites"), dict) else None
    if sites is None:
        erros.append("fontes.sites: seção obrigatória ausente")
    else:
        _booleano(sites.get("ativa"), "fontes.sites.ativa", erros)
        _inteiro(sites.get("peso"), "fontes.sites.peso", erros, 1, 10)
        _inteiro(sites.get("dias_maximos"), "fontes.sites.dias_maximos", erros, 1, 60)
        _booleano(sites.get("aceitar_sem_data"), "fontes.sites.aceitar_sem_data", erros)
        for nome in ("regiao_duckduckgo", "periodo_duckduckgo"):
            _texto(sites.get(nome), f"fontes.sites.{nome}", erros)
        lista = sites.get("lista")
        if not isinstance(lista, list):
            erros.append("fontes.sites.lista: deve ser uma lista")
            lista = []
        for i, item in enumerate(lista):
            base = f"fontes.sites.lista[{i}]"
            if not isinstance(item, dict):
                erros.append(f"{base}: deve ser um objeto")
                continue
            for nome in ("id", "nome", "dominio", "q"):
                _texto(item.get(nome), f"{base}.{nome}", erros)
            dominio = item.get("dominio")
            if isinstance(dominio, str) and ("/" in dominio or " " in dominio or "." not in dominio):
                erros.append(f"{base}.dominio: use só o domínio, como \"catho.com.br\"")
            if item.get("id") in ids_busca:
                erros.append(f"{base}.id: '{item.get('id')}' repetido")
            ids_busca.add(item.get("id"))

    remotive = fontes.get("remotive") if isinstance(fontes.get("remotive"), dict) else None
    if remotive is None:
        erros.append("fontes.remotive: seção obrigatória ausente")
    else:
        _booleano(remotive.get("ativa"), "fontes.remotive.ativa", erros)
        _inteiro(remotive.get("dias_maximos"), "fontes.remotive.dias_maximos", erros, 1, 60)

    serp = _secao(cfg, "serpapi", erros)
    _inteiro(serp.get("dia_renovacao"), "serpapi.dia_renovacao", erros, 1, 31)
    _inteiro(serp.get("execucoes_por_dia"), "serpapi.execucoes_por_dia", erros, 1, 24)
    _inteiro(serp.get("buscas_por_execucao_padrao"), "serpapi.buscas_por_execucao_padrao", erros, 0, 50)

    email = _secao(cfg, "email", erros)
    _inteiro(email.get("max_por_secao"), "email.max_por_secao", erros, 1, 200)
    _booleano(email.get("enviar_sem_vagas"), "email.enviar_sem_vagas", erros)
    _booleano(email.get("anexar_csv"), "email.anexar_csv", erros)

    historico = _secao(cfg, "historico", erros)
    _inteiro(historico.get("dias"), "historico.dias", erros, 7, 3650)

    if erros:
        raise ConfigInvalida("config.json inválido:\n  - " + "\n  - ".join(erros))
    return cfg


def carregar(caminho):
    caminho = Path(caminho)
    try:
        cfg = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigInvalida(f"arquivo não encontrado: {caminho}") from None
    except json.JSONDecodeError as e:
        raise ConfigInvalida(f"config.json com erro de sintaxe na linha {e.lineno}, coluna {e.colno}: {e.msg}") from None
    return validar(cfg)
