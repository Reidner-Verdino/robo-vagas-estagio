"""Testes da classificação: a regra que decide o que chega ao e-mail."""

import unittest

import apoio
from apoio import candidato
from reid import classificacao as cl
from reid.classificacao import classificar
from reid.modelo import Vaga


def aceita(c, cfg=None):
    vaga, motivo = classificar(c, cfg or apoio.cfg())
    if vaga is None:
        raise AssertionError(f"'{c.titulo}' foi descartada por: {motivo}")
    return vaga


def motivo(c, cfg=None):
    vaga, m = classificar(c, cfg or apoio.cfg())
    if vaga is not None:
        raise AssertionError(f"'{c.titulo}' deveria ser descartada, mas entrou em {vaga.trilha}")
    return m


class TestTrilhas(unittest.TestCase):
    def test_cada_trilha(self):
        casos = {
            "Estágio em Análise de Dados": "dados",
            "Estágio - Dados e Gestão": "dados",
            "Estagiário de BI": "dados",
            "Data Analyst Intern": "dados",
            "Desenvolvedor Python Júnior": "desenvolvimento",
            "Estágio Backend": "desenvolvimento",
            "Analista de Automação Júnior": "desenvolvimento",
            "Analista de Suporte N1": "suporte",
            "Help Desk Júnior": "suporte",
            "Estágio em TI": "ti_geral",
            "Estagiário de Tecnologia da Informação": "ti_geral",
        }
        for titulo, trilha in casos.items():
            self.assertEqual(aceita(candidato(titulo=titulo, modalidade_hint="remoto")).trilha, trilha, titulo)

    def test_prioridade_dados_antes_de_desenvolvimento(self):
        self.assertEqual(aceita(candidato(titulo="Engenheiro de Dados Python Júnior")).trilha, "dados")

    def test_fora_de_ti(self):
        for titulo in ["Estágio em Recursos Humanos", "Assistente Administrativo", "Recepcionista"]:
            self.assertEqual(motivo(candidato(titulo=titulo)), cl.FORA_DE_TI, titulo)

    def test_termos_excluidos(self):
        for titulo in ["Vendedor Interno de Software", "Estágio em Vendas - Tecnologia",
                       "Técnico em Automação Industrial Júnior"]:
            self.assertEqual(motivo(candidato(titulo=titulo)), cl.EXCLUIDA, titulo)

    def test_curriculo_sugerido(self):
        self.assertEqual(aceita(candidato(titulo="Estágio em Dados")).curriculo, "Dados")
        self.assertEqual(aceita(candidato(titulo="Analista de Suporte N1")).curriculo, "Suporte")


