"""Concorrência revelada pela co-listagem histórica de unidades."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Sequence

import numpy as np
import pandas as pd


def _segment_tuple(value: object, size: int) -> tuple:
    if size == 0:
        return ()
    if size == 1:
        return (value,)
    return tuple(value)


def build_colisting_network(
    lists: pd.DataFrame,
    list_col: str = "choice_id",
    unit_col: str = "unit_id",
    segment_cols: Sequence[str] = (),
) -> pd.DataFrame:
    """Calcula omega_ij = n_ij / sqrt(n_i n_j) em listas do treino."""
    required = [*segment_cols, list_col, unit_col]
    missing = sorted(set(required) - set(lists.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    if lists[required].isna().any().any():
        raise ValueError("Chaves da rede de co-listagem não podem ser nulas")

    unique = lists[required].drop_duplicates()
    unit_counts: Counter = Counter()
    pair_counts: Counter = Counter()
    group_cols = [*segment_cols, list_col]
    grouper = group_cols[0] if len(group_cols) == 1 else group_cols
    for group_key, group in unique.groupby(grouper, sort=False):
        key = group_key if isinstance(group_key, tuple) else (group_key,)
        segment = key[:-1]
        units = sorted(group[unit_col].unique().tolist(), key=str)
        unit_counts.update((segment, unit) for unit in units)
        pair_counts.update((segment, left, right) for left, right in combinations(units, 2))

    rows = []
    for key, n_ij in pair_counts.items():
        segment, left, right = key[0], key[1], key[2]
        n_i = unit_counts[(segment, left)]
        n_j = unit_counts[(segment, right)]
        row = {column: segment[pos] for pos, column in enumerate(segment_cols)}
        row.update(
            {
                "unit_i": left,
                "unit_j": right,
                "n_i": n_i,
                "n_j": n_j,
                "n_ij": n_ij,
                "omega": n_ij / np.sqrt(n_i * n_j),
            }
        )
        rows.append(row)
    columns = [*segment_cols, "unit_i", "unit_j", "n_i", "n_j", "n_ij", "omega"]
    return pd.DataFrame(rows, columns=columns)


def colisting_competition(
    network: pd.DataFrame,
    capacity: pd.DataFrame,
    unit_col: str = "unit_id",
    capacity_col: str = "capacity_ex_ante",
    segment_cols: Sequence[str] = (),
) -> pd.DataFrame:
    """Soma omega_ij vezes a capacidade ex ante da unidade concorrente j."""
    capacity_keys = [*segment_cols, unit_col]
    required_network = [*segment_cols, "unit_i", "unit_j", "omega"]
    missing = sorted(
        (set(capacity_keys + [capacity_col]) - set(capacity.columns))
        | (set(required_network) - set(network.columns))
    )
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    if capacity.duplicated(capacity_keys).any():
        raise ValueError("Capacidade deve ser única por unidade e segmento")
    if (capacity[capacity_col] < 0).any() or capacity[capacity_col].isna().any():
        raise ValueError("Capacidade ex ante deve ser não negativa e observada")

    reverse = network.rename(columns={"unit_i": "unit_j", "unit_j": "unit_i"})
    directed = pd.concat([network, reverse], ignore_index=True)
    competitor_capacity = capacity.rename(
        columns={unit_col: "unit_j", capacity_col: "_competitor_capacity"}
    )
    directed = directed.merge(
        competitor_capacity[[*segment_cols, "unit_j", "_competitor_capacity"]],
        on=[*segment_cols, "unit_j"],
        how="left",
        validate="many_to_one",
    )
    if directed["_competitor_capacity"].isna().any():
        raise ValueError("Há concorrentes sem capacidade ex ante")
    directed["_weighted_capacity"] = directed["omega"] * directed["_competitor_capacity"]
    summary = (
        directed.groupby([*segment_cols, "unit_i"], as_index=False)
        .agg(
            competition_colisting=("_weighted_capacity", "sum"),
            colisting_weight_sum=("omega", "sum"),
        )
        .rename(columns={"unit_i": unit_col})
    )
    base = capacity[capacity_keys].copy()
    result = base.merge(summary, on=capacity_keys, how="left", validate="one_to_one")
    result[["competition_colisting", "colisting_weight_sum"]] = result[
        ["competition_colisting", "colisting_weight_sum"]
    ].fillna(0.0)
    return result
