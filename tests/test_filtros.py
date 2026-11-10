"""Testes das regras de filtragem, interpretação do LinkedIn, datas e controle de cota.

Rodar com:  python -m unittest discover tests
"""
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vagas_bot as bot  # noqa: E402


class TestEstagiosGupyEGoogle(unittest.TestCase):
    def test_aceita_estagios_de_tecnologia(self):
        for titulo in ["Estágio em Engenharia de Dados", "Estagiário de TI",
                       "Data Engineering Intern", "Estagiária Desenvolvimento Front-end"]:
            self.assertTrue(bot.e_vaga_desejada(titulo), titulo)
        self.assertTrue(bot.e_vaga_desejada("Estágio de Suporte - Tech Travel"))

    def test_rejeita_outras_areas_e_niveis(self):
        for titulo in ["Estágio Administrativo", "Analista de Dados Pleno",
                       "Estágio em Vendas - Tecnologia", "Estágio Direito"]:
            self.assertFalse(bot.e_vaga_desejada(titulo), titulo)

    def test_tipo_estagio_informado_pela_fonte(self):
        self.assertTrue(bot.e_vaga_desejada("Desenvolvedor Python", ja_e_estagio=True))


class TestFiltroTIAmplo(unittest.TestCase):
    def test_aceita_qualquer_area_e_nivel_de_ti(self):
        for titulo in ["Desenvolvedor .NET Sênior", "Analista de Suporte N2", "Engenheiro de Dados Pleno",
                       "UX/UI Designer", "Consultor SAP", "Analista de Segurança da Informação",
                       "Desenvolvedor C# Júnior", "Estágio em Dados", "Product Owner", "DBA Oracle"]:
            self.assertTrue(bot.e_ti(titulo), titulo)

    def test_rejeita_fora_de_ti(self):
        for titulo in ["Vendedor Interno", "Assistente Administrativo", "Auxiliar de Limpeza",
                       "Executivo de Vendas de Software", "Analista Financeiro"]:
            self.assertFalse(bot.e_ti(titulo), titulo)


class TestPublicacoes(unittest.TestCase):
    def test_publicacao_de_vaga(self):
        self.assertTrue(bot.e_publicacao_de_vaga("Estamos contratando Dev Python! Envie seu currículo"))
        self.assertTrue(bot.e_publicacao_de_vaga("#vagas Analista de Dados remoto"))

    def test_publicacao_de_estagio_sem_a_palavra_vaga(self):
        texto = "Estágio de Suporte - Tech 100% Remoto #SeLiga: cursando Sistemas de Informação"
        self.assertTrue(bot.e_publicacao_de_vaga(texto))
        self.assertTrue(bot.e_ti(texto))

    def test_busca_de_recrutadores_favoritos(self):
        nomes = ["Ana Exemplo", "Bruno Exemplo"]
        with mock.patch.dict(bot.CONFIG, {"linkedin_recrutadores": nomes}):
            busca = next(b for b in bot.agenda_de_buscas() if b["id"] == "recrutadores_favoritos")
        for nome in nomes:
            self.assertIn(f'"{nome}"', busca["q"])

    def test_sem_recrutadores_nao_cria_busca(self):
        with mock.patch.dict(bot.CONFIG, {"linkedin_recrutadores": []}):
            ids = [b["id"] for b in bot.agenda_de_buscas()]
        self.assertNotIn("recrutadores_favoritos", ids)

    def test_ignora_quem_procura_emprego(self):
        self.assertFalse(bot.e_publicacao_de_vaga("Estou em busca de uma vaga como dev #opentowork"))

    def test_interpreta_titulo_de_publicacao(self):
        autor, texto = bot.interpretar_publicacao_linkedin(
            "Maria Souza no LinkedIn: Vaga aberta para Desenvolvedor Java | LinkedIn")
        self.assertEqual((autor, texto), ("Maria Souza", "Vaga aberta para Desenvolvedor Java"))
        autor, _ = bot.interpretar_publicacao_linkedin(
            "#vagas #ti Analista de Suporte | João Lima posted on the topic | LinkedIn")
        self.assertEqual(autor, "João Lima")