class TestNivel(unittest.TestCase):
    def test_niveis_aceitos(self):
        casos = {"Estágio em Dados": "Estágio", "Desenvolvedor Python Jr": "Júnior",
                 "Analista de Suporte N1": "Júnior", "Desenvolvedor Júnior/Pleno": "Júnior",
                 "Data Analyst Intern": "Estágio", "Junior Data Analyst": "Júnior"}
        for titulo, nivel in casos.items():
            self.assertEqual(aceita(candidato(titulo=titulo)).nivel, nivel, titulo)

    def test_somente_estagio_e_junior(self):
        self.assertEqual(apoio.cfg()["niveis"]["aceitos"], ["estagio", "junior"])
        self.assertEqual(motivo(candidato(titulo="Trainee de Tecnologia")), cl.NIVEL_NAO_ACEITO)
        self.assertEqual(motivo(candidato(titulo="Analista de Dados", nivel_hint="trainee")), cl.NIVEL_NAO_ACEITO)
        self.assertEqual(motivo(candidato(titulo="Analista de Dados")), cl.NIVEL_NAO_INFORMADO)

    def test_niveis_configuraveis(self):
        cfg = apoio.cfg()
        cfg["niveis"]["aceitos"] = ["estagio", "junior", "trainee"]
        self.assertEqual(aceita(candidato(titulo="Trainee de Tecnologia"), cfg).nivel, "Trainee")

    def test_niveis_acima_de_junior(self):
        for titulo in ["Engenheiro de Dados Sênior", "Desenvolvedor Pleno", "Analista de Suporte N2",
                       "Analista de Sistemas II", "Coordenador de TI", "Tech Lead Python", "Data Engineer Sr"]:
            self.assertEqual(motivo(candidato(titulo=titulo)), cl.NIVEL_ALTO, titulo)

    def test_interno_nao_e_estagio(self):
        self.assertEqual(motivo(candidato(titulo="Desenvolvedor Interno")), cl.NIVEL_NAO_INFORMADO)

    def test_aprendiz_descartado(self):
        self.assertEqual(motivo(candidato(titulo="Jovem Aprendiz de TI")), cl.NIVEL_ALTO)
        self.assertEqual(motivo(candidato(titulo="Auxiliar de TI", nivel_hint="excluido")), cl.NIVEL_ALTO)

    def test_tipo_informado_pela_fonte(self):
        self.assertEqual(aceita(candidato(titulo="Analista de Dados", nivel_hint="estagio")).nivel, "Estágio")

    def test_nivel_nao_informado_pode_ser_aceito(self):
        cfg = apoio.cfg()
        self.assertFalse(cfg["perfil"]["aceitar_nivel_nao_informado"])
        cfg["perfil"]["aceitar_nivel_nao_informado"] = True
        self.assertEqual(aceita(candidato(titulo="Analista de Dados"), cfg).nivel, "Não informado")


class TestModalidade(unittest.TestCase):
    def test_remoto(self):
        self.assertEqual(aceita(candidato(modalidade_hint="remoto", local="São Paulo, SP")).modalidade, "Remoto")
        self.assertEqual(aceita(candidato(titulo="Estágio Dados - 100% Remoto", local="São Paulo, SP")).modalidade,
                         "Remoto")

    def test_rio_de_janeiro_e_regiao(self):
        self.assertEqual(aceita(candidato(local="Rio de Janeiro, RJ")).modalidade, "Presencial (RJ)")
        self.assertEqual(aceita(candidato(local="Nova Iguaçu, Rio de Janeiro", modalidade_hint="hibrido")).modalidade,
                         "Híbrido (RJ)")
        self.assertEqual(aceita(candidato(local="Duque de Caxias, RJ")).modalidade, "Presencial (RJ)")

    def test_fora_da_regiao(self):
        for local in ["São Paulo, SP", "Macaé, Rio de Janeiro", "Belo Horizonte, MG", "Niterói, RJ",
                      "São Gonçalo, RJ"]:
            self.assertEqual(motivo(candidato(local=local)), cl.FORA_DA_REGIAO, local)

    def test_centro_do_rio_tem_prioridade(self):
        centro = aceita(candidato(titulo="Estágio em Dados - Centro/RJ", local="Rio de Janeiro, RJ"))
        outro = aceita(candidato(titulo="Estágio em Dados", local="Rio de Janeiro, RJ"))
        remoto = aceita(candidato(titulo="Estágio em Dados", modalidade_hint="remoto"))
        self.assertEqual(centro.modalidade, "Presencial (Centro do Rio)")
        self.assertEqual(outro.modalidade, "Presencial (RJ)")
        self.assertGreater(centro.pontuacao, outro.pontuacao)
        self.assertGreater(centro.pontuacao, remoto.pontuacao)
        hibrido = aceita(candidato(titulo="Estágio em Dados", local="Rio de Janeiro, RJ", modalidade_hint="hibrido",
                                   resumo="Escritório no Centro do Rio"))
        self.assertEqual(hibrido.modalidade, "Híbrido (Centro do Rio)")

    def test_centro_de_outra_coisa_nao_conta(self):
        v = aceita(candidato(titulo="Estágio em Dados - Centro de Distribuição", local="Duque de Caxias, RJ"))
        self.assertEqual(v.modalidade, "Presencial (RJ)")

    def test_local_generico_fica_a_confirmar(self):
        for local in ["", "Brasil", "Brazil"]:
            self.assertEqual(aceita(candidato(local=local)).modalidade, "A confirmar", local)


