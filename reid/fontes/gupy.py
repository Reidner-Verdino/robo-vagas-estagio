"""Gupy: API pública do portal de vagas (gratuita, sem chave)."""

from datetime import datetime, timezone

from ..modelo import Candidato
from ..rede import ErroRede, get_json
from ..texto import BRASILIA, iso_para_datetime

ENDERECOS = [
    "https://portal.gupy.io/api/job-search/jobs",   # endereço atual (desde out/2026)
    "https://portal.api.gupy.io/api/job",           # antigo, mantido como reserva
]
POR_PAGINA = 100
MODALIDADES = {"remote": "remoto", "hybrid": "hibrido", "on-site": "presencial", "onsite": "presencial"}


def _pagina(termo, offset):
    """Tenta cada endereço em ordem; devolve a lista de vagas da página."""
    erros = []
    for endereco in ENDERECOS:
        try:
            dados = get_json(endereco, params={"jobName": termo, "limit": POR_PAGINA, "offset": offset})
        except ErroRede as e:
            erros.append(str(e))
            continue
        lista = dados.get("data") if isinstance(dados, dict) else None
        if not isinstance(lista, list):
            erros.append("resposta sem a lista 'data'")
            continue
        return lista
    raise ErroRede("; ".join(erros))


def _nivel_pelo_tipo(tipo):
    tipo = (tipo or "").lower()
    if "intern" in tipo:
        return "estagio"
    if "trainee" in tipo:
        return "trainee"
    if "apprentice" in tipo or "aprendiz" in tipo:
        return "excluido"
    return ""


def _candidato(j, cfg_fonte, agora):
    titulo = str(j.get("name") or "").strip()
    publicada_em = iso_para_datetime(j.get("publishedDate"))
    idade = None
    publicada = ""
    if publicada_em is not None:
        idade = max(0, (agora - publicada_em).days)
        publicada = publicada_em.astimezone(BRASILIA).strftime("%d/%m/%Y")
    modalidade = MODALIDADES.get(str(j.get("workplaceType") or "").lower(), "")
    if j.get("isRemoteWork") is True:
        modalidade = "remoto"
    local = ", ".join(str(x) for x in (j.get("city"), j.get("state")) if x)
    return Candidato(
        titulo=titulo,
        empresa=str(j.get("careerPageName") or "").strip(),
        link=str(j.get("jobUrl") or "").strip(),
        fonte="Gupy",
        texto=titulo,
        local=local,
        publicada=publicada,
        idade=idade,
        idade_max=cfg_fonte["dias_maximos"],
        aceitar_sem_data=False,
        modalidade_hint=modalidade,
        nivel_hint=_nivel_pelo_tipo(j.get("type")),
    )


def buscar(cfg_fonte, agora=None):
    agora = agora or datetime.now(timezone.utc)
    candidatos, falhas, vistos, respondeu = [], [], set(), False
    for termo in cfg_fonte["termos"]:
        for pagina in range(cfg_fonte["paginas_por_termo"]):
            try:
                lista = _pagina(termo, pagina * POR_PAGINA)
            except ErroRede as e:
                falhas.append(f"Gupy '{termo}': {e}")
                break
            respondeu = True
            for j in lista:
                if not isinstance(j, dict):
                    continue
                identificador = j.get("id") or j.get("jobUrl")
                if identificador in vistos:
                    continue
                vistos.add(identificador)
                candidatos.append(_candidato(j, cfg_fonte, agora))
            if len(lista) < POR_PAGINA:
                break
    if not respondeu:
        raise ErroRede("todas as consultas falharam: " + falhas[0])
    return candidatos, falhas
