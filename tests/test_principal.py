"""Testes de ponta a ponta: execução completa com fontes e envio simulados."""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import apoio
from apoio import candidato
from reid import principal
from reid.rede import ErroRede

AGORA = datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc)      # 13h em Brasília
PRODUCAO = {"EMAIL_REMETENTE": "eu@gmail.com", "EMAIL_SENHA_APP": "abcd efgh ijkl mnop", "SERPAPI_KEY": "k"}


def vagas_gupy():
    return [candidato(titulo="Estágio em Análise de Dados", empresa="Acme", link="https://acme.gupy.io/jobs/1",
                      modalidade_hint="remoto"),
            candidato(titulo="Analista de Suporte N1", empresa="Beta", link="https://beta.gupy.io/jobs/2",
                      local="Rio de Janeiro, Rio de Janeiro"),
            candidato(titulo="Desenvolvedor Sênior", empresa="Gama", link="https://gama.gupy.io/jobs/3")]


def vagas_linkedin():
    return [candidato(titulo="Estágio em Análise de Dados", empresa="Acme", link="https://br.linkedin.com/jobs/view/1",
                      fonte="LinkedIn")], []


class Execucao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.pasta.name)
        shutil.copy(apoio.RAIZ / "config.json", self.raiz / "config.json")
        self.patches = {
            "gupy": mock.patch("reid.fontes.gupy.buscar", return_value=(vagas_gupy(), [])),
            "remotive": mock.patch("reid.fontes.remotive.buscar", return_value=([], [])),
            "saldo": mock.patch("reid.fontes.serpapi.saldo", return_value=200),
            "linkedin": mock.patch("reid.fontes.linkedin.buscar", side_effect=lambda *a, **k: vagas_linkedin()),
            "google": mock.patch("reid.fontes.google_vagas.buscar", return_value=[]),
            "sites": mock.patch("reid.fontes.sites.buscar", return_value=([], [])),
            "enviar": mock.patch("reid.envio.enviar"),
        }
        self.mocks = {nome: p.start() for nome, p in self.patches.items()}

    def tearDown(self):
        mock.patch.stopall()
        self.pasta.cleanup()

    def rodar(self, argv=(), env=None):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            codigo = principal.main(list(argv), env=PRODUCAO if env is None else env, raiz=self.raiz, agora=AGORA)
        return codigo, saida.getvalue()

    def arquivo(self, nome):
        caminho = self.raiz / nome
        return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None