class TestExterior(unittest.TestCase):
    def base(self, **campos):
        dados = dict(titulo="Junior Data Analyst", fonte="Remotive", exterior=True, regiao_exterior="Worldwide",
                     texto="Junior Data Analyst Data python", idade=2, idade_max=14, aceitar_sem_data=False)
        dados.update(campos)
        return candidato(**dados)

    def test_aceita_regioes_abertas_ao_brasil(self):
        for regiao in ["Worldwide", "LATAM", "Latin America", "Americas", "Brazil", "Anywhere in the world"]:
            v = aceita(self.base(regiao_exterior=regiao))
            self.assertEqual(v.modalidade, "Remoto (exterior)")
            self.assertEqual(v.curriculo, "Dados (versão em inglês)")

    def test_recusa_regioes_fechadas(self):
        for regiao in ["USA only", "Europe", "UK", ""]:
            self.assertEqual(motivo(self.base(regiao_exterior=regiao)), cl.REGIAO_EXTERIOR, regiao)

    def test_exige_nivel_explicito(self):
        self.assertEqual(motivo(self.base(titulo="Data Analyst", texto="Data Analyst")), cl.NIVEL_NAO_INFORMADO)
        self.assertEqual(motivo(self.base(titulo="Senior Data Analyst", texto="Senior Data Analyst")), cl.NIVEL_ALTO)
        self.assertEqual(aceita(self.base(titulo="Data Analyst", texto="Data Analyst", nivel_hint="estagio")).nivel,
                         "Estágio")


class TestPublicacoes(unittest.TestCase):
    def post(self, texto, **campos):
        return candidato(titulo=texto[:110], texto=texto, fonte="LinkedIn", publicacao=True,
                         link="https://www.linkedin.com/posts/fulana_vaga-activity-1", **campos)

    def test_anuncio_de_vaga(self):
        v = aceita(self.post("Estamos contratando Analista de Dados Júnior! Envie seu currículo"))
        self.assertEqual((v.trilha, v.publicacao), ("dados", True))
        self.assertEqual(aceita(self.post("Estágio de Suporte - Tech 100% Remoto #SeLiga")).trilha, "suporte")

    def test_candidato_procurando_vaga(self):
        self.assertEqual(motivo(self.post("Estou em busca de uma vaga como desenvolvedor #opentowork")), cl.CANDIDATO)

    def test_sem_sinal_de_anuncio(self):
        self.assertEqual(motivo(self.post("Dica de Python: use list comprehensions")), cl.NAO_ANUNCIO)

    def test_ti_generica_nao_basta_em_publicacao(self):
        self.assertEqual(motivo(self.post("Vaga para recepcionista em empresa de tecnologia")), cl.FORA_DE_TI)
        self.assertEqual(motivo(self.post("Vaga de recepcionista: envie seus dados e currículo")), cl.FORA_DE_TI)

    def test_nivel_no_corpo_do_post(self):
        v = aceita(self.post("Vaga aberta no time de dados! Buscamos pessoa estagiária, remoto"))
        self.assertEqual(v.nivel, "Estágio")
        self.assertEqual(motivo(self.post("Vaga aberta: Analista de Dados, remoto")), cl.NIVEL_NAO_INFORMADO)

    def test_nivel_alto_no_titulo_do_post(self):
        self.assertEqual(motivo(self.post("Vaga: Desenvolvedor Python Sênior, remoto")), cl.NIVEL_ALTO)