class TestVagasLinkedIn(unittest.TestCase):
    def test_titulo_em_portugues(self):
        self.assertEqual(
            bot.interpretar_vaga_linkedin("Acme contratando Desenvolvedor Python Júnior em São Paulo, SP | LinkedIn"),
            ("Desenvolvedor Python Júnior", "Acme", "São Paulo, SP"))

    def test_titulo_do_duckduckgo(self):
        self.assertEqual(
            bot.interpretar_vaga_linkedin("Data Engineer na empresa EY – São Paulo, SP | LinkedIn Jobs"),
            ("Data Engineer", "EY", "São Paulo, SP"))
        self.assertEqual(
            bot.interpretar_vaga_linkedin("AI Engineer Senior na empresa Hotmart - LinkedIn Jobs"),
            ("AI Engineer Senior", "Hotmart", ""))

    def test_cargos_de_ia_e_engenharia_em_ingles(self):
        for cargo in ["AI Engineer Senior", "ML Engineer", "Cloud Engineer", "Senior Data Engineer"]:
            self.assertTrue(bot.e_ti(cargo), cargo)
        for cargo in ["Designer Pleno (Mid-level Designer)", "Estágio de Marketing", "Analista de CRM e Growth"]:
            self.assertFalse(bot.e_ti(cargo), cargo)

    def test_formata_datas(self):
        self.assertEqual(bot.formatar_data("Oct 29, 2026"), "29/10/2026")
        self.assertEqual(bot.formatar_data("2026-10-29"), "29/10/2026")
        self.assertEqual(bot.formatar_data("há 2 dias"), "há 2 dias")

    def test_titulo_em_ingles(self):
        self.assertEqual(
            bot.interpretar_vaga_linkedin("Acme hiring Data Engineer in Rio de Janeiro, RJ | LinkedIn"),
            ("Data Engineer", "Acme", "Rio de Janeiro, RJ"))

    def test_consulta_restrita_ao_linkedin(self):
        params = bot.parametros_linkedin({"id": "x", "site": "br.linkedin.com/jobs/view", "q": "dev"}, "k")
        self.assertEqual(params["engine"], "duckduckgo")
        self.assertTrue(params["q"].startswith("site:br.linkedin.com/jobs/view "))
        self.assertIn("df", params)

    def test_descarta_resultados_de_outros_sites(self):
        falsa = mock.Mock()
        falsa.json.return_value = {"organic_results": [
            {"title": "27 vagas de Desenvolvedor | Glassdoor",
             "link": "https://www.glassdoor.com.br/Vaga/desenvolvedor-vagas.htm", "snippet": "dev"}]}
        falsa.raise_for_status.return_value = None
        with mock.patch.object(bot.requests, "get", return_value=falsa):
            self.assertEqual(bot.buscar_linkedin({"id": "t", "q": "x"}, "k"), [])

    def test_classificacao_e_deduplicacao(self):
        resposta = {"organic_results": [
            {"title": "Acme contratando Desenvolvedor Java em Recife, PE | LinkedIn",
             "link": "https://br.linkedin.com/jobs/view/desenvolvedor-java-123", "snippet": "…"},
            {"title": "Beta contratando Assistente Administrativo em Niterói, RJ | LinkedIn",
             "link": "https://br.linkedin.com/jobs/view/assistente-456", "snippet": "…"},
            {"title": "Gama contratando Vendedor em Salvador, BA | LinkedIn",
             "link": "https://br.linkedin.com/jobs/view/vendedor-789", "snippet": "…"},
            {"title": "Ana Reis no LinkedIn: Estamos contratando Analista de Dados! | LinkedIn",
             "link": "https://www.linkedin.com/posts/ana-reis_vaga-activity-1", "snippet": "Remoto, envie seu CV"},
            {"title": "Caio no LinkedIn: #opentowork busco oportunidade como dev | LinkedIn",
             "link": "https://www.linkedin.com/posts/caio_activity-2", "snippet": ""},
        ]}
        falsa = mock.Mock()
        falsa.json.return_value = resposta
        falsa.raise_for_status.return_value = None
        with mock.patch.object(bot.requests, "get", return_value=falsa):
            vagas = bot.buscar_linkedin({"id": "teste", "q": "x"}, "chave")
        categorias = [v["categoria"] for v in vagas]
        self.assertEqual(categorias, ["ti", "publicacao_ti"])
        self.assertEqual(vagas[0]["titulo"], "Desenvolvedor Java")
        self.assertEqual(vagas[1]["empresa"], "Ana Reis")


