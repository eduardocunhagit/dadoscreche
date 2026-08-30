"""Usa matrículas do ano anterior como proxy declarada de capacidade."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from .rotinas.normalization import normalize_code
except ImportError:
    from rotinas.normalization import normalize_code


ROOT = Path(__file__).resolve().parents[1]
OFFER = ROOT / "OferecimentosEvagas"
KEYS = ["ano", "unidade", "grupamento_norm"]

PUBLIC = {
    2023: ("totalalunoscreche2023.xlsx", "CONSOLIDADO"),
    2024: ("totalalunoscreche2024.xlsx", "Consolidado"),
    2025: ("totaalunoscreche2025.xlsx", "Consolidado"),
}
PARTNER = {
    2023: ("Parceiras2023.xlsx", "2023", 2, 2, 6, (13, 15, 17, 19)),
    2024: ("Parceiras2024.xlsx", "Maio-2024", 4, 2, 6, (14, 19, 24, 29)),
    2025: ("Parceiras2025.xlsx", "MAIO -2025", 2, 1, 2, (5, 9, 13, 17)),
}


def _long(frame, year, unit_col, name_col, cols, network, width):
    unit = normalize_code(frame.iloc[:, unit_col], width=width)
    valid = unit.str.fullmatch(r"\d+", na=False)
    numbers = frame.iloc[:, list(cols)].apply(pd.to_numeric, errors="coerce").fillna(0)
    values = {
        "BERCARIO": numbers.iloc[:, 0] + numbers.iloc[:, 1],
        "MATERNAL I": numbers.iloc[:, 2],
        "MATERNAL II": numbers.iloc[:, 3],
    }
    pieces = []
    for group, enrollment in values.items():
        pieces.append(pd.DataFrame({
            "ano": year + 1,
            "ano_matricula": year,
            "unidade": unit,
            "nome_unidade": frame.iloc[:, name_col].astype("string").str.strip(),
            "grupamento_norm": group,
            "matriculas_ano_anterior": enrollment,
            "rede": network,
        }).loc[valid])
    return pd.concat(pieces, ignore_index=True)


def construir_proxy_capacidade(base=OFFER):
    pieces = []
    for year, (filename, sheet) in PUBLIC.items():
        raw = pd.read_excel(base / filename, sheet_name=sheet, header=None)
        pieces.append(_long(raw.iloc[3:], year, 1, 2, (3, 5, 7, 9, 11, 13), "publica", 7))
    for year, (filename, sheet, start, unit, name, cols) in PARTNER.items():
        raw = pd.read_excel(base / filename, sheet_name=sheet, header=None)
        pieces.append(_long(raw.iloc[start:], year, unit, name, cols, "parceira", 5))

    result = pd.concat(pieces, ignore_index=True)
    result = (
        result.groupby(KEYS, as_index=False, observed=True)
        .agg(
            ano_matricula=("ano_matricula", "first"),
            nome_unidade=("nome_unidade", "first"),
            matriculas_ano_anterior=("matriculas_ano_anterior", "sum"),
            rede=("rede", "first"),
        )
    )
    result["matriculas_ano_anterior"] = result["matriculas_ano_anterior"].astype("int64")
    if (result["matriculas_ano_anterior"] < 0).any():
        raise ValueError("Matrículas negativas na proxy de capacidade")
    if result.duplicated(KEYS).any():
        raise ValueError("Proxy duplicada em ano × unidade × grupamento")
    result["capacity_concept"] = "matriculas_ano_anterior_proxy"
    return result.sort_values(KEYS).reset_index(drop=True)


def calcular_gap(demand, capacity, demand_col):
    missing = sorted(set(KEYS + [demand_col]) - set(demand.columns))
    if missing:
        raise ValueError(f"Colunas ausentes na demanda: {missing}")
    data = demand.copy()
    data["unidade"] = normalize_code(data["unidade"])
    dimensions = [c for c in ("draw_id", "model", "fold", "sample", "sample_segment") if c in data]
    demand_unit = (
        data.groupby([*KEYS, *dimensions], as_index=False, observed=True)[demand_col]
        .sum().rename(columns={demand_col: "demanda_prevista"})
    )
    result = demand_unit.merge(capacity, on=KEYS, how="left", validate="many_to_one")
    result["capacity_coverage"] = result["matriculas_ano_anterior"].notna()
    result["planning_gap"] = result["demanda_prevista"] - result["matriculas_ano_anterior"]
    result["gap_positivo"] = result["planning_gap"].gt(0).where(result["capacity_coverage"])
    return result


def calcular_gap_unidade(demand, capacity, demand_col):
    required = {"ano", "unidade", demand_col}
    missing = sorted(required - set(demand.columns))
    if missing:
        raise ValueError(f"Colunas ausentes na demanda: {missing}")
    data = demand.copy()
    data["unidade"] = normalize_code(data["unidade"])
    demand_unit = (
        data.groupby(["ano", "unidade"], as_index=False, observed=True)[demand_col]
        .sum().rename(columns={demand_col: "demanda_prevista"})
    )
    capacity_unit = (
        capacity.groupby(["ano", "unidade"], as_index=False, observed=True)
        .agg(
            matriculas_ano_anterior=("matriculas_ano_anterior", "sum"),
            ano_matricula=("ano_matricula", "first"),
            rede=("rede", "first"),
            capacity_concept=("capacity_concept", "first"),
        )
    )
    result = demand_unit.merge(capacity_unit, on=["ano", "unidade"], how="left", validate="one_to_one")
    result["capacity_coverage"] = result["matriculas_ano_anterior"].notna()
    result["planning_gap"] = result["demanda_prevista"] - result["matriculas_ano_anterior"]
    result["gap_positivo"] = result["planning_gap"].gt(0).where(result["capacity_coverage"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demanda", type=Path)
    parser.add_argument("--coluna-demanda", default="demanda_prevista")
    parser.add_argument("--saida-proxy", required=True, type=Path)
    parser.add_argument("--saida-gap", type=Path)
    parser.add_argument("--nivel", choices=("grupamento", "unidade"), default="grupamento")
    parser.add_argument("--ano-demanda", type=int)
    args = parser.parse_args()

    proxy = construir_proxy_capacidade()
    args.saida_proxy.parent.mkdir(parents=True, exist_ok=True)
    proxy.to_csv(args.saida_proxy, index=False)
    if args.demanda:
        if not args.saida_gap:
            parser.error("--saida-gap é obrigatório quando --demanda for informado")
        demand = pd.read_csv(args.demanda, dtype={"unidade": "string"})
        if args.ano_demanda is not None:
            demand["ano"] = args.ano_demanda
        function = calcular_gap if args.nivel == "grupamento" else calcular_gap_unidade
        gap = function(demand, proxy, args.coluna_demanda)
        args.saida_gap.parent.mkdir(parents=True, exist_ok=True)
        gap.to_csv(args.saida_gap, index=False)


if __name__ == "__main__":
    main()