class TestDatasEAlertas(unittest.TestCase):
    def test_idade(self):
        self.assertEqual(motivo(candidato(idade=8, idade_max=7)), cl.ANTIGA)
        self.assertIsNotNone(aceita(candidato(idade=7, idade_max=7)))
        self.assertEqual(motivo(candidato(idade=None, aceitar_sem_data=False)), cl.SEM_DATA)
        self.assertIsNotNone(aceita(candidato(idade=None, aceitar_sem_data=True)))

    def test_dados_incompletos(self):
        self.assertEqual(motivo(candidato(link="")), cl.SEM_DADOS)
        self.assertEqual(motivo(candidato(titulo="", texto="")), cl.SEM_DADOS)
        self.assertEqual(motivo(candidato(link="javascript:alert(1)")), cl.SEM_DADOS)

    def test_alerta_de_pagamento(self):
        v = aceita(candidato(titulo="Estágio em Dados", resumo="Taxa de inscrição de R$ 50 via Pix"))
        self.assertEqual(len(v.alertas), 1)

    def test_tecnologias_citadas(self):
        v = aceita(candidato(titulo="Estágio em Dados - Python e SQL"))
        self.assertEqual(v.termos_stack, ["python", "sql"])


class TestPontuacao(unittest.TestCase):
    def test_ordem_de_prioridade(self):
        dados = aceita(candidato(titulo="Estágio em Dados", modalidade_hint="remoto", idade=1))
        dev = aceita(candidato(titulo="Estágio em Desenvolvimento de Software", modalidade_hint="remoto", idade=1))
        suporte = aceita(candidato(titulo="Analista de Suporte N1", idade=5))
        self.assertGreater(dados.pontuacao, dev.pontuacao)
        self.assertGreater(dev.pontuacao, suporte.pontuacao)


class TestSitesPrioritarios(unittest.TestCase):
    def test_bonus_para_sites_da_lista(self):
        catho = aceita(candidato(fonte="Catho", link="https://www.catho.com.br/vagas/1", modalidade_hint="remoto"))
        indeed = aceita(candidato(fonte="Indeed", link="https://br.indeed.com/vaga/1", modalidade_hint="remoto"))
        gupy = aceita(candidato(fonte="Gupy", link="https://acme.gupy.io/jobs/1", modalidade_hint="remoto"))
        self.assertEqual(catho.pontuacao - indeed.pontuacao, apoio.cfg()["perfil"]["bonus_site_prioritario"])
        self.assertEqual(gupy.pontuacao, catho.pontuacao)

    def test_reconhece_pelo_dominio(self):
        via_google = aceita(candidato(fonte="Google Vagas", link="https://www.infojobs.com.br/vaga-de-estagio-1",
                                      modalidade_hint="remoto"))
        outro = aceita(candidato(fonte="Google Vagas", link="https://www.glassdoor.com.br/vaga/1",
                                 modalidade_hint="remoto"))
        self.assertGreater(via_google.pontuacao, outro.pontuacao)

    def test_chave_por_link(self):
        a = aceita(candidato(titulo="Estágio em TI", empresa="", chave_por_link=True, link="https://catho.com.br/v/1"))
        b = aceita(candidato(titulo="Estágio em TI", empresa="", chave_por_link=True, link="https://catho.com.br/v/2"))
        self.assertNotEqual(a.chave, b.chave)


class TestChave(unittest.TestCase):
    def test_formato_compativel_com_o_historico_antigo(self):
        v = Vaga(titulo="Estágio em Dados", empresa="Acme", link="https://x", fonte="Gupy")
        self.assertEqual(v.chave, "estagio em dados|acme")
        p = Vaga(titulo="Post", empresa="Ana", link="https://www.linkedin.com/posts/ana_1?utm=x", fonte="LinkedIn",
                 publicacao=True)
        self.assertEqual(p.chave, "https://www.linkedin.com/posts/ana_1")


if __name__ == "__main__":
    unittest.main()
