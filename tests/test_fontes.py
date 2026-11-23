"""Testes das fontes com respostas simuladas: nenhum teste acessa a internet."""

import unittest
from datetime import date, datetime, timezone
from unittest import mock

import requests

import apoio
from apoio import RespostaFalsa
from reid import rede
from reid.fontes import google_vagas, gupy, linkedin, remotive, serpapi, sites
from reid.rede import ErroRede

AGORA = datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc)
HOJE = date(2026, 11, 3)


def respostas(*itens):
    """Patch de requests.get que devolve as respostas na ordem (exceções são levantadas)."""
    fila = list(itens)

    def falso(*args, **kwargs):
        item = fila.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    return mock.patch.object(rede.requests, "get", side_effect=falso)


class TestRede(unittest.TestCase):
    def test_repete_falha_temporaria(self):
        with respostas(RespostaFalsa(503, {"error": "ocupado"}), RespostaFalsa(200, {"ok": 1})) as g:
            self.assertEqual(rede.get_json("https://x"), {"ok": 1})
        self.assertEqual(g.call_count, 2)

    def test_repete_tempo_esgotado_e_desiste(self):
        with respostas(requests.Timeout(), requests.Timeout(), requests.ConnectionError()) as g:
            with self.assertRaises(ErroRede):
                rede.get_json("https://x")
        self.assertEqual(g.call_count, rede.TENTATIVAS)

    def test_erro_definitivo_nao_repete(self):
        with respostas(RespostaFalsa(401, {"error": "Invalid API key"})) as g:
            with self.assertRaises(ErroRede) as ctx:
                rede.get_json("https://x")
        self.assertEqual(g.call_count, 1)
        self.assertIn("Invalid API key", str(ctx.exception))
        self.assertEqual(ctx.exception.status, 401)

    def test_resposta_que_nao_e_json(self):
        with respostas(RespostaFalsa(200, json_invalido=True)):
            with self.assertRaises(ErroRede):
                rede.get_json("https://x")


def vaga_gupy(i, **campos):
    base = {"id": i, "name": "Estágio em Dados", "careerPageName": "Acme", "city": "Rio de Janeiro",
            "state": "Rio de Janeiro", "workplaceType": "hybrid", "isRemoteWork": False,
            "publishedDate": "2026-11-01T10:00:00.000Z", "jobUrl": f"https://acme.gupy.io/jobs/{i}",
            "type": "vacancy_type_internship"}
    base.update(campos)
    return base


class TestGupy(unittest.TestCase):
    def cfg(self, termos=("estagio dados",)):
        c = apoio.cfg()["fontes"]["gupy"]
        c["termos"] = list(termos)
        return c

    def test_converte_campos(self):
        with respostas(RespostaFalsa(200, {"data": [vaga_gupy(1)]})):
            candidatos, falhas = gupy.buscar(self.cfg(), AGORA)
        c = candidatos[0]
        self.assertEqual((c.titulo, c.empresa, c.fonte, c.local), ("Estágio em Dados", "Acme", "Gupy",
                                                                   "Rio de Janeiro, Rio de Janeiro"))
        self.assertEqual((c.idade, c.publicada, c.modalidade_hint, c.nivel_hint), (2, "01/11/2026", "hibrido", "estagio"))
        self.assertFalse(c.aceitar_sem_data)
        self.assertEqual(falhas, [])

    def test_usa_endereco_reserva(self):
        with respostas(RespostaFalsa(404, reason="Not Found"), RespostaFalsa(200, {"data": [vaga_gupy(1)]})) as g:
            candidatos, _ = gupy.buscar(self.cfg(), AGORA)
        self.assertEqual(len(candidatos), 1)
        self.assertIn("portal.api.gupy.io", g.call_args_list[1].args[0])

    def test_paginacao_e_duplicatas_entre_termos(self):
        pagina_cheia = {"data": [vaga_gupy(i) for i in range(100)]}
        with respostas(RespostaFalsa(200, pagina_cheia), RespostaFalsa(200, {"data": [vaga_gupy(100)]}),
                       RespostaFalsa(200, {"data": [vaga_gupy(5), vaga_gupy(200)]})) as g:
            candidatos, _ = gupy.buscar(self.cfg(("estagio dados", "estagio ti")), AGORA)
        self.assertEqual(len(candidatos), 102)
        self.assertEqual(g.call_count, 3)

    def test_remoto_e_aprendiz(self):
        with respostas(RespostaFalsa(200, {"data": [vaga_gupy(1, isRemoteWork=True, type="vacancy_type_apprentice")]})):
            c = gupy.buscar(self.cfg(), AGORA)[0][0]
        self.assertEqual((c.modalidade_hint, c.nivel_hint), ("remoto", "excluido"))

    def test_falha_parcial_e_total(self):
        falha = RespostaFalsa(500, reason="erro")
        with respostas(*([falha] * 6), RespostaFalsa(200, {"data": [vaga_gupy(1)]})):
            candidatos, falhas = gupy.buscar(self.cfg(("estagio dados", "estagio ti")), AGORA)
        self.assertEqual((len(candidatos), len(falhas)), (1, 1))
        with respostas(*([falha] * 6)):
            with self.assertRaises(ErroRede):
                gupy.buscar(self.cfg(), AGORA)

    def test_resposta_sem_data(self):
        with respostas(RespostaFalsa(200, {"mensagem": "x"}), RespostaFalsa(200, {"mensagem": "x"})):
            with self.assertRaises(ErroRede):
                gupy.buscar(self.cfg(), AGORA)


