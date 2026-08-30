"""Tabela longa de opções observadas por episódio de escolha."""

import pandas as pd

from .validation import REGISTRATION_KEYS, assert_choice_invariants


def build_choice_episodes(options: pd.DataFrame, validate: bool = True) -> pd.DataFrame:
    """Cria uma linha por opção observada, sem expandir um produto cartesiano."""

    if validate:
        assert_choice_invariants(options)

    data = options.copy()
    keys = [data[column].astype("string") for column in REGISTRATION_KEYS]
    data["inscricao_id"] = keys[0].str.cat(keys[1:], sep=":")
    data["alternativa_id"] = data["unidade"].str.cat(data["horario_norm"], sep="|")
    data["rank_preferencia"] = data["opcao"].astype("Int64")
    data["primeira_opcao"] = data["rank_preferencia"].eq(1)

    columns = [
        "ano",
        "inscricao_id",
        "aluno_anon",
        "alternativa_id",
        "unidade",
        "nome_unidade",
        "nome_unidade_norm",
        "grupamento_norm",
        "horario_norm",
        "rank_preferencia",
        "primeira_opcao",
        "data_criacao",
        "CEP",
        "bairro_norm",
        "sexo_crianca_norm",
        "nascimento_aluno_anomes",
    ]
    return data.loc[:, columns].sort_values(
        ["ano", "inscricao_id", "rank_preferencia"], kind="stable"
    ).reset_index(drop=True)
