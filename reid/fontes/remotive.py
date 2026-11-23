"""Remotive: vagas remotas internacionais (API pública e gratuita, sem chave).

A API devolve o feed completo e ignora filtros, então o REID faz uma única
requisição por execução e filtra tudo na classificação. A Remotive pede que a
origem seja citada: cada vaga aparece no e-mail com a fonte "Remotive" e o link
para a página da própria Remotive.
"""

from datetime import datetime, timezone

from ..modelo import Candidato
from ..rede import ErroRede, get_json
from ..texto import BRASILIA, iso_para_datetime, resumir

ENDERECO = "https://remotive.com/api/remote-jobs"


def buscar(cfg_fonte, agora=None):
    agora = agora or datetime.now(timezone.utc)
    dados = get_json(ENDERECO, timeout=60)
    jobs = dados.get("jobs") if isinstance(dados, dict) else None
    if not isinstance(jobs, list):
        raise ErroRede("resposta da Remotive sem a lista 'jobs'")
    candidatos = []
    for j in jobs:
        if not isinstance(j, dict):
            continue
        titulo = str(j.get("title") or "").strip()
        publicada_em = iso_para_datetime(j.get("publication_date"))
        idade = max(0, (agora - publicada_em).days) if publicada_em else None
        tags = " ".join(str(t) for t in (j.get("tags") or []) if isinstance(t, str))
        tipo = str(j.get("job_type") or "").lower()
        candidatos.append(Candidato(
            titulo=titulo,
            empresa=str(j.get("company_name") or "").strip(),
            link=str(j.get("url") or "").strip(),
            fonte="Remotive",
            texto=f"{titulo} {j.get('category') or ''} {tags}",
            local=str(j.get("candidate_required_location") or "").strip(),
            publicada=publicada_em.astimezone(BRASILIA).strftime("%d/%m/%Y") if publicada_em else "",
            resumo=resumir(f"{j.get('category') or ''} · {tags}".strip(" ·"), 160),
            idade=idade,
            idade_max=cfg_fonte["dias_maximos"],
            aceitar_sem_data=False,
            nivel_hint="estagio" if tipo == "internship" else "",
            exterior=True,
            regiao_exterior=str(j.get("candidate_required_location") or ""),
        ))
    return candidatos, []
