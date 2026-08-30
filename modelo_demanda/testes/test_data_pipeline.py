import unittest

import pandas as pd

from modelo_demanda.rotinas.episodes import build_choice_episodes
from modelo_demanda.rotinas.historical import aggregate_historical_demand
from modelo_demanda.rotinas.io import prepare_query_a
from modelo_demanda.rotinas.normalization import normalize_code, normalize_text
from modelo_demanda.rotinas.splits import STANDARD_FOLDS, split_temporal
from modelo_demanda.rotinas.validation import assert_choice_invariants, check_choice_invariants


def synthetic_raw() -> pd.DataFrame:
    rows = [
        (2021, 179, 1, 10, 1, "0100001", "Creche Á", "Maternal I", "Parcial", "aluno_1"),
        (2021, 179, 1, 10, 2, "0100002", "Creche B", "Maternal I", "Parcial", "aluno_1"),
        (2023, 184, 2, 20, 1, "0100002", "Creche B", "Maternal I", "Integral", "aluno_2"),
        (2024, 194, 3, 30, 1, "0100001", "Creche Á", "Maternal I", "Parcial", "aluno_3"),
        (2025, 195, 4, 40, 1, "0100003", "Creche C", "Berçário", "Integral", "aluno_4"),
    ]
    columns = [
        "ano", "prm_id", "plm_id", "ipl_id", "opcao", "unidade",
        "nome_unidade", "grupamento", "horario", "aluno_anon",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame["data_criacao"] = "2021-01-05 10:00:00"
    frame["sexo_crianca"] = "F"
    frame["nascimento_aluno_anomes"] = "2019-01"
    frame["responsavel_anon"] = "responsavel_1"
    frame["CEP"] = "1234567.0"
    frame["bairro"] = " São  Cristóvão "
    frame["situacao"] = "Lista de espera"
    return frame


class NormalizationTest(unittest.TestCase):
    def test_text_and_code_normalization(self):
        self.assertEqual(normalize_text(pd.Series([" São  Cristóvão "])).iloc[0], "SAO CRISTOVAO")
        self.assertEqual(normalize_code(pd.Series(["1234567.0"]), width=8).iloc[0], "01234567")


class QueryATest(unittest.TestCase):
    def setUp(self):
        self.options = prepare_query_a(synthetic_raw())

    def test_schema_and_types(self):
        self.assertEqual(str(self.options["ano"].dtype), "Int64")
        self.assertEqual(self.options.loc[0, "grupamento_norm"], "MATERNAL I")
        self.assertEqual(self.options.loc[0, "CEP"], "01234567")

    def test_observed_episode_table_does_not_expand_rows(self):
        episodes = build_choice_episodes(self.options)
        self.assertEqual(len(episodes), len(self.options))
        self.assertEqual(episodes["inscricao_id"].nunique(), 4)
        self.assertEqual(int(episodes["primeira_opcao"].sum()), 4)

    def test_invariants_report_and_failure(self):
        report = check_choice_invariants(self.options)
        self.assertTrue(report["ok"].all())

        invalid = self.options.copy()
        invalid.loc[invalid["ipl_id"].eq(10), "opcao"] = 2
        with self.assertRaisesRegex(ValueError, "uma_primeira_opcao"):
            assert_choice_invariants(invalid)

    def test_rank_six_is_a_declared_warning(self):
        warning = self.options.iloc[[0]].copy()
        warning["opcao"] = 6
        report = check_choice_invariants(warning)
        row = report.set_index("regra").loc["rank_acima_do_limite_usual"]
        self.assertEqual(row["severidade"], "warning")
        self.assertEqual(row["violacoes"], 1)

    def test_repeated_alternative_is_a_warning_not_a_blocker(self):
        repeated = self.options.copy()
        registration = repeated["ipl_id"].eq(10)
        repeated.loc[registration & repeated["opcao"].eq(2), "unidade"] = "0100001"
        report = check_choice_invariants(repeated).set_index("regra")
        self.assertEqual(report.loc["alternativa_unica_na_lista", "severidade"], "warning")
        assert_choice_invariants(repeated)

    def test_rank_gap_is_preserved_as_a_warning(self):
        gap = self.options.copy()
        gap.loc[gap["ipl_id"].eq(10) & gap["opcao"].eq(2), "opcao"] = 3
        report = check_choice_invariants(gap).set_index("regra")
        self.assertEqual(report.loc["ranks_consecutivos_desde_um", "severidade"], "warning")
        assert_choice_invariants(gap)

    def test_standard_temporal_splits(self):
        episodes = build_choice_episodes(self.options)
        train_2024, test_2024 = split_temporal(episodes, STANDARD_FOLDS[0])
        train_2025, test_2025 = split_temporal(episodes, STANDARD_FOLDS[1])
        self.assertEqual(set(train_2024["ano"]), {2021, 2023})
        self.assertEqual(set(test_2024["ano"]), {2024})
        self.assertEqual(set(train_2025["ano"]), {2021, 2023, 2024})
        self.assertEqual(set(test_2025["ano"]), {2025})

    def test_historical_demand_keeps_two_denominators(self):
        demand = aggregate_historical_demand(build_choice_episodes(self.options))
        u2_2021 = demand[(demand["ano"].eq(2021)) & (demand["unidade"].eq("0100002"))].iloc[0]
        self.assertEqual(u2_2021["demanda_historica_lista"], 1)
        self.assertEqual(u2_2021["demanda_historica_primeira_opcao"], 0)

        u1_2021 = demand[(demand["ano"].eq(2021)) & (demand["unidade"].eq("0100001"))].iloc[0]
        self.assertEqual(u1_2021["participacao_historica_primeira_opcao"], 1.0)


if __name__ == "__main__":
    unittest.main()
