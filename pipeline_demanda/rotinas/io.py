"""Leitura e tipagem da Query A sem modificar o arquivo bruto."""

from pathlib import Path

import pandas as pd

from .normalization import normalize_code, normalize_text


QUERY_A_COLUMNS = (
    "ano",
    "prm_id",
    "plm_id",
    "ipl_id",
    "opcao",
    "unidade",
    "nome_unidade",
    "grupamento",
    "horario",
    "data_criacao",
    "aluno_anon",
    "sexo_crianca",
    "nascimento_aluno_anomes",
    "responsavel_anon",
    "CEP",
    "bairro",
    "situacao",
)

INTEGER_COLUMNS = ("ano", "prm_id", "plm_id", "ipl_id", "opcao")
TEXT_COLUMNS = (
    "nome_unidade",
    "grupamento",
    "horario",
    "sexo_crianca",
    "bairro",
    "situacao",
)


def prepare_query_a(raw: pd.DataFrame) -> pd.DataFrame:
    """Valida o esquema e devolve a Query A em tipos analíticos canônicos."""

    missing = sorted(set(QUERY_A_COLUMNS) - set(raw.columns))
    if missing:
        raise ValueError(f"Colunas ausentes na Query A: {missing}")

    data = raw.loc[:, QUERY_A_COLUMNS].copy()
    for column in INTEGER_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="raise").astype("Int64")

    original_dates = data["data_criacao"].notna()
    data["data_criacao"] = pd.to_datetime(data["data_criacao"], errors="coerce")
    if (original_dates & data["data_criacao"].isna()).any():
        raise ValueError("data_criacao contém valores não interpretáveis")

    data["unidade"] = normalize_code(data["unidade"])
    data["CEP"] = normalize_code(data["CEP"], width=8)
    for column in ("aluno_anon", "responsavel_anon", "nascimento_aluno_anomes"):
        data[column] = data[column].astype("string").str.strip()
    for column in TEXT_COLUMNS:
        data[f"{column}_norm"] = normalize_text(data[column])

    return data


def load_query_a(path: str | Path, years: tuple[int, ...] | None = None) -> pd.DataFrame:
    """Lê o CSV ou CSV.GZ oficial; o filtro anual ocorre após a tipagem."""

    raw = pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        dtype="string",
        na_values=["NULL"],
        keep_default_na=True,
    )
    data = prepare_query_a(raw)
    if years is not None:
        data = data[data["ano"].isin(years)].copy()
    return data.reset_index(drop=True)
