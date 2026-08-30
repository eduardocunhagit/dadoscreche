import unittest

import pandas as pd

from frente2.integrar_frentes import integrar


class IntegracaoFrentesTest(unittest.TestCase):
    def test_integration_conserves_front_one_total(self):
        frente1 = pd.DataFrame({
            "ano": [2025],
            "origin_area": ["CENTRO"],
            "grupamento_norm": ["MATERNAL I"],
            "inscricoes_previstas": [100.0],
        })
        frente2 = pd.DataFrame({
            "ano": [2025, 2025],
            "origin_area": ["CENTRO", "CENTRO"],
            "grupamento_norm": ["MATERNAL I", "MATERNAL I"],
            "alternativa_id": ["A|I", "B|P"],
            "unidade": ["A", "B"],
            "horario_norm": ["INTEGRAL", "PARCIAL"],
            "choice_share": [0.6, 0.4],
        })
        result = integrar(frente1, frente2)
        self.assertAlmostEqual(result["demanda_prevista"].sum(), 100.0)
        self.assertEqual(result["demanda_prevista"].tolist(), [60.0, 40.0])


if __name__ == "__main__":
    unittest.main()
