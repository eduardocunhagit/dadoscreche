"""Benchmarks e logit condicional para a primeira opção da família."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd


def _require_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")


def _group_codes(frame: pd.DataFrame, choice_cols: Sequence[str]) -> np.ndarray:
    keys = pd.MultiIndex.from_frame(frame[list(choice_cols)])
    return pd.factorize(keys, sort=False)[0]


def _validate_choice_table(
    frame: pd.DataFrame,
    choice_cols: Sequence[str],
    unit_col: str,
    chosen_col: str | None = None,
) -> None:
    required = [*choice_cols, unit_col]
    if chosen_col is not None:
        required.append(chosen_col)
    _require_columns(frame, required)
    if frame.empty:
        raise ValueError("A tabela de alternativas está vazia")
    if frame[required].isna().any().any():
        raise ValueError("Chaves e escolha observada não podem ser nulas")
    if frame.duplicated([*choice_cols, unit_col]).any():
        raise ValueError("Cada unidade deve aparecer uma vez por conjunto de escolha")
    if chosen_col is not None:
        chosen = frame[chosen_col].to_numpy(dtype=float)
        if not np.isin(chosen, [0.0, 1.0]).all():
            raise ValueError(f"{chosen_col} deve conter apenas 0 e 1")
        sums = pd.Series(chosen).groupby(_group_codes(frame, choice_cols)).sum()
        if not np.allclose(sums.to_numpy(), 1.0):
            raise ValueError("Cada conjunto de escolha deve ter exatamente uma opção escolhida")


def _normalize_by_group(scores: np.ndarray, codes: np.ndarray) -> np.ndarray:
    totals = pd.Series(scores).groupby(codes).transform("sum").to_numpy()
    if np.any(totals <= 0) or not np.isfinite(totals).all():
        raise ValueError("Os escores devem gerar massa positiva em cada conjunto")
    return scores / totals


def _softmax_by_group(utility: np.ndarray, codes: np.ndarray) -> np.ndarray:
    order = np.argsort(codes, kind="stable")
    ordered_codes = codes[order]
    ordered_utility = utility[order]
    starts = np.r_[0, np.flatnonzero(np.diff(ordered_codes)) + 1]
    counts = np.diff(np.r_[starts, len(order)])
    maxima = np.maximum.reduceat(ordered_utility, starts)
    exp_utility = np.exp(ordered_utility - np.repeat(maxima, counts))
    totals = np.add.reduceat(exp_utility, starts)
    ordered_probability = exp_utility / np.repeat(totals, counts)
    probability = np.empty_like(ordered_probability)
    probability[order] = ordered_probability
    return probability


@dataclass
class HistoricalShareBenchmark:
    """Probabilidade proporcional às escolhas históricas da unidade."""

    choice_cols: Sequence[str] = ("choice_id",)
    unit_col: str = "unit_id"
    chosen_col: str = "chosen"
    stratum_cols: Sequence[str] = ()
    smoothing: float = 1.0

    def fit(self, frame: pd.DataFrame) -> "HistoricalShareBenchmark":
        if self.smoothing <= 0:
            raise ValueError("smoothing deve ser positivo")
        _validate_choice_table(frame, self.choice_cols, self.unit_col, self.chosen_col)
        _require_columns(frame, self.stratum_cols)
        keys = [*self.stratum_cols, self.unit_col]
        self.counts_ = (
            frame.groupby(keys, dropna=False)[self.chosen_col]
            .sum()
            .rename("_stratum_count")
            .reset_index()
        )
        self.global_counts_ = (
            frame.groupby(self.unit_col, dropna=False)[self.chosen_col]
            .sum()
            .rename("_global_count")
            .reset_index()
        )
        return self

    def predict_proba(self, frame: pd.DataFrame) -> pd.Series:
        if not hasattr(self, "counts_"):
            raise RuntimeError("O benchmark precisa ser ajustado antes da previsão")
        _validate_choice_table(frame, self.choice_cols, self.unit_col)
        _require_columns(frame, self.stratum_cols)
        row = frame[[*self.stratum_cols, self.unit_col]].copy()
        row["_row"] = np.arange(len(row))
        row = row.merge(
            self.counts_, on=[*self.stratum_cols, self.unit_col], how="left", sort=False
        )
        row = row.merge(self.global_counts_, on=self.unit_col, how="left", sort=False)
        row = row.sort_values("_row")
        count = row["_stratum_count"].fillna(row["_global_count"]).fillna(0.0)
        scores = count.to_numpy(dtype=float) + self.smoothing
        probability = _normalize_by_group(scores, _group_codes(frame, self.choice_cols))
        return pd.Series(probability, index=frame.index, name="predicted_probability")


@dataclass
class NearestUnitBenchmark:
    """Divide probabilidade igualmente entre as unidades de menor distância."""

    choice_cols: Sequence[str] = ("choice_id",)
    unit_col: str = "unit_id"
    distance_col: str = "distance_km"
    tie_tolerance: float = 1e-10

    def fit(self, frame: pd.DataFrame) -> "NearestUnitBenchmark":
        _validate_choice_table(frame, self.choice_cols, self.unit_col)
        _require_columns(frame, [self.distance_col])
        return self

    def predict_proba(self, frame: pd.DataFrame) -> pd.Series:
        _validate_choice_table(frame, self.choice_cols, self.unit_col)
        _require_columns(frame, [self.distance_col])
        distance = frame[self.distance_col].to_numpy(dtype=float)
        if not np.isfinite(distance).all() or np.any(distance < 0):
            raise ValueError("Distâncias devem ser finitas e não negativas")
        codes = _group_codes(frame, self.choice_cols)
        minima = pd.Series(distance).groupby(codes).transform("min").to_numpy()
        nearest = np.isclose(distance, minima, rtol=0.0, atol=self.tie_tolerance)
        probability = _normalize_by_group(nearest.astype(float), codes)
        return pd.Series(probability, index=frame.index, name="predicted_probability")


@dataclass
class ConditionalLogit:
    """Logit condicional linear estimado por máxima verossimilhança."""

    feature_cols: Sequence[str]
    choice_cols: Sequence[str] = ("choice_id",)
    unit_col: str = "unit_id"
    chosen_col: str = "chosen"
    l2: float = 0.01
    max_iter: int = 1_000
    tolerance: float = 1e-7
    initial_step: float = 1.0
    coefficients_: np.ndarray = field(init=False, repr=False)

    def _matrix(self, frame: pd.DataFrame, fit: bool) -> np.ndarray:
        _require_columns(frame, self.feature_cols)
        matrix = frame[list(self.feature_cols)].to_numpy(dtype=float)
        if not np.isfinite(matrix).all():
            raise ValueError("Atributos do modelo devem ser finitos")
        if fit:
            self.feature_means_ = matrix.mean(axis=0)
            scale = matrix.std(axis=0)
            self.feature_scales_ = np.where(scale > 0, scale, 1.0)
        return (matrix - self.feature_means_) / self.feature_scales_

    def _loss_gradient(
        self,
        beta: np.ndarray,
        matrix: np.ndarray,
        chosen: np.ndarray,
        codes: np.ndarray,
        n_choices: int,
    ) -> tuple[float, np.ndarray]:
        probability = _softmax_by_group(matrix @ beta, codes)
        chosen_probability = probability[chosen == 1]
        loss = -np.log(np.clip(chosen_probability, 1e-15, 1.0)).sum() / n_choices
        loss += 0.5 * self.l2 * float(beta @ beta)
        gradient = matrix.T @ (probability - chosen) / n_choices + self.l2 * beta
        return float(loss), gradient

    def fit(self, frame: pd.DataFrame) -> "ConditionalLogit":
        if not self.feature_cols:
            raise ValueError("Informe ao menos um atributo da alternativa")
        if self.l2 < 0:
            raise ValueError("l2 não pode ser negativo")
        _validate_choice_table(frame, self.choice_cols, self.unit_col, self.chosen_col)
        matrix = self._matrix(frame, fit=True)
        chosen = frame[self.chosen_col].to_numpy(dtype=float)
        codes = _group_codes(frame, self.choice_cols)
        n_choices = int(np.unique(codes).size)
        beta = np.zeros(matrix.shape[1], dtype=float)
        loss, gradient = self._loss_gradient(beta, matrix, chosen, codes, n_choices)
        step = self.initial_step
        self.converged_ = False

        for iteration in range(1, self.max_iter + 1):
            if np.max(np.abs(gradient)) < self.tolerance:
                self.converged_ = True
                break
            direction = -gradient
            directional_derivative = float(gradient @ direction)
            trial_step = step
            for _ in range(30):
                trial_beta = beta + trial_step * direction
                trial_loss, trial_gradient = self._loss_gradient(
                    trial_beta, matrix, chosen, codes, n_choices
                )
                if trial_loss <= loss + 1e-4 * trial_step * directional_derivative:
                    break
                trial_step *= 0.5
            else:
                break
            beta, loss, gradient = trial_beta, trial_loss, trial_gradient
            step = min(trial_step * 1.5, 10.0)

        self.coefficients_ = beta
        self.n_iter_ = iteration
        self.loss_ = loss
        self.gradient_max_ = float(np.max(np.abs(gradient)))
        return self

    def predict_proba(self, frame: pd.DataFrame) -> pd.Series:
        if not hasattr(self, "coefficients_"):
            raise RuntimeError("O logit precisa ser ajustado antes da previsão")
        _validate_choice_table(frame, self.choice_cols, self.unit_col)
        matrix = self._matrix(frame, fit=False)
        probability = _softmax_by_group(
            matrix @ self.coefficients_, _group_codes(frame, self.choice_cols)
        )
        return pd.Series(probability, index=frame.index, name="predicted_probability")

    def coefficient_table(self) -> pd.DataFrame:
        if not hasattr(self, "coefficients_"):
            raise RuntimeError("O logit precisa ser ajustado antes de expor coeficientes")
        return pd.DataFrame(
            {
                "feature": list(self.feature_cols),
                "coefficient_standardized": self.coefficients_,
                "coefficient_original_scale": self.coefficients_ / self.feature_scales_,
                "training_mean": self.feature_means_,
                "training_scale": self.feature_scales_,
            }
        )

    def explain(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Decompõe a utilidade em contribuições aditivas por atributo."""
        matrix = self._matrix(frame, fit=False)
        contribution = matrix * self.coefficients_
        result = frame[[*self.choice_cols, self.unit_col]].copy()
        for position, feature in enumerate(self.feature_cols):
            result[f"contribution__{feature}"] = contribution[:, position]
        result["systematic_utility"] = contribution.sum(axis=1)
        result["predicted_probability"] = self.predict_proba(frame).to_numpy()
        return result
