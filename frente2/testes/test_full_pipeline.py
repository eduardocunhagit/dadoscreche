import unittest

import numpy as np
import pandas as pd

from frente2.executar_frente2 import CountConditionalLogit, softmax


class CompletePipelineTests(unittest.TestCase):
    def test_softmax_sums_to_one_by_market(self):
        codes = np.array([0, 0, 1, 1, 1])
        probability = softmax(np.array([1.0, 2.0, -1.0, 0.0, 1.0]), codes, 2)
        np.testing.assert_allclose(np.bincount(codes, weights=probability), 1.0)

    def test_count_logit_learns_distance_penalty(self):
        frame = pd.DataFrame({
            "market_id": ["a", "a", "b", "b", "c", "c"],
            "distance": [1.0, 5.0, 2.0, 6.0, 1.0, 7.0],
            "choice_count": [8, 2, 7, 3, 9, 1],
        })
        model = CountConditionalLogit(["distance"], max_iter=100).fit(frame)
        self.assertLess(model.beta_[0], 0)
        probability = model.predict(frame)
        for market in frame.market_id.unique():
            self.assertAlmostEqual(probability[frame.market_id.eq(market)].sum(), 1.0)


if __name__ == "__main__":
    unittest.main()
