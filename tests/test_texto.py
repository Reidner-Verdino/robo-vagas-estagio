import unittest
from datetime import date

import apoio  # noqa: F401
from reid.texto import (data_absoluta, formatar_data, idade_em_dias, idade_relativa, iso_para_datetime,
                        limpar_html, normalizar, resumir, tem_termo, termos_encontrados)


class TestNormalizacao(unittest.TestCase):
    def test_remove_acentos_maiusculas_e_espacos(self):
        self.assertEqual(normalizar("  Estágio   em  TECNOLOGIA "), "estagio em tecnologia")

    def test_valores_vazios(self):
        self.assertEqual(normalizar(None), "")
        self.assertEqual(normalizar(""), "")


class TestTermos(unittest.TestCase):
    def test_palavra_inteira(self):
        self.assertTrue(tem_termo("Estagiário de TI", ["ti"]))
        self.assertFalse(tem_termo("Partida de futebol", ["ti"]))
        self.assertFalse(tem_termo("Atividades", ["ti"]))

    def test_prefixo_com_asterisco(self):
        for texto in ["Estágio", "Estagiário", "ESTAGIÁRIA de dados"]:
            self.assertTrue(tem_termo(texto, ["estagi*"]), texto)

    def test_intern_nao_casa_interno_nem_internacional(self):
        self.assertFalse(tem_termo("Vendedor Interno", ["intern", "internship"]))
        self.assertFalse(tem_termo("Comércio Internacional", ["intern"]))
        self.assertTrue(tem_termo("Data Intern", ["intern"]))

    def test_termos_com_simbolos(self):
        self.assertTrue(tem_termo("Desenvolvedor C# Júnior", ["c#"]))
        self.assertTrue(tem_termo("Dev .NET", [".net"]))
        self.assertTrue(tem_termo("Estágio Front-end", ["front-end"]))
        self.assertFalse(tem_termo("Internet", [".net"]))

    def test_termos_encontrados_sem_repeticao(self):
        self.assertEqual(termos_encontrados("Python, SQL e mais Python", ["python", "sql", "java"]), ["python", "sql"])

    def test_termo_vazio_e_invalido(self):
        with self.assertRaises(ValueError):
            tem_termo("x", ["*"])


class TestDatas(unittest.TestCase):
    def test_relativas_em_portugues_e_ingles(self):
        casos = {"há 5 horas": 0, "há 30 minutos": 0, "ontem": 1, "há 3 dias": 3, "há 2 semanas": 14,
                 "há 1 mês": 30, "há 2 meses": 60, "há 30+ dias": 30, "3 days ago": 3, "Just posted": 0,
                 "há uma semana": 7, "a day ago": 1, "2d": 2, "hoje": 0}
        for texto, esperado in casos.items():
            self.assertEqual(idade_relativa(texto), esperado, texto)

    def test_textos_que_nao_sao_datas(self):
        # "6 horas por dia" é barrado antes, pelo filtro de sinais de data da fonte (ver test_fontes)
        for texto in ["", "Tempo integral", "R$ 1.500 por mês", "Período de 2 de cada mês"]:
            self.assertIsNone(idade_relativa(texto), texto)

    def test_data_em_portugues_nao_vira_dias(self):
        self.assertIsNone(idade_relativa("29 de out. de 2026"))
        self.assertEqual(data_absoluta("29 de out. de 2026"), date(2026, 10, 29))

    def test_datas_absolutas(self):
        self.assertEqual(data_absoluta("Oct 29, 2026"), date(2026, 10, 29))
        self.assertEqual(data_absoluta("2026-10-29T10:00:00"), date(2026, 10, 29))
        self.assertEqual(data_absoluta("29/10/2026"), date(2026, 10, 29))
        self.assertIsNone(data_absoluta("31/02/2026"))
        self.assertIsNone(data_absoluta("Tempo integral"))

    def test_idade_de_data_absoluta(self):
        self.assertEqual(idade_em_dias("Oct 29, 2026", hoje=date(2026, 11, 3)), 5)
        self.assertEqual(idade_em_dias("há 2 dias", hoje=date(2026, 11, 3)), 2)
        self.assertIsNone(idade_em_dias("", hoje=date(2026, 11, 3)))

    def test_formatar_data(self):
        self.assertEqual(formatar_data("Oct 29, 2026"), "29/10/2026")
        self.assertEqual(formatar_data("2026-10-29"), "29/10/2026")
        self.assertEqual(formatar_data("há 2 dias"), "há 2 dias")
        self.assertEqual(formatar_data(""), "")

    def test_iso(self):
        self.assertEqual(iso_para_datetime("2026-10-29T12:00:00Z").utcoffset().total_seconds(), 0)
        self.assertIsNotNone(iso_para_datetime("2026-10-29T12:00:00").tzinfo)
        self.assertIsNone(iso_para_datetime("ontem"))
        self.assertIsNone(iso_para_datetime(None))


class TestResumo(unittest.TestCase):
    def test_resumir_corta_em_palavra(self):
        texto = "palavra " * 50
        r = resumir(texto, 30)
        self.assertTrue(r.endswith("…"))
        self.assertLessEqual(len(r), 31)

    def test_limpar_html(self):
        self.assertEqual(limpar_html("<p>Olá <b>mundo</b></p>"), "Olá mundo")


if __name__ == "__main__":
    unittest.main()
