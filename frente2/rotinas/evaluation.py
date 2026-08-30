"""Validação in-sample e temporal fora da amostra da Frente 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from .models import ConditionalLogit, HistoricalShareBenchmark, NearestUnitBenchmark
from .splits import STANDARD_FOLDS, TemporalFold


DEFAULT_FOLDS = STANDARD_FOLDS


@dataclass
class EvaluationResult:
    predictions: pd.DataFrame
    metrics: pd.DataFrame
    unit_demand: pd.DataFrame


def _choice_codes(frame: pd.DataFrame, choice_cols: Sequence[str]) -> np.ndarray:
    keys = pd.MultiIndex.from_frame(frame[list(choice_cols)])
    return pd.factorize(keys, sort=False)[0]


def choice_metrics(
    frame: pd.DataFrame,
    probability_col: str = "predicted_probability",
    chosen_col: str = "chosen",
    choice_cols: Sequence[str] = ("choice_id",),
) -> dict[str, float]:
    required = [*choice_cols, probability_col, chosen_col]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    probability = frame[probability_col].to_numpy(dtype=float)
    chosen = frame[chosen_col].to_numpy(dtype=float)
    codes = _choice_codes(frame, choice_cols)
    sums = pd.Series(probability).groupby(codes).sum().to_numpy()
    chosen_sums = pd.Series(chosen).groupby(codes).sum().to_numpy()
    if np.any(probability < 0) or not np.isfinite(probability).all():
        raise ValueError("Probabilidades devem ser finitas e não negativas")
    if not np.allclose(sums, 1.0, atol=1e-8):
        raise ValueError("Probabilidades devem somar um em cada conjunto")
    if not np.allclose(chosen_sums, 1.0):
        raise ValueError("Cada conjunto deve ter exatamente uma escolha observada")

    selected_probability = probability[chosen == 1]
    log_loss = -np.log(np.clip(selected_probability, 1e-15, 1.0)).mean()
    maximum = pd.Series(probability).groupby(codes).transform("max").to_numpy()
    is_top = np.isclose(probability, maximum, rtol=0.0, atol=1e-12)
    top_count = pd.Series(is_top.astype(int)).groupby(codes).transform("sum").to_numpy()
    top1 = np.sum(((chosen == 1) & is_top) / top_count) / np.unique(codes).size
    return {
        "log_loss": float(log_loss),
        "top1": float(top1),
        "n_choice_sets": int(np.unique(codes).size),
        "n_alternatives": int(len(frame)),
    }


def unit_demand_comparison(
    frame: pd.DataFrame,
    unit_col: str = "unit_id",
    probability_col: str = "predicted_probability",
    chosen_col: str = "chosen",
    group_cols: Sequence[str] = (),
) -> pd.DataFrame:
    required = [*group_cols, unit_col, probability_col, chosen_col]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    comparison = (
        frame.groupby([*group_cols, unit_col], dropna=False, as_index=False)
        .agg(
            predicted_demand=(probability_col, "sum"),
            observed_demand=(chosen_col, "sum"),
        )
    )
    comparison["error"] = comparison["predicted_demand"] - comparison["observed_demand"]
    comparison["absolute_error"] = comparison["error"].abs()
    return comparison


def demand_metrics(comparison: pd.DataFrame) -> dict[str, float]:
    required = {"absolute_error", "observed_demand"}
    missing = sorted(required - set(comparison.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    denominator = float(comparison["observed_demand"].sum())
    absolute_error = comparison["absolute_error"].to_numpy(dtype=float)
    return {
        "demand_mae": float(absolute_error.mean()),
        "demand_wape": float(absolute_error.sum() / denominator) if denominator > 0 else np.nan,
    }


def default_model_factories(
    full_feature_cols: Sequence[str],
    choice_cols: Sequence[str] = ("choice_id",),
    unit_col: str = "unit_id",
    chosen_col: str = "chosen",
    distance_col: str = "distance_km",
    stratum_cols: Sequence[str] = ("grupamento", "horario"),
) -> dict[str, Callable[[], object]]:
    common = {"choice_cols": choice_cols, "unit_col": unit_col}
    return {
        "historical_share": lambda: HistoricalShareBenchmark(
            **common, chosen_col=chosen_col, stratum_cols=stratum_cols
        ),
        "nearest_unit": lambda: NearestUnitBenchmark(
            **common, distance_col=distance_col
        ),
        "conditional_logit_distance": lambda: ConditionalLogit(
            [distance_col], **common, chosen_col=chosen_col
        ),
        "conditional_logit_full": lambda: ConditionalLogit(
            full_feature_cols, **common, chosen_col=chosen_col
        ),
    }


def run_temporal_evaluation(
    frame: pd.DataFrame,
    model_factories: Mapping[str, Callable[[], object]],
    folds: Sequence[TemporalFold] = DEFAULT_FOLDS,
    year_col: str = "ano",
    choice_cols: Sequence[str] = ("choice_id",),
    unit_col: str = "unit_id",
    chosen_col: str = "chosen",
    demand_group_cols: Sequence[str] = (),
    fold_transform: Callable[[pd.DataFrame, pd.DataFrame], tuple[pd.DataFrame, pd.DataFrame]]
    | None = None,
) -> EvaluationResult:
    """Ajusta cada modelo no passado e avalia treino e ano futuro separadamente."""
    required = [year_col, *choice_cols, unit_col, chosen_col, *demand_group_cols]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    prediction_parts = []
    metric_rows = []
    demand_parts = []

    for fold in folds:
        train = frame.loc[frame[year_col].isin(fold.train_years)].copy()
        test = frame.loc[frame[year_col] == fold.test_year].copy()
        if train.empty or test.empty:
            raise ValueError(f"Fold {fold.name} sem observações de treino ou teste")
        if fold_transform is not None:
            train, test = fold_transform(train, test)

        for model_name, factory in model_factories.items():
            model = factory().fit(train)
            for sample_name, sample in (("in_sample", train), ("oos", test)):
                evaluated = sample.copy()
                evaluated["predicted_probability"] = model.predict_proba(sample).to_numpy()
                evaluated["model"] = model_name
                evaluated["fold"] = fold.name
                evaluated["sample"] = sample_name
                metrics = choice_metrics(
                    evaluated, "predicted_probability", chosen_col, choice_cols
                )
                comparison = unit_demand_comparison(
                    evaluated,
                    unit_col,
                    "predicted_probability",
                    chosen_col,
                    demand_group_cols,
                )
                metrics.update(demand_metrics(comparison))
                metrics.update({"model": model_name, "fold": fold.name, "sample": sample_name})
                metric_rows.append(metrics)
                comparison["model"] = model_name
                comparison["fold"] = fold.name
                comparison["sample"] = sample_name
                demand_parts.append(comparison)
                prediction_parts.append(evaluated)

    return EvaluationResult(
        predictions=pd.concat(prediction_parts, ignore_index=True),
        metrics=pd.DataFrame(metric_rows),
        unit_demand=pd.concat(demand_parts, ignore_index=True),
    )
