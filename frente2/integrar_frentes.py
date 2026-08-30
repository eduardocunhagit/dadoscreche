"""Combina totais previstos pela Frente 1 com participações da Frente 2."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BASE_KEYS = ["ano", "origin_area", "grupamento_norm"]
F1_REQUIRED = [*BASE_KEYS, "inscricoes_previstas"]
F2_REQUIRED = [
    *BASE_KEYS,
    "alternativa_id",
    "unidade",
    "horario_norm",
    "choice_share",
]


def integrar(frente1: pd.DataFrame, frente2: pd.DataFrame) -> pd.DataFrame:
    missing_f1 = sorted(set(F1_REQUIRED) - set(frente1.columns))
    missing_f2 = sorted(set(F2_REQUIRED) - set(frente2.columns))
    if missing_f1 or missing_f2:
        raise ValueError(f"Colunas ausentes: frente1={missing_f1}; frente2={missing_f2}")

    draw_keys = ["draw_id"] if "draw_id" in frente1.columns else []
    f1_keys = [*BASE_KEYS, *draw_keys]
    if frente1.duplicated(f1_keys).any():
        raise ValueError("A Frente 1 deve ter uma linha por célula e draw_id")
    if frente2.duplicated([*BASE_KEYS, "alternativa_id"]).any():
        raise ValueError("A Frente 2 contém alternativa duplicada na célula")
    if frente1[F1_REQUIRED].isna().any().any() or frente2[F2_REQUIRED].isna().any().any():
        raise ValueError("As chaves e previsões não podem ser nulas")
    if (frente1["inscricoes_previstas"] < 0).any():
        raise ValueError("inscricoes_previstas deve ser não negativa")
    if ((frente2["choice_share"] < 0) | (frente2["choice_share"] > 1)).any():
        raise ValueError("choice_share deve estar entre zero e um")

    share_sum = frente2.groupby(BASE_KEYS, observed=True)["choice_share"].sum()
    if not np.allclose(share_sum.to_numpy(), 1.0, atol=1e-8):
        raise ValueError("As participações da Frente 2 devem somar um por célula")

    result = frente1.merge(frente2, on=BASE_KEYS, how="left", validate="one_to_many")
    if result["alternativa_id"].isna().any():
        missing = result.loc[result["alternativa_id"].isna(), BASE_KEYS].drop_duplicates()
        raise ValueError(f"Células da Frente 1 sem participação da Frente 2: {len(missing)}")
    result["demanda_prevista"] = result["inscricoes_previstas"] * result["choice_share"]

    integrated = result.groupby(f1_keys, observed=True)["demanda_prevista"].sum().sort_index()
    expected = frente1.set_index(f1_keys)["inscricoes_previstas"].sort_index()
    if not np.allclose(integrated.to_numpy(), expected.to_numpy(), atol=1e-8):
        raise AssertionError("A integração não conservou o total previsto pela Frente 1")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frente1", required=True, type=Path)
    parser.add_argument("--frente2", required=True, type=Path)
    parser.add_argument("--saida", required=True, type=Path)
    args = parser.parse_args()
    result = integrar(pd.read_csv(args.frente1), pd.read_csv(args.frente2))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.saida, index=False)


if __name__ == "__main__":
    main()
