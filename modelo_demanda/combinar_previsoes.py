"""Combina o total previsto por território com participações por creche e turno."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASE_KEYS = ["ano", "origin_area", "grupamento_norm"]
TOTAL_REQUIRED = [*BASE_KEYS, "inscricoes_previstas"]
SHARE_REQUIRED = [
    *BASE_KEYS, "alternativa_id", "unidade", "horario_norm", "choice_share"
]


def integrar(totais: pd.DataFrame, participacoes: pd.DataFrame) -> pd.DataFrame:
    missing_totals = sorted(set(TOTAL_REQUIRED) - set(totais.columns))
    missing_shares = sorted(set(SHARE_REQUIRED) - set(participacoes.columns))
    if missing_totals or missing_shares:
        raise ValueError(
            f"Colunas ausentes: totais={missing_totals}; participações={missing_shares}"
        )

    draw_keys = ["draw_id"] if "draw_id" in totais.columns else []
    total_keys = [*BASE_KEYS, *draw_keys]
    if totais.duplicated(total_keys).any():
        raise ValueError("Os totais devem ter uma linha por célula e draw_id")
    if participacoes.duplicated([*BASE_KEYS, "alternativa_id"]).any():
        raise ValueError("Há alternativa duplicada na mesma célula")
    if totais[TOTAL_REQUIRED].isna().any().any() or participacoes[SHARE_REQUIRED].isna().any().any():
        raise ValueError("Chaves e previsões não podem ser nulas")
    if (totais["inscricoes_previstas"] < 0).any():
        raise ValueError("inscricoes_previstas deve ser não negativa")
    if ((participacoes["choice_share"] < 0) | (participacoes["choice_share"] > 1)).any():
        raise ValueError("choice_share deve estar entre zero e um")

    share_sum = participacoes.groupby(BASE_KEYS, observed=True)["choice_share"].sum()
    if not np.allclose(share_sum.to_numpy(), 1.0, atol=1e-8):
        raise ValueError("As participações devem somar um em cada célula")

    result = totais.merge(participacoes, on=BASE_KEYS, how="left", validate="one_to_many")
    if result["alternativa_id"].isna().any():
        missing = result.loc[result["alternativa_id"].isna(), BASE_KEYS].drop_duplicates()
        raise ValueError(f"Células sem participação prevista: {len(missing)}")
    result["demanda_prevista"] = result["inscricoes_previstas"] * result["choice_share"]

    integrated = result.groupby(total_keys, observed=True)["demanda_prevista"].sum().sort_index()
    expected = totais.set_index(total_keys)["inscricoes_previstas"].sort_index()
    if not np.allclose(integrated.to_numpy(), expected.to_numpy(), atol=1e-8):
        raise AssertionError("A projeção não conservou o total previsto")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--totais", required=True, type=Path)
    parser.add_argument("--participacoes", required=True, type=Path)
    parser.add_argument("--saida", required=True, type=Path)
    args = parser.parse_args()
    result = integrar(pd.read_csv(args.totais), pd.read_csv(args.participacoes))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.saida, index=False)


if __name__ == "__main__":
    main()