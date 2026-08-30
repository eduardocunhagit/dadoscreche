import unittest

import numpy as np
import pandas as pd

from pipeline_demanda.rotinas.models import (
    ConditionalLogit,
    HistoricalShareBenchmark,
    NearestUnitBenchmark,
)


def synthetic_choices(years=(2021, 2022, 2023), choices_per_year=20):
    rows = []
    for year in years:
        for choice in range(choices_per_year):
            choice_id = f"{year}-{choice}"
            chosen_unit = "A" if choice < choices_per_year * 0.75 else "B"
            for unit, distance in (("A", 1.0), ("B", 4.0)):
                rows.append(
                    {
                        "ano": year,
                        "choice_id": choice_id,
                        "unit_id": unit,
                        "chosen": int(unit == chosen_unit),
                        "distance_km": distance,
                        "grupamento": "M1",
                        "horario": "Integral",
                        "capacity": 30 if unit == "A" else 20,
                    }
                )
    return pd.DataFrame(rows)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.frame = synthetic_choices()

    def assert_probabilities_sum_to_one(self, probability):
        sums = probability.groupby(self.frame["choice_id"]).sum()
        np.testing.assert_allclose(sums.to_numpy(), 1.0)

    def test_historical_share_prefers_popular_unit(self):
        model = HistoricalShareBenchmark(stratum_cols=("grupamento", "horario"))
        probability = model.fit(self.frame).predict_proba(self.frame)
        self.assert_probabilities_sum_to_one(probability)
        mean = self.frame.assign(p=probability).groupby("unit_id")["p"].mean()
        self.assertGreater(mean["A"], mean["B"])

    def test_nearest_unit_is_deterministic(self):
        probability = NearestUnitBenchmark().fit(self.frame).predict_proba(self.frame)
        self.assert_probabilities_sum_to_one(probability)
        predicted = self.frame.assign(p=probability)
        self.assertTrue((predicted.loc[predicted.unit_id == "A", "p"] == 1).all())

    def test_conditional_logit_learns_negative_distance(self):
        model = ConditionalLogit(["distance_km", "capacity"], l2=0.05)
        probability = model.fit(self.frame).predict_proba(self.frame)
        self.assert_probabilities_sum_to_one(probability)
        coefficients = model.coefficient_table().set_index("feature")
        self.assertLess(coefficients.loc["distance_km", "coefficient_original_scale"], 0)
        explanation = model.explain(self.frame.iloc[:2])
        self.assertIn("contribution__distance_km", explanation)

    def test_invalid_choice_set_is_rejected(self):
        invalid = self.frame.copy()
        invalid.loc[invalid.choice_id == invalid.choice_id.iloc[0], "chosen"] = 0
        with self.assertRaises(ValueError):
            ConditionalLogit(["distance_km"]).fit(invalid)


if __name__ == "__main__":
    unittest.main()
