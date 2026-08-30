import unittest

import pandas as pd

from pipeline_demanda.integrar_frentes import integrar


class ProjecaoDemandaTest(unittest.TestCase):
    def test_projection_conserves_total(self):
        totals = pd.DataFrame({
            "ano": [2025],
            "origin_area": ["CENTRO"],
            "grupamento_norm": ["MATERNAL I"],
            "inscricoes_previstas": [100.0],
        })
        shares = pd.DataFrame({
            "ano": [2025, 2025],
            "origin_area": ["CENTRO", "CENTRO"],
            "grupamento_norm": ["MATERNAL I", "MATERNAL I"],
            "alternativa_id": ["A|I", "B|P"],
            "unidade": ["A", "B"],
            "horario_norm": ["INTEGRAL", "PARCIAL"],
            "choice_share": [0.6, 0.4],
        })
        result = integrar(totals, shares)
        self.assertAlmostEqual(result["demanda_prevista"].sum(), 100.0)
        self.assertEqual(result["demanda_prevista"].tolist(), [60.0, 40.0])


if __name__ == "__main__":
    unittest.main()
