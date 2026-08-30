import unittest

import pandas as pd

from modelo_demanda.rotinas.competition import build_colisting_network, colisting_competition


class CompetitionTests(unittest.TestCase):
    def test_overlap_and_weighted_capacity(self):
        lists = pd.DataFrame(
            {
                "choice_id": [1, 1, 2, 2, 3, 3],
                "unit_id": ["A", "B", "A", "B", "A", "C"],
            }
        )
        network = build_colisting_network(lists)
        ab = network.query("unit_i == 'A' and unit_j == 'B'").iloc[0]
        self.assertEqual(ab.n_ij, 2)
        self.assertAlmostEqual(ab.omega, 2 / (3 * 2) ** 0.5)

        capacity = pd.DataFrame(
            {"unit_id": ["A", "B", "C", "D"], "capacity_ex_ante": [10, 20, 30, 40]}
        )
        competition = colisting_competition(network, capacity).set_index("unit_id")
        expected_a = ab.omega * 20 + (1 / (3 * 1) ** 0.5) * 30
        self.assertAlmostEqual(competition.loc["A", "competition_colisting"], expected_a)
        self.assertEqual(competition.loc["D", "competition_colisting"], 0)

    def test_network_uses_only_rows_passed_to_it(self):
        train = pd.DataFrame({"choice_id": [1, 1], "unit_id": ["A", "B"]})
        future = pd.DataFrame({"choice_id": [2, 2], "unit_id": ["A", "C"]})
        network = build_colisting_network(train)
        self.assertNotIn("C", set(network.unit_i) | set(network.unit_j))
        self.assertIn("C", set(build_colisting_network(pd.concat([train, future])).unit_j))


if __name__ == "__main__":
    unittest.main()
