import csv
import io
import unittest
from datetime import datetime

import apoio
from reid import relatorio
from reid.modelo import Vaga
from reid.texto import BRASILIA

AGORA_BR = datetime(2026, 11, 3, 13, 0, tzinfo=BRASILIA)


def vaga(titulo, trilha, pontuacao=40, **campos):
    nomes = {t["id"]: t["nome"] for t in apoio.cfg()["trilhas"]}
    base = dict(titulo=titulo, empresa="Acme", link=f"https://exemplo.com/{abs(hash(titulo))}", fonte="Gupy",
                trilha=trilha, trilha_nome=nomes[trilha], curriculo="Dados", nivel="Estágio", modalidade="Remoto",
                pontuacao=pontuacao)
    base.update(campos)
    return Vaga(**base)


class TestSecoes(unittest.TestCase):
    def test_ordem_das_trilhas_e_publicacoes_por_ultimo(self):
        vagas = [vaga("Post", "dados", publicacao=True), vaga("Suporte N1", "suporte"),
                 vaga("Dados B", "dados", 40), vaga("Dados A", "dados", 49)]
        secoes = relatorio.secoes(vagas, apoio.cfg())
        self.assertEqual([s["id"] for s, _ in secoes], ["dados", "suporte", "publicacoes"])
        self.assertEqual([v.titulo for v in secoes[0][1]], ["Dados A", "Dados B"])

    def test_assunto(self):
        vagas = [vaga("A", "dados"), vaga("B", "dados"), vaga("C", "desenvolvimento")]
        self.assertEqual(relatorio.assunto(vagas, apoio.cfg(), AGORA_BR),
                         "REID · 3 vagas novas · Dados 2 · Desenvolvimento 1 · 03/11 13h")
        self.assertEqual(relatorio.assunto([vaga("A", "dados")], apoio.cfg(), AGORA_BR),
                         "REID · 1 vaga nova · Dados 1 · 03/11 13h")
        self.assertIn("nenhuma vaga nova", relatorio.assunto([], apoio.cfg(), AGORA_BR))


class TestHtml(unittest.TestCase):
    def test_paleta_e_conteudo(self):
        html = relatorio.montar_html([vaga("Estágio em Dados", "dados")], apoio.cfg(), AGORA_BR,
                                     {"mais_citados": [("python", 3)], "falhas": ["Gupy: HTTP 500"], "restantes": 99})
        for cor in relatorio.COR.values():
            self.assertIn(cor, html)
        for texto in ["Estágio em Dados", "Currículo: Dados", "Mais citados em novembro: python 3",
                      "Fonte com falha: Gupy: HTTP 500", "Buscas SerpApi restantes: 99", "1 vaga nova"]:
            self.assertIn(texto, html)

    def test_escapa_texto_externo(self):
        html = relatorio.montar_html([vaga("<script>alert(1)</script>", "dados", empresa="A & B")], apoio.cfg(),
                                     AGORA_BR, {})
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("A &amp; B", html)

    def test_limite_por_secao(self):
        cfg = apoio.cfg()
        cfg["email"]["max_por_secao"] = 2
        vagas = [vaga(f"Dados {i}", "dados") for i in range(5)]
        html = relatorio.montar_html(vagas, cfg, AGORA_BR, {})
        self.assertIn("+ 3 nesta trilha na planilha anexa", html)
        self.assertEqual(html.count("Abrir vaga"), 2)

    def test_publicacao_mostra_resumo_e_trilha(self):
        post = vaga("Estamos contratando", "dados", publicacao=True, resumo="Vaga remota de dados",
                    fonte="LinkedIn")
        html = relatorio.montar_html([post], apoio.cfg(), AGORA_BR, {})
        self.assertIn("Vaga remota de dados", html)
        self.assertIn("Abrir publicação", html)
        self.assertIn("Publicações de recrutadores", html)

    def test_vaga_do_exterior_indica_curriculo_em_ingles(self):
        v = vaga("Junior Data Analyst", "dados", curriculo="Dados (versão em inglês)", modalidade="Remoto (exterior)")
        self.assertIn("currículo em inglês", relatorio.montar_html([v], apoio.cfg(), AGORA_BR, {}))

    def test_alerta(self):
        html = relatorio.montar_html([vaga("Estágio", "dados", alertas=["menciona pagamento"])], apoio.cfg(),
                                     AGORA_BR, {})
        self.assertIn("Atenção: menciona pagamento", html)


class TestTextoECsv(unittest.TestCase):
    def test_texto_puro(self):
        texto = relatorio.montar_texto([vaga("Estágio em Dados", "dados")], apoio.cfg(), AGORA_BR, {"falhas": []})
        self.assertIn("== Dados (1) · Currículo: Dados ==", texto)
        self.assertIn("https://exemplo.com/", texto)

    def test_csv(self):
        dados = relatorio.montar_csv([vaga("Estágio; em Dados", "dados"), vaga("Suporte", "suporte")],
                                     apoio.cfg(), AGORA_BR)
        self.assertTrue(dados.startswith(b"\xef\xbb\xbf"))
        linhas = list(csv.reader(io.StringIO(dados.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(linhas[0], relatorio.COLUNAS_CSV)
        self.assertEqual(len(linhas), 3)
        self.assertEqual(linhas[1][3], "Estágio; em Dados")
        self.assertEqual(linhas[1][0], "03/11/2026")


if __name__ == "__main__":
    unittest.main()
