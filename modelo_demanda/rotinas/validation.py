"""Invariantes observáveis das listas de preferência."""

import pandas as pd


REGISTRATION_KEYS = ("ano", "prm_id", "plm_id", "ipl_id")


def _registration_groups(data: pd.DataFrame):
    return data.groupby(list(REGISTRATION_KEYS), dropna=False, sort=False)


def check_choice_invariants(data: pd.DataFrame, max_rank: int = 5) -> pd.DataFrame:
    """Resume violações; rank acima de cinco é aviso por existir na extração."""

    required = set(REGISTRATION_KEYS) | {"opcao", "grupamento_norm", "unidade", "horario_norm"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Colunas ausentes para validar escolhas: {missing}")

    groups = _registration_groups(data)
    first_counts = data["opcao"].eq(1).groupby(
        [data[column] for column in REGISTRATION_KEYS], dropna=False, sort=False
    ).sum()
    group_counts = groups["grupamento_norm"].nunique(dropna=False)
    rank_stats = groups["opcao"].agg(["size", "min", "max", "nunique"])
    invalid_rank = data["opcao"].isna() | data["opcao"].le(0)
    invalid_rank_groups = invalid_rank.groupby(
        [data[column] for column in REGISTRATION_KEYS], dropna=False, sort=False
    ).any()
    alternative = data["unidade"].fillna("<NA>") + "|" + data["horario_norm"].fillna("<NA>")
    unique_alternatives = data.assign(_alternative=alternative).groupby(
        list(REGISTRATION_KEYS), dropna=False, sort=False
    )["_alternative"].nunique(dropna=False)

    consecutive = (
        rank_stats["min"].eq(1)
        & rank_stats["max"].eq(rank_stats["size"])
        & rank_stats["nunique"].eq(rank_stats["size"])
    )
    rules = [
        ("uma_primeira_opcao", "error", int(first_counts.ne(1).sum())),
        ("grupamento_unico", "error", int(group_counts.ne(1).sum())),
        ("rank_inteiro_positivo", "error", int(invalid_rank_groups.sum())),
        ("rank_unico", "error", int(rank_stats["nunique"].ne(rank_stats["size"]).sum())),
        ("ranks_consecutivos_desde_um", "warning", int((~consecutive).sum())),
        (
            "alternativa_unica_na_lista",
            "warning",
            int(unique_alternatives.ne(rank_stats["size"]).sum()),
        ),
        ("rank_acima_do_limite_usual", "warning", int(groups["opcao"].max().gt(max_rank).sum())),
    ]
    return pd.DataFrame(rules, columns=["regra", "severidade", "violacoes"]).assign(
        ok=lambda frame: frame["violacoes"].eq(0)
    )


def assert_choice_invariants(data: pd.DataFrame, fail_on_warnings: bool = False) -> None:
    """Interrompe apenas em violações estruturais, salvo opção explícita."""

    report = check_choice_invariants(data)
    mask = report["violacoes"].gt(0)
    if not fail_on_warnings:
        mask &= report["severidade"].eq("error")
    if mask.any():
        failures = report.loc[mask, ["regra", "violacoes"]].to_dict("records")
        raise ValueError(f"Invariantes de escolha violados: {failures}")
