"""Histórico de vagas já enviadas (vagas_vistas.json) e estatísticas mensais (estatisticas.json).

Um arquivo ausente é tratado como vazio. Um arquivo corrompido interrompe a
execução: tratá-lo como vazio faria o robô reenviar todas as vagas antigas e
sobrescrever o histórico.
"""

import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path

MESES_GUARDADOS = 12


class HistoricoInvalido(Exception):
    pass


def _ler(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise HistoricoInvalido(f"{caminho.name} está corrompido (linha {e.lineno}): corrija ou restaure "
                                "a versão anterior pelo histórico do GitHub") from None
    if not isinstance(dados, dict):
        raise HistoricoInvalido(f"{caminho.name} deve conter um objeto JSON")
    return dados


def _gravar(caminho, dados):
    """Grava em um arquivo temporário e troca de uma vez: nunca deixa o arquivo pela metade."""
    caminho = Path(caminho)
    fd, temporario = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        os.replace(temporario, caminho)
    except BaseException:
        if os.path.exists(temporario):
            os.remove(temporario)
        raise


# ---------------------------------------------------------------- vagas vistas
def carregar_vistas(caminho):
    vistas = _ler(caminho)
    for chave, data in vistas.items():
        if not isinstance(chave, str) or not isinstance(data, str):
            raise HistoricoInvalido("vagas_vistas.json deve mapear cada vaga para uma data (texto)")
    return vistas


def registrar_vistas(vistas, chaves, hoje):
    data = hoje.strftime("%Y-%m-%d")
    for chave in chaves:
        vistas[chave] = data
    return vistas


def salvar_vistas(caminho, vistas, hoje, dias):
    corte = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    _gravar(caminho, {k: v for k, v in vistas.items() if v >= corte})


# ---------------------------------------------------------------- estatísticas
def carregar_estatisticas(caminho):
    return _ler(caminho)


def registrar_estatisticas(estatisticas, vagas, hoje):
    """Conta, no mês, quantas vagas novas citam cada tecnologia e quantas houve por trilha."""
    mes = hoje.strftime("%Y-%m")
    atual = estatisticas.setdefault(mes, {"vagas": 0, "termos": {}, "trilhas": {}})
    atual.setdefault("termos", {})
    atual.setdefault("trilhas", {})
    atual["vagas"] = int(atual.get("vagas", 0)) + len(vagas)
    for v in vagas:
        for termo in v.termos_stack:
            atual["termos"][termo] = atual["termos"].get(termo, 0) + 1
        atual["trilhas"][v.trilha] = atual["trilhas"].get(v.trilha, 0) + 1
    for antigo in sorted(estatisticas)[:-MESES_GUARDADOS]:
        del estatisticas[antigo]
    return estatisticas


def mais_citados(estatisticas, hoje, quantidade=8):
    termos = (estatisticas.get(hoje.strftime("%Y-%m")) or {}).get("termos") or {}
    return sorted(termos.items(), key=lambda item: (-item[1], item[0]))[:quantidade]


def salvar_estatisticas(caminho, estatisticas):
    _gravar(caminho, estatisticas)
