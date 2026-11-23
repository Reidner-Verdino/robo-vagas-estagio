import unittest
from datetime import date, datetime, timedelta, timezone

import apoio
from reid import cota
from reid.principal import agenda_paga


class TestCota(unittest.TestCase):
    def test_proxima_renovacao(self):
        self.assertEqual(cota.proxima_renovacao(date(2026, 10, 20), 15), date(2026, 11, 15))
        self.assertEqual(cota.proxima_renovacao(date(2026, 10, 10), 15), date(2026, 10, 15))
        self.assertEqual(cota.proxima_renovacao(date(2026, 10, 15), 15), date(2026, 11, 15))
        self.assertEqual(cota.proxima_renovacao(date(2026, 1, 31), 31), date(2026, 2, 28))
        self.assertEqual(cota.proxima_renovacao(date(2026, 12, 20), 15), date(2027, 1, 15))

    def test_divide_o_saldo_ate_a_renovacao(self):
        agora = datetime(2026, 10, 15, 16, tzinfo=timezone.utc)      # 31 dias até 15/11 -> 62 execuções
        permitidas, renovacao, execucoes = cota.buscas_permitidas(240, agora, apoio.cfg()["serpapi"])
        self.assertEqual((renovacao, execucoes), (date(2026, 11, 15), 62))
        self.assertIn(permitidas, (3, 4))

    def test_soma_do_mes_nunca_passa_do_saldo(self):
        cfg = apoio.cfg()["serpapi"]
        inicio = datetime(2026, 10, 15, 16, tzinfo=timezone.utc)
        restantes = 250
        for i in range(62):
            agora = inicio + timedelta(hours=12 * i)
            permitidas, _, _ = cota.buscas_permitidas(restantes, agora, cfg)
            restantes -= permitidas
            self.assertGreaterEqual(restantes, 0)

    def test_saldo_zero(self):
        agora = datetime(2026, 10, 20, 16, tzinfo=timezone.utc)
        self.assertEqual(cota.buscas_permitidas(0, agora, apoio.cfg()["serpapi"])[0], 0)

    def test_prioridade_no_ciclo(self):
        buscas = agenda_paga(apoio.cfg())
        ciclo = cota.ciclo_ponderado(buscas)
        contagem = {b["id"]: 0 for b in buscas}
        for b in ciclo:
            contagem[b["id"]] += 1
        self.assertEqual(sum(contagem.values()), sum(b["peso"] for b in buscas))
        self.assertGreater(contagem["linkedin_dados"], contagem["google_vagas_1"])

    def test_todas_as_buscas_rodam_ao_longo_do_tempo(self):
        buscas = agenda_paga(apoio.cfg())
        vistas = set()
        for janela in range(12):
            agora = datetime.fromtimestamp(janela * 12 * 3600, tz=timezone.utc)
            escolhidas = cota.escolher(buscas, 4, agora)
            self.assertEqual(len(escolhidas), 4)
            self.assertEqual(len({b["id"] for b in escolhidas}), 4)
            vistas |= {b["id"] for b in escolhidas}
        self.assertEqual(vistas, {b["id"] for b in buscas})

    def test_limites(self):
        buscas = agenda_paga(apoio.cfg())
        agora = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.assertEqual(cota.escolher(buscas, 0, agora), [])
        self.assertEqual(len(cota.escolher(buscas, 99, agora)), len(buscas))
        self.assertEqual(cota.escolher([], 4, agora), [])


if __name__ == "__main__":
    unittest.main()