class TestProducao(Execucao):
    def test_envia_uma_vez_e_salva(self):
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 0, saida)
        self.assertEqual(self.mocks["enviar"].call_count, 1)
        mensagem = self.mocks["enviar"].call_args.args[0]
        self.assertEqual(mensagem["Subject"], "REID · 2 vagas novas · Dados 1 · Suporte 1 · 03/11 13h")
        anexos = [p.get_filename() for p in mensagem.walk() if p.get_filename()]
        self.assertEqual(anexos, ["reid_vagas_2026-11-03_13h.csv"])
        vistas = self.arquivo("vagas_vistas.json")
        self.assertEqual(set(vistas), {"estagio em analise de dados|acme", "analista de suporte n1|beta"})
        self.assertEqual(self.arquivo("estatisticas.json")["2026-11"]["vagas"], 2)

    def test_segunda_execucao_nao_repete(self):
        self.rodar()
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 0)
        self.assertEqual(self.mocks["enviar"].call_count, 1)
        self.assertIn("Nenhuma vaga nova", saida)

    def test_repetida_entre_fontes_vem_uma_vez(self):
        codigo, saida = self.rodar()
        # a mesma vaga chega pela Gupy e por cada busca do LinkedIn: entra uma única vez.
        # O número de buscas depende do config.json (recrutadores), então é lido do mock.
        n = self.mocks["linkedin"].call_count
        self.assertGreater(n, 0)
        self.assertIn(f"Aceitas: {2 + n} · já enviadas ou repetidas: {n} · novas: 2", saida)

    def test_falha_no_envio_nao_salva_historico(self):
        self.mocks["enviar"].side_effect = OSError("SMTP fora do ar")
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 1)
        self.assertIsNone(self.arquivo("vagas_vistas.json"))
        self.assertIn("ERRO ao enviar", saida)

    def test_uma_fonte_com_falha_nao_derruba_as_outras(self):
        self.mocks["gupy"].side_effect = ErroRede("HTTP 500")
        codigo, saida = self.rodar(env={**PRODUCAO, "GITHUB_ACTIONS": "true"})
        self.assertEqual(codigo, 0, saida)
        self.assertIn("::warning title=REID::Gupy: HTTP 500", saida)
        mensagem = self.mocks["enviar"].call_args.args[0]
        self.assertIn("Fonte com falha", mensagem.get_payload()[0].get_payload()[1].get_payload(decode=True).decode())

    def test_todas_as_fontes_falhando(self):
        for nome in ("gupy", "remotive", "linkedin", "google", "sites"):
            self.mocks[nome].side_effect = ErroRede("fora do ar")
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 1)
        self.mocks["enviar"].assert_not_called()
        self.assertIsNone(self.arquivo("vagas_vistas.json"))

    def test_sem_chave_da_serpapi_segue_com_fontes_gratuitas(self):
        env = {k: v for k, v in PRODUCAO.items() if k != "SERPAPI_KEY"}
        codigo, saida = self.rodar(env=env)
        self.assertEqual(codigo, 0)
        self.mocks["linkedin"].assert_not_called()
        self.assertIn("SERPAPI_KEY não definida", saida)

    def test_cota_e_respeitada(self):
        self.mocks["saldo"].return_value = 0
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 0)
        self.mocks["linkedin"].assert_not_called()
        self.mocks["google"].assert_not_called()
        self.mocks["sites"].assert_not_called()

    def test_vaga_de_site_prioritario(self):
        self.mocks["saldo"].return_value = 10000          # cota folgada: todas as buscas rodam
        self.mocks["sites"].return_value = ([candidato(
            titulo="Estágio em Ciência de Dados", empresa="", fonte="Catho", chave_por_link=True,
            link="https://www.catho.com.br/vagas/estagio-ciencia-de-dados/1/", modalidade_hint="remoto")], [])
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 0, saida)
        self.assertEqual(self.mocks["sites"].call_count, len(apoio.cfg()["fontes"]["sites"]["lista"]))
        vistas = self.arquivo("vagas_vistas.json")
        self.assertIn("https://www.catho.com.br/vagas/estagio-ciencia-de-dados/1/", vistas)

    def test_saldo_indisponivel_usa_padrao(self):
        self.mocks["saldo"].side_effect = ErroRede("HTTP 503")
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 0)
        chamadas = sum(self.mocks[n].call_count for n in ("linkedin", "google", "sites"))
        self.assertEqual(chamadas, apoio.cfg()["serpapi"]["buscas_por_execucao_padrao"])


class TestModos(Execucao):
    def test_sem_credenciais_e_modo_teste(self):
        codigo, saida = self.rodar(env={})
        self.assertEqual(codigo, 0)
        self.mocks["enviar"].assert_not_called()
        self.assertIsNone(self.arquivo("vagas_vistas.json"))
        self.assertIn("Modo teste", saida)

    def test_opcao_teste_com_credenciais(self):
        codigo, _ = self.rodar(["--teste"])
        self.assertEqual(codigo, 0)
        self.mocks["enviar"].assert_not_called()

    def test_credenciais_incompletas(self):
        codigo, saida = self.rodar(env={"EMAIL_REMETENTE": "eu@gmail.com"})
        self.assertEqual(codigo, 2)
        self.assertIn("credenciais incompletas", saida)

    def test_validar(self):
        codigo, saida = self.rodar(["--validar"])
        self.assertEqual(codigo, 0)
        self.mocks["gupy"].assert_not_called()

    def test_config_invalido(self):
        (self.raiz / "config.json").write_text("{}", encoding="utf-8")
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 2)
        self.assertIn("config.json inválido", saida)

    def test_historico_corrompido(self):
        (self.raiz / "vagas_vistas.json").write_text("{quebrado", encoding="utf-8")
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 1)
        self.mocks["enviar"].assert_not_called()
        self.assertEqual((self.raiz / "vagas_vistas.json").read_text(encoding="utf-8"), "{quebrado")

    def test_previa_em_html(self):
        previa = self.raiz / "previa.html"
        codigo, _ = self.rodar(["--teste", "--previa", str(previa)])
        self.assertEqual(codigo, 0)
        self.assertIn("Estágio em Análise de Dados", previa.read_text(encoding="utf-8"))

    def test_historico_antigo_e_respeitado(self):
        (self.raiz / "vagas_vistas.json").write_text(
            json.dumps({"estagio em analise de dados|acme": "2026-10-30"}), encoding="utf-8")
        codigo, _ = self.rodar()
        mensagem = self.mocks["enviar"].call_args.args[0]
        self.assertEqual(mensagem["Subject"], "REID · 1 vaga nova · Suporte 1 · 03/11 13h")


if __name__ == "__main__":
    unittest.main()
