"""Demanda manifesta histórica, com denominadores declarados."""

import pandas as pd


CELL_KEYS = ("ano", "unidade", "grupamento_norm", "horario_norm")


def aggregate_historical_demand(episodes: pd.DataFrame) -> pd.DataFrame:
    """Conta primeira opção e presença na lista por unidade/grupamento/turno."""

    required = set(CELL_KEYS) | {"inscricao_id", "aluno_anon", "primeira_opcao"}
    missing = sorted(required - set(episodes.columns))
    if missing:
        raise ValueError(f"Colunas ausentes para demanda histórica: {missing}")

    listed = episodes.drop_duplicates([*CELL_KEYS, "inscricao_id"])
    totals = listed.groupby(list(CELL_KEYS), dropna=False, observed=True).agg(
        demanda_historica_lista=("inscricao_id", "nunique"),
        criancas_unicas_na_lista=("aluno_anon", "nunique"),
    )
    first = listed[listed["primeira_opcao"]].groupby(
        list(CELL_KEYS), dropna=False, observed=True
    ).agg(demanda_historica_primeira_opcao=("inscricao_id", "nunique"))

    result = totals.join(first, how="left").fillna({"demanda_historica_primeira_opcao": 0}).reset_index()
    result["demanda_historica_primeira_opcao"] = result[
        "demanda_historica_primeira_opcao"
    ].astype("int64")
    denominator = result.groupby(
        ["ano", "grupamento_norm", "horario_norm"], dropna=False, observed=True
    )["demanda_historica_primeira_opcao"].transform("sum")
    result["participacao_historica_primeira_opcao"] = (
        result["demanda_historica_primeira_opcao"].div(denominator.where(denominator.ne(0)))
    )
    return result.sort_values(list(CELL_KEYS), kind="stable").reset_index(drop=True)
