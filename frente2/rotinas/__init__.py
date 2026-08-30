"""Modelos explicáveis para a distribuição da demanda entre creches."""

from .competition import build_colisting_network, colisting_competition
from .episodes import build_choice_episodes
from .historical import aggregate_historical_demand
from .io import load_query_a, prepare_query_a
from .splits import STANDARD_FOLDS, split_temporal
from .validation import assert_choice_invariants, check_choice_invariants
from .evaluation import (
    DEFAULT_FOLDS,
    EvaluationResult,
    TemporalFold,
    choice_metrics,
    default_model_factories,
    demand_metrics,
    run_temporal_evaluation,
    unit_demand_comparison,
)
from .models import (
    ConditionalLogit,
    HistoricalShareBenchmark,
    NearestUnitBenchmark,
)

__all__ = [
    "ConditionalLogit",
    "DEFAULT_FOLDS",
    "EvaluationResult",
    "HistoricalShareBenchmark",
    "NearestUnitBenchmark",
    "TemporalFold",
    "build_colisting_network",
    "choice_metrics",
    "colisting_competition",
    "default_model_factories",
    "demand_metrics",
    "run_temporal_evaluation",
    "unit_demand_comparison",
    "STANDARD_FOLDS",
    "aggregate_historical_demand",
    "assert_choice_invariants",
    "build_choice_episodes",
    "check_choice_invariants",
    "load_query_a",
    "prepare_query_a",
    "split_temporal",
]
