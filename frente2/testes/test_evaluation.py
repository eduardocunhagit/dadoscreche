import unittest

import numpy as np
import pandas as pd

from frente2.rotinas.evaluation import (
    choice_metrics,
    default_model_factories,
    run_temporal_evaluation,
    unit_demand_comparison,
)


def temporal_choices():
    rows = []
    for year in range(2021, 2026):
        for choice in range(8):
            selected = "A" if choice < 6 else "B"
            for unit, distance, capacity in (("A", 1.0, 30), ("B", 3.0, 20)):
                rows.append(
                    {
                        "ano": year,
                        "choice_id": f"{year}-{choice}",
                        "unit_id": unit,
                        "chosen": int(unit == selected),
                        "distance_km": distance,
                        "capacity": capacity,
                        "grupamento": "M1",
                        "horario": "Integral",
                    }
                )
    return pd.DataFrame(rows)


class EvaluationTests(unittest.TestCase):
    def test_choice_and_demand_metrics(self):
        frame = temporal_choices().query("ano == 2025").copy()
        frame["predicted_probability"] = np.where(frame.unit_id == "A", 0.75, 0.25)
        metrics = choice_metrics(frame)
        self.assertAlmostEqual(metrics["top1"], 0.75)
        demand = unit_demand_comparison(frame)
        self.assertAlmostEqual(demand.absolute_error.sum(), 0.0)

    def test_temporal_runner_returns_in_sample_and_oos(self):
        frame = temporal_choices()
        factories = default_model_factories(["distance_km", "capacity"])
        result = run_temporal_evaluation(frame, factories)
        self.assertEqual(set(result.metrics["sample"]), {"in_sample", "oos"})
        self.assertEqual(result.metrics.query("sample == 'oos'").shape[0], 8)
        sums = result.predictions.groupby(["model", "fold", "sample", "choice_id"])[
            "predicted_probability"
        ].sum()
        np.testing.assert_allclose(sums.to_numpy(), 1.0)
        self.assertTrue(
            {"predicted_demand", "observed_demand", "absolute_error"}.issubset(
                result.unit_demand.columns
            )
        )


if __name__ == "__main__":
    unittest.main()
