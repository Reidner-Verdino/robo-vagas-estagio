"""Avaliação de cada candidato a vaga.

Todas as fontes passam pela mesma função, na mesma ordem de regras, para que um
critério nunca valha numa fonte e não em outra. A função devolve a Vaga aceita
ou o motivo exato do descarte, que vai para o log.
"""

from urllib.parse import urlparse

from .modelo import Vaga
from .texto import normalizar, tem_termo, termos_encontrados

PONTOS_NIVEL = {"Estágio": 10, "Júnior": 10, "Trainee": 8, "Não informado": 0}
PONTOS_MODALIDADE = {"Remoto": 6, "Híbrido (RJ)": 6, "Presencial (RJ)": 4, "Remoto (exterior)": 5, "A confirmar": 0}
IDS_NIVEL = {"Estágio": "estagio", "Júnior": "junior", "Trainee": "trainee"}
LOCAIS_GENERICOS = {"", "brasil", "brazil", "br"}

# Motivos de descarte (usados no log e nos testes)
SEM_DADOS = "dados incompletos"
SEM_DATA = "sem data"
ANTIGA = "mais antiga que o limite"
EXCLUIDA = "termo excluído"
FORA_DE_TI = "fora das trilhas de TI"
NAO_ANUNCIO = "não anuncia vaga"
CANDIDATO = "candidato procurando vaga"
NIVEL_ALTO = "nível acima de júnior"
NIVEL_NAO_INFORMADO = "nível não informado"
NIVEL_NAO_ACEITO = "nível não aceito"
REGIAO_EXTERIOR = "região do exterior não aceita"
FORA_DA_REGIAO = "presencial ou híbrido fora da região"


def _trilha(c, cfg):
    for t in cfg["trilhas"]:
        if c.publicacao and not t["aceita_publicacoes"]:
            continue
        termos = list(t["termos"])
        if not c.publicacao:
            termos += t.get("termos_somente_vagas", [])
        if tem_termo(c.texto, termos):
            return t
    return None


def _nivel(c, cfg):
    """Nível da vaga. Devolve (nível, motivo_de_descarte).

    Em vagas, o nível é lido no título. Em publicações, "estágio" ou "júnior"
    valem em qualquer parte do texto, mas os termos de nível alto continuam
    sendo lidos só no título (o corpo de um post cita "sênior" por vários motivos).
    """
    if c.nivel_hint == "excluido":
        return None, NIVEL_ALTO
    n = cfg["niveis"]
    onde = c.texto if c.publicacao else c.titulo
    if c.nivel_hint == "estagio" or tem_termo(onde, n["estagio"]):
        nivel = "Estágio"
    elif tem_termo(onde, n["junior"]):
        nivel = "Júnior"               # "Júnior/Pleno" conta como júnior
    elif c.nivel_hint == "trainee" or tem_termo(onde, n["trainee"]):
        nivel = "Trainee"
    else:
        nivel = None
    if nivel:
        if IDS_NIVEL[nivel] in n["aceitos"]:
            return nivel, None
        return None, NIVEL_NAO_ACEITO
    if tem_termo(c.titulo, n["excluidos"]):
        return None, NIVEL_ALTO
    if c.exterior:
        # no exterior, vaga sem nível no título costuma ser pleno ou sênior
        return None, NIVEL_NAO_INFORMADO
    if cfg["perfil"]["aceitar_nivel_nao_informado"]:
        return "Não informado", None
    return None, NIVEL_NAO_INFORMADO


def _modalidade(c, cfg):
    """Modalidade e região. Devolve (modalidade, motivo_de_descarte)."""
    perfil = cfg["perfil"]
    if c.exterior:
        if not tem_termo(c.regiao_exterior, perfil["regioes_exterior_aceitas"]):
            return None, REGIAO_EXTERIOR
        return "Remoto (exterior)", None
    texto = " ".join([c.texto, c.local, c.resumo])
    if c.modalidade_hint == "remoto" or tem_termo(texto, cfg["termos_remoto"]):
        return "Remoto", None
    cidade = (c.local or "").split(",")[0]          # "Macaé, Rio de Janeiro" -> "Macaé"
    if tem_termo(f"{cidade} {c.texto}", perfil["cidades_presencial"]):
        hibrido = c.modalidade_hint == "hibrido" or tem_termo(texto, cfg["termos_hibrido"])
        return ("Híbrido (RJ)" if hibrido else "Presencial (RJ)"), None
    if normalizar(c.local) not in LOCAIS_GENERICOS:
        return None, FORA_DA_REGIAO
    return "A confirmar", None


def classificar(c, cfg):
    """Devolve (Vaga, None) quando aceita ou (None, motivo) quando descartada."""
    link = (c.link or "").strip()
    if not (c.titulo or "").strip() or not link.lower().startswith(("https://", "http://")):
        return None, SEM_DADOS
    if c.idade is None and not c.aceitar_sem_data:
        return None, SEM_DATA
    if c.idade is not None and c.idade > c.idade_max:
        return None, ANTIGA
    if tem_termo(c.texto, cfg["termos_excluir"]):
        return None, EXCLUIDA

    trilha = _trilha(c, cfg)
    if trilha is None:
        return None, FORA_DE_TI

    if c.publicacao:
        if tem_termo(c.texto, cfg["termos_candidato"]):
            return None, CANDIDATO
        if not tem_termo(c.texto, cfg["termos_sinal_vaga"]):
            return None, NAO_ANUNCIO

    nivel, motivo = _nivel(c, cfg)
    if motivo:
        return None, motivo

    modalidade, motivo = _modalidade(c, cfg)
    if motivo:
        return None, motivo

    texto_completo = f"{c.texto} {c.resumo}"
    alertas = []
    if tem_termo(texto_completo, cfg["termos_alerta"]):
        alertas.append("menciona pagamento: confira antes de se candidatar")

    pontos_modalidade = PONTOS_MODALIDADE[modalidade]
    if modalidade in ("Híbrido (RJ)", "Presencial (RJ)") and \
            tem_termo(f"{c.local} {texto_completo}", cfg["perfil"]["locais_prioritarios"]):
        modalidade = modalidade.replace("(RJ)", "(Centro do Rio)")
        pontos_modalidade += cfg["perfil"]["bonus_local_prioritario"]

    if tem_termo(f"{c.fonte} {urlparse(link).hostname or ''}", cfg["perfil"]["sites_prioritarios"]):
        pontos_modalidade += cfg["perfil"]["bonus_site_prioritario"]

    curriculo = trilha["curriculo"] + (" (versão em inglês)" if c.exterior else "")
    recencia = 3 if c.idade is not None and c.idade <= 2 else 0
    pontuacao = trilha["peso"] + PONTOS_NIVEL[nivel] + pontos_modalidade + recencia

    vaga = Vaga(
        titulo=c.titulo.strip(),
        empresa=(c.empresa or "").strip(),
        link=c.link.strip(),
        fonte=c.fonte,
        local=(c.local or "").strip(),
        publicada=c.publicada,
        resumo=c.resumo,
        publicacao=c.publicacao,
        trilha=trilha["id"],
        trilha_nome=trilha["nome"],
        curriculo=curriculo,
        nivel=nivel,
        modalidade=modalidade,
        alertas=alertas,
        termos_stack=termos_encontrados(texto_completo, cfg["termos_stack"]),
        pontuacao=pontuacao,
        chave_por_link=c.chave_por_link,
    )
    return vaga, None
