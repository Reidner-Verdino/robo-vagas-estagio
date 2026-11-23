import json
import tempfile
import unittest
from pathlib import Path

import apoio
from reid import config
from reid.config import ConfigInvalida


class TestConfig(unittest.TestCase):
    def validar(self, alterar):
        cfg = apoio.cfg()
        alterar(cfg)
        with self.assertRaises(ConfigInvalida) as ctx:
            config.validar(cfg)
        return str(ctx.exception)

    def test_config_do_projeto_e_valido(self):
        self.assertIsInstance(apoio.cfg(), dict)

    def test_secao_ausente(self):
        self.assertIn("serpapi", self.validar(lambda c: c.pop("serpapi")))

    def test_tipos_e_intervalos(self):
        self.assertIn("serpapi.dia_renovacao", self.validar(lambda c: c["serpapi"].update(dia_renovacao=32)))
        self.assertIn("trilhas[0].peso", self.validar(lambda c: c["trilhas"][0].update(peso=True)))
        self.assertIn("email.enviar_sem_vagas", self.validar(lambda c: c["email"].update(enviar_sem_vagas="sim")))

    def test_niveis_aceitos_e_bonus(self):
        self.assertIn("niveis.aceitos", self.validar(lambda c: c["niveis"].update(aceitos=["pleno"])))
        self.assertIn("niveis.aceitos", self.validar(lambda c: c["niveis"].update(aceitos=[])))
        self.assertIn("perfil.bonus_local_prioritario",
                      self.validar(lambda c: c["perfil"].update(bonus_local_prioritario=-1)))

    def test_sites(self):
        self.assertIn("dominio", self.validar(
            lambda c: c["fontes"]["sites"]["lista"][0].update(dominio="https://catho.com.br/vagas")))
        self.assertIn("repetido", self.validar(
            lambda c: c["fontes"]["sites"]["lista"].append(dict(c["fontes"]["sites"]["lista"][0]))))
        self.assertIn("fontes.sites", self.validar(lambda c: c["fontes"].pop("sites")))

    def test_trilha_repetida(self):
        self.assertIn("repetido", self.validar(lambda c: c["trilhas"].append(dict(c["trilhas"][0]))))

    def test_motor_e_site(self):
        self.assertIn("motor", self.validar(lambda c: c["fontes"]["linkedin"].update(motor="bing")))
        self.assertIn("linkedin.com", self.validar(
            lambda c: c["fontes"]["linkedin"]["buscas"][0].update(site="glassdoor.com")))

    def test_termo_vazio(self):
        self.assertIn("termos_stack[1]", self.validar(lambda c: c["termos_stack"].insert(1, "  ")))

    def test_varios_erros_de_uma_vez(self):
        def alterar(c):
            c["serpapi"]["dia_renovacao"] = 0
            c["email"]["max_por_secao"] = 0
        mensagem = self.validar(alterar)
        self.assertIn("serpapi.dia_renovacao", mensagem)
        self.assertIn("email.max_por_secao", mensagem)

    def test_json_com_erro_de_sintaxe(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "config.json"
            caminho.write_text('{"perfil": }', encoding="utf-8")
            with self.assertRaises(ConfigInvalida) as ctx:
                config.carregar(caminho)
            self.assertIn("linha 1", str(ctx.exception))
            with self.assertRaises(ConfigInvalida):
                config.carregar(Path(pasta) / "nao_existe.json")

    def test_recrutadores_podem_ficar_vazios(self):
        cfg = apoio.cfg()
        cfg["fontes"]["linkedin"]["recrutadores"] = []
        config.validar(cfg)
        cfg["fontes"]["linkedin"]["recrutadores"] = ["Ana Exemplo"]
        config.validar(cfg)
        json.dumps(cfg)


if __name__ == "__main__":
    unittest.main()
