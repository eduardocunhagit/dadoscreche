"""Folds temporais fixados antes da estimação."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TemporalFold:
    name: str
    train_years: tuple[int, ...]
    test_year: int

    def __post_init__(self) -> None:
        if not self.train_years or max(self.train_years) >= self.test_year:
            raise ValueError("Todo ano de treino deve anteceder o ano de teste")


STANDARD_FOLDS = (
    TemporalFold("oos_2024", (2021, 2022, 2023), 2024),
    TemporalFold("oos_2025", (2021, 2022, 2023, 2024), 2025),
)


def split_temporal(data: pd.DataFrame, fold: TemporalFold) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa treino e teste sem usar observações futuras no treino."""

    if "ano" not in data:
        raise ValueError("A coluna ano é obrigatória para o split temporal")
    train = data[data["ano"].isin(fold.train_years)].copy()
    test = data[data["ano"].eq(fold.test_year)].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)