class TestDatas(unittest.TestCase):
    def test_formatos_em_portugues_e_ingles(self):
        casos = {"há 5 horas": 0, "ontem": 1, "há 3 dias": 3, "há 2 semanas": 14,
                 "há 1 mês": 30, "há 30+ dias": 30, "3 days ago": 3, "Just posted": 0}
        for texto, esperado in casos.items():
            self.assertEqual(bot.idade_em_dias(texto), esperado, texto)

    def test_texto_sem_data(self):
        self.assertIsNone(bot.idade_em_dias(""))

    def test_data_nas_etiquetas_do_google(self):
        vaga = {"detected_extensions": {}, "extensions": ["Tempo integral", "6 horas por dia", "há 2 dias"]}
        self.assertEqual(bot.data_da_vaga_google(vaga), ("há 2 dias", 2))

    def test_etiquetas_sem_data(self):
        vaga = {"extensions": ["Tempo integral", "R$ 1.500 por mês"]}
        self.assertEqual(bot.data_da_vaga_google(vaga), ("", None))


class TestCota(unittest.TestCase):
    def test_proxima_renovacao(self):
        self.assertEqual(bot.proxima_renovacao(date(2026, 10, 20), 15), date(2026, 11, 15))
        self.assertEqual(bot.proxima_renovacao(date(2026, 10, 10), 15), date(2026, 10, 15))
        self.assertEqual(bot.proxima_renovacao(date(2026, 1, 31), 31), date(2026, 2, 28))
        self.assertEqual(bot.proxima_renovacao(date(2026, 12, 20), 15), date(2027, 1, 15))

    def test_divide_a_cota_ate_a_renovacao(self):
        falsa = mock.Mock()
        falsa.json.return_value = {"total_searches_left": 240}
        agora = datetime(2026, 10, 15, 16, tzinfo=timezone.utc)  # 30 dias até 14/11 -> 60 execuções
        with mock.patch.object(bot.requests, "get", return_value=falsa):
            permitidas, restantes = bot.buscas_disponiveis("chave", agora)
        self.assertEqual(restantes, 240)
        self.assertEqual(permitidas, 4)

    def test_prioriza_ti_no_ciclo(self):
        ciclo = bot.ciclo_ponderado(bot.agenda_de_buscas())
        contagem = {}
        for b in ciclo:
            contagem[b["id"]] = contagem.get(b["id"], 0) + 1
        self.assertGreater(contagem["ti_vagas_desenvolvimento"], contagem["google_vagas_1"])
        self.assertGreater(contagem["ti_publicacoes_infra_suporte"], contagem["google_vagas_1"])

    def test_todas_as_buscas_rodam_ao_longo_do_tempo(self):
        vistas = set()
        for janela in range(10):
            agora = datetime.fromtimestamp(janela * 12 * 3600, tz=timezone.utc)
            vistas |= {b["id"] for b in bot.escolher_buscas(4, agora)}
        self.assertEqual(vistas, {b["id"] for b in bot.agenda_de_buscas()})

    def test_respeita_a_quantidade(self):
        agora = datetime(2026, 10, 20, tzinfo=timezone.utc)
        self.assertEqual(len(bot.escolher_buscas(4, agora)), 4)
        self.assertEqual(len(bot.escolher_buscas(50, agora)), len(bot.agenda_de_buscas()))


class TestEmail(unittest.TestCase):
    def test_tema_escuro_e_ordem_das_secoes(self):
        vagas = [
            {"titulo": "Recrutadora anuncia vaga", "empresa": "B", "local": "", "fonte": "Publicação no LinkedIn",
             "publicada": "", "link": "https://b", "categoria": "publicacao_ti", "publicacao": True,
             "resumo": "Vaga remota"},
            {"titulo": "Dev Python", "empresa": "A", "local": "SP", "fonte": "LinkedIn",
             "publicada": "há 1 dia", "link": "https://a", "categoria": "ti"},
        ]
        corpo = bot.montar_html(vagas)
        self.assertIn(bot.COR["fundo"], corpo)
        self.assertIn(bot.COR["laranja"], corpo)
        self.assertLess(corpo.index("Dev Python"), corpo.index("Recrutadora anuncia vaga"))
        self.assertNotIn("dministrativ", corpo)

    def test_assunto(self):
        vagas = [{"categoria": "ti"}, {"categoria": "estagio"}, {"categoria": "publicacao_ti"}]
        self.assertIn("2 vaga(s) de TI", bot.assunto(vagas))
        self.assertIn("1 publicação", bot.assunto(vagas))


if __name__ == "__main__":
    unittest.main()