class TestSerpApi(unittest.TestCase):
    def test_sem_resultados_nao_e_falha(self):
        with respostas(RespostaFalsa(200, {"error": "DuckDuckGo hasn't returned any results for this query."})):
            self.assertEqual(serpapi.buscar({"q": "x"}, "k"), {})

    def test_outro_erro_e_falha(self):
        with respostas(RespostaFalsa(200, {"error": "Your account has run out of searches."})):
            with self.assertRaises(ErroRede):
                serpapi.buscar({"q": "x"}, "k")

    def test_saldo(self):
        with respostas(RespostaFalsa(200, {"total_searches_left": 120})):
            self.assertEqual(serpapi.saldo("k"), 120)
        with respostas(RespostaFalsa(200, {"plan_searches_left": 7})):
            self.assertEqual(serpapi.saldo("k"), 7)
        with respostas(RespostaFalsa(200, {"account_id": "x"})):
            with self.assertRaises(ErroRede):
                serpapi.saldo("k")
        with respostas(RespostaFalsa(401, {"error": "Invalid API key"})):
            with self.assertRaises(ErroRede):
                serpapi.saldo("k")


class TestGoogleVagas(unittest.TestCase):
    def test_data_nas_etiquetas(self):
        j = {"detected_extensions": {}, "extensions": ["Tempo integral", "6 horas por dia", "há 2 dias"]}
        self.assertEqual(google_vagas.data_da_vaga(j, HOJE), ("há 2 dias", 2))
        self.assertEqual(google_vagas.data_da_vaga({"extensions": ["Tempo integral", "R$ 1.500 por mês"]}, HOJE),
                         ("", None))

    def test_converte_campos(self):
        dados = {"jobs_results": [{
            "title": "Estágio em Dados", "company_name": "Acme", "location": "Rio de Janeiro, RJ",
            "via": "via LinkedIn", "detected_extensions": {"posted_at": "há 1 dia", "work_from_home": True},
            "apply_options": [{"title": "LinkedIn", "link": "https://linkedin.com/jobs/view/1"}]},
            {"title": "Estágio TI", "company_name": "Beta", "share_link": "https://google.com/x"}]}
        with respostas(RespostaFalsa(200, dados)):
            a, b = google_vagas.buscar("estágio dados", apoio.cfg()["fontes"]["google_vagas"], "k", HOJE)
        self.assertEqual((a.fonte, a.idade, a.modalidade_hint, a.link), ("LinkedIn", 1, "remoto",
                                                                       "https://linkedin.com/jobs/view/1"))
        self.assertEqual((b.fonte, b.link, b.idade, b.publicada), ("Google Vagas", "https://google.com/x", None,
                                                                 "data não informada"))


