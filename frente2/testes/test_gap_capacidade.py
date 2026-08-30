import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calcular_gap_capacidade import calcular_gap


class GapCapacidadeTest(unittest.TestCase):
    def test_agrega_origens_e_turnos_antes_do_gap(self):
        demand = pd.DataFrame({
            "ano": [2025, 2025, 2025],
            "unidade": ["01001", "01001", "01001"],
            "grupamento_norm": ["MATERNAL I"] * 3,
            "origin_area": ["A", "A", "B"],
            "horario_norm": ["INTEGRAL", "PARCIAL", "INTEGRAL"],
            "demanda_prevista": [20.0, 10.0, 15.0],
        })
        capacity = pd.DataFrame({
            "ano": [2025], "unidade": ["01001"],
            "grupamento_norm": ["MATERNAL I"],
            "matriculas_ano_anterior": [40],
        })
        result = calcular_gap(demand, capacity, "demanda_prevista")
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "demanda_prevista"], 45)
        self.assertEqual(result.loc[0, "planning_gap"], 5)
        self.assertTrue(result.loc[0, "gap_positivo"])


if __name__ == "__main__":
    unittest.main()
