import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import apoio  # noqa: F401
from reid import historico
from reid.historico import HistoricoInvalido
from reid.modelo import Vaga


class TestHistorico(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "vagas_vistas.json"

    def tearDown(self):
        self.pasta.cleanup()

    def test_arquivo_ausente_e_vazio(self):
        self.assertEqual(historico.carregar_vistas(self.caminho), {})
        self.caminho.write_text("", encoding="utf-8")
        self.assertEqual(historico.carregar_vistas(self.caminho), {})

    def test_arquivo_corrompido_interrompe(self):
        self.caminho.write_text("{ isto não é json", encoding="utf-8")
        with self.assertRaises(HistoricoInvalido):
            historico.carregar_vistas(self.caminho)
        self.caminho.write_text("[1, 2]", encoding="utf-8")
        with self.assertRaises(HistoricoInvalido):
            historico.carregar_vistas(self.caminho)
        self.caminho.write_text('{"a": 1}', encoding="utf-8")
        with self.assertRaises(HistoricoInvalido):
            historico.carregar_vistas(self.caminho)

    def test_salva_e_remove_antigas(self):
        vistas = {"antiga|x": "2026-01-01", "recente|y": "2026-10-30"}
        historico.registrar_vistas(vistas, ["nova|z"], date(2026, 11, 3))
        historico.salvar_vistas(self.caminho, vistas, date(2026, 11, 3), 90)
        salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertEqual(salvo, {"recente|y": "2026-10-30", "nova|z": "2026-11-03"})
        self.assertEqual(list(Path(self.pasta.name).glob(".*.tmp")), [])

    def test_estatisticas(self):
        vagas = [Vaga("a", "e", "l", "f", trilha="dados", termos_stack=["python", "sql"]),
                 Vaga("b", "e", "l", "f", trilha="dados", termos_stack=["python"])]
        estat = {}
        historico.registrar_estatisticas(estat, vagas, date(2026, 11, 3))
        historico.registrar_estatisticas(estat, vagas[:1], date(2026, 11, 4))
        self.assertEqual(estat["2026-11"]["vagas"], 3)
        self.assertEqual(historico.mais_citados(estat, date(2026, 11, 5)), [("python", 3), ("sql", 2)])
        self.assertEqual(estat["2026-11"]["trilhas"], {"dados": 3})

    def test_guarda_doze_meses(self):
        estat = {f"2025-{m:02d}": {"vagas": 1, "termos": {}, "trilhas": {}} for m in range(1, 13)}
        historico.registrar_estatisticas(estat, [], date(2026, 1, 10))
        self.assertEqual(len(estat), 12)
        self.assertNotIn("2025-01", estat)
        self.assertIn("2026-01", estat)


if __name__ == "__main__":
    unittest.main()