class TestLinkedIn(unittest.TestCase):
    def cfg(self):
        return apoio.cfg()["fontes"]["linkedin"]

    def test_titulos_de_vagas(self):
        casos = {
            "Data Engineer na empresa EY – São Paulo, SP | LinkedIn Jobs": ("Data Engineer", "EY", "São Paulo, SP"),
            "AI Engineer Senior na empresa Hotmart - LinkedIn Jobs": ("AI Engineer Senior", "Hotmart", ""),
            "Acme contratando Desenvolvedor Python Júnior em São Paulo, SP | LinkedIn":
                ("Desenvolvedor Python Júnior", "Acme", "São Paulo, SP"),
            "Acme hiring Data Engineer in Rio de Janeiro, RJ | LinkedIn": ("Data Engineer", "Acme", "Rio de Janeiro, RJ"),
            "Estágio de Marketing | Euro Infoprodutos": ("Estágio de Marketing", "Euro Infoprodutos", ""),
        }
        for titulo, esperado in casos.items():
            self.assertEqual(linkedin.interpretar_vaga(titulo), esperado, titulo)

    def test_titulos_de_publicacoes(self):
        self.assertEqual(linkedin.interpretar_publicacao("Maria Souza no LinkedIn: Vaga aberta para Dev Java | LinkedIn"),
                         ("Maria Souza", "Vaga aberta para Dev Java"))
        self.assertEqual(linkedin.interpretar_publicacao("#vagas Suporte | João Lima posted on the topic | LinkedIn")[0],
                         "João Lima")

    def test_parametros_por_motor(self):
        busca = {"id": "x", "site": "br.linkedin.com/jobs/view", "q": "(estágio OR júnior) (dados OR BI)"}
        p = linkedin.parametros(busca, self.cfg())
        self.assertEqual(p["engine"], "duckduckgo")
        self.assertEqual(p["q"], "site:br.linkedin.com/jobs/view (estágio OR júnior) (dados OR BI)")
        cfg = self.cfg()
        cfg["motor"] = "google"
        p = linkedin.parametros(busca, cfg)
        self.assertEqual((p["engine"], p["as_sitesearch"]), ("google", "br.linkedin.com"))

    def test_busca_de_recrutadores_favoritos(self):
        cfg = self.cfg()
        cfg["recrutadores"] = ["Ana Exemplo", "Bruno Exemplo"]
        ids = {b["id"]: b for b in linkedin.buscas_configuradas(cfg)}
        self.assertIn('"Ana Exemplo" OR "Bruno Exemplo"', ids["recrutadores_favoritos"]["q"])
        cfg["recrutadores"] = []
        self.assertNotIn("recrutadores_favoritos", {b["id"] for b in linkedin.buscas_configuradas(cfg)})

    def test_separa_vagas_publicacoes_e_outros_sites(self):
        dados = {"organic_results": [
            {"title": "Data Engineer na empresa EY – Rio de Janeiro, RJ | LinkedIn Jobs",
             "link": "https://br.linkedin.com/jobs/view/data-engineer-123", "snippet": "Vaga", "date": "Oct 29, 2026"},
            {"title": "Ana Reis no LinkedIn: Estamos contratando Analista de Dados! | LinkedIn",
             "link": "https://www.linkedin.com/posts/ana-reis_vaga-activity-1", "snippet": "Remoto"},
            {"title": "27 vagas de Desenvolvedor | Glassdoor", "link": "https://www.glassdoor.com.br/Vaga/x.htm"},
            {"title": "Gean - Aluno | LinkedIn", "link": "https://www.linkedin.com/in/gean"},
            {"title": "Falso", "link": "https://linkedin.com.golpe.com/jobs/view/1"},
        ]}
        busca = {"id": "x", "site": "linkedin.com", "q": "q"}
        with respostas(RespostaFalsa(200, dados)):
            candidatos, descartes = linkedin.buscar(busca, self.cfg(), "k", HOJE)
        vaga, post = candidatos
        self.assertEqual((vaga.titulo, vaga.empresa, vaga.local, vaga.idade, vaga.publicada),
                         ("Data Engineer", "EY", "Rio de Janeiro, RJ", 5, "29/10/2026"))
        self.assertTrue(post.publicacao)
        self.assertEqual(post.empresa, "Ana Reis")
        self.assertEqual([m for m, _, _ in descartes],
                         ["não é do LinkedIn", "endereço não é vaga nem publicação", "não é do LinkedIn"])


class TestSites(unittest.TestCase):
    def cfg(self):
        return apoio.cfg()["fontes"]["sites"]

    def site(self, nome="Catho", dominio="catho.com.br"):
        return {"id": "x", "nome": nome, "dominio": dominio, "q": "(estágio OR júnior)"}

    def test_dominio(self):
        self.assertTrue(sites.dominio_confere("https://www.catho.com.br/vagas/1", "catho.com.br"))
        self.assertTrue(sites.dominio_confere("https://acme.vagas.solides.com.br/vaga/9", "vagas.solides.com.br"))
        self.assertFalse(sites.dominio_confere("https://catho.com.br.golpe.com/vagas/1", "catho.com.br"))
        self.assertFalse(sites.dominio_confere("https://vagas.solides.com.br.x/1", "vagas.solides.com.br"))
        self.assertFalse(sites.dominio_confere("javascript:alert(1)", "catho.com.br"))

    def test_titulo_e_local(self):
        self.assertEqual(sites.limpar_titulo("Vaga de Estágio em TI - Rio de Janeiro, RJ | Catho", "Catho"),
                         "Estágio em TI")
        self.assertEqual(sites.limpar_titulo("Analista de Dados Júnior | InfoJobs", "InfoJobs"), "Analista de Dados Júnior")
        self.assertEqual(sites.extrair_local("Estágio em TI em Duque de Caxias/RJ"), "Duque de Caxias, RJ")
        self.assertEqual(sites.extrair_local("Estágio em TI - RJ"), "")
        self.assertEqual(sites.extrair_local("Python, SQL e Java, AB"), "")

    def test_busca_separa_vagas_listagens_e_outros_sites(self):
        dados = {"organic_results": [
            {"title": "Vaga de Estágio em Dados - São Paulo, SP | Catho", "link": "https://www.catho.com.br/vagas/x/1/",
             "snippet": "Estágio híbrido", "date": "há 2 dias"},
            {"title": "120 vagas de Estágio em TI | Catho", "link": "https://www.catho.com.br/vagas/estagio-ti/"},
            {"title": "Estágio em TI | Outro site", "link": "https://outro.com.br/vaga/1"},
        ]}
        with respostas(RespostaFalsa(200, dados)) as g:
            candidatos, descartes = sites.buscar(self.site(), self.cfg(), "k", HOJE)
        params = g.call_args.kwargs["params"]
        self.assertEqual((params["engine"], params["q"]), ("duckduckgo", "site:catho.com.br (estágio OR júnior)"))
        (c,) = candidatos
        self.assertEqual((c.titulo, c.fonte, c.local, c.idade, c.chave_por_link),
                         ("Estágio em Dados", "Catho", "São Paulo, SP", 2, True))
        self.assertEqual([m for m, _, _ in descartes], ["página de listagem, não de vaga", "não é do Catho"])


class TestRemotive(unittest.TestCase):
    def test_converte_campos(self):
        dados = {"jobs": [{"id": 1, "url": "https://remotive.com/remote-jobs/data/junior-1", "title": "Junior Data Analyst",
                           "company_name": "Acme", "category": "Data", "tags": ["python", "sql"],
                           "job_type": "internship", "publication_date": "2026-11-01T12:00:00",
                           "candidate_required_location": "LATAM"}]}
        with respostas(RespostaFalsa(200, dados)):
            candidatos, falhas = remotive.buscar(apoio.cfg()["fontes"]["remotive"], AGORA)
        c = candidatos[0]
        self.assertEqual((c.fonte, c.exterior, c.regiao_exterior, c.idade, c.nivel_hint),
                         ("Remotive", True, "LATAM", 2, "estagio"))
        self.assertIn("python", c.texto)

    def test_resposta_invalida(self):
        with respostas(RespostaFalsa(200, {"0-legal-notice": "x"})):
            with self.assertRaises(ErroRede):
                remotive.buscar(apoio.cfg()["fontes"]["remotive"], AGORA)


if __name__ == "__main__":
    unittest.main()
