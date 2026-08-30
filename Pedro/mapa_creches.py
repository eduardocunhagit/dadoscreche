from __future__ import annotations

import html
import json
import math
import re
import unicodedata
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from branca.element import Element
from folium.plugins import Fullscreen, HeatMap


REFERENCE_YEAR = 2025
REPOSITORY_ROOT = Path(r"C:\Users\pedro\Documents\2026\ClaudeImpactLab2")
PEDRO_DIR = REPOSITORY_ROOT / "Pedro"
OUTPUT_DIR = PEDRO_DIR / "output"

LOCATION_FILE = (
    REPOSITORY_ROOT
    / "OferecimentosEvagas"
    / "Unidades_Unificadas_com_Localizacao.xlsx"
)
PUBLIC_ENROLLMENT_FILE = (
    REPOSITORY_ROOT / "OferecimentosEvagas" / "totaalunoscreche2025.xlsx"
)
PARTNER_ENROLLMENT_FILE = (
    REPOSITORY_ROOT / "OferecimentosEvagas" / "Parceiras2025.xlsx"
)
APPLICATION_FILE = (
    REPOSITORY_ROOT
    / "Bases IC_ ClassificadoseFila"
    / "01_QueryA_InscricoesPorAno.csv.gz"
)
MICROAREA_FILE = (
    REPOSITORY_ROOT
    / "Microáreas_SME_revisãoIPP"
    / "Microareas_SME_revisao.shp"
)

MAP_FILE = OUTPUT_DIR / "mapa_creches_2025.html"
PANEL_FILE = OUTPUT_DIR / "creches_2025.csv"
UNMATCHED_FILE = OUTPUT_DIR / "creches_sem_coord_2025.csv"
SUMMARY_FILE = OUTPUT_DIR / "resumo_mapa_2025.json"
PREDICTED_DEMAND_FILE = PEDRO_DIR / "Modelo" / "results" / "f2_prev_unidade.csv"


def normalize_code(series: pd.Series) -> pd.Series:
    """Standardize school codes across numeric and text source formats."""
    values = series.astype("string").str.strip()
    values = values.str.replace(r"\.0$", "", regex=True)
    values = values.str.replace(r"\D", "", regex=True)
    values = values.str.lstrip("0")
    return values.mask(values.eq(""))


def normalize_name(value: object) -> str | None:
    """Create an accent-free name key for diagnostics and future crosswalks."""
    if pd.isna(value):
        return None
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", ascii_text.upper()).strip()


def to_numeric(series: pd.Series) -> pd.Series:
    """Convert spreadsheet cells to numbers while treating blanks as zero."""
    return pd.to_numeric(series, errors="coerce").fillna(0)


def first_non_null(series: pd.Series) -> object:
    """Return the first observed value when consolidating duplicate rows."""
    observed = series.dropna()
    return observed.iloc[0] if not observed.empty else pd.NA


def load_locations() -> pd.DataFrame:
    """Load the unified school registry and validate Rio coordinates."""
    locations = pd.read_excel(
        LOCATION_FILE,
        sheet_name="Unidades_Unificadas",
    ).copy()
    locations["codigo"] = normalize_code(locations["DESIGNACAO"])
    locations["nome_norm"] = locations["DENOMINACAO"].map(normalize_name)
    locations["coord_valida"] = (
        locations["LATITUDE"].between(-24, -20)
        & locations["LONGITUDE"].between(-46, -40)
    )

    if locations["codigo"].duplicated().any():
        duplicate_codes = locations.loc[
            locations["codigo"].duplicated(keep=False), "codigo"
        ].tolist()
        raise ValueError(f"Duplicate location codes: {duplicate_codes[:10]}")

    return locations.rename(
        columns={
            "DENOMINACAO": "nome_localizacao",
            "CRE": "cre_localizacao",
            "microárea": "microarea",
            "RUA": "endereco",
            "BAIRRO": "bairro",
            "LATITUDE": "latitude",
            "LONGITUDE": "longitude",
            "Tipo": "tipo_unidade",
        }
    )


def load_public_enrollment() -> pd.DataFrame:
    """Aggregate 2025 public enrollment by comparable age group."""
    public = pd.read_excel(
        PUBLIC_ENROLLMENT_FILE,
        sheet_name="Consolidado",
        header=2,
    ).copy()
    public["codigo"] = normalize_code(public["Designacao"])
    public = public.loc[public["codigo"].notna()].copy()

    # Public reports split each age group between integral and partial schedules.
    public["mat_bercario"] = to_numeric(public["Aluno"]) + to_numeric(
        public["Aluno.1"]
    )
    public["mat_maternal_1"] = to_numeric(public["Aluno.2"]) + to_numeric(
        public["Aluno.3"]
    )
    public["mat_maternal_2"] = to_numeric(public["Aluno.4"]) + to_numeric(
        public["Aluno.5"]
    )
    public["matriculas_total"] = to_numeric(public["Aluno.6"]) + to_numeric(
        public["Aluno.7"]
    )
    public["turmas_total"] = to_numeric(public["Turma.6"]) + to_numeric(
        public["Turma.7"]
    )
    public["cre_publica"] = public["Rótulos de Linha"].astype("string")
    public["fonte_publica"] = True

    columns = [
        "codigo",
        "Denominacao",
        "cre_publica",
        "mat_bercario",
        "mat_maternal_1",
        "mat_maternal_2",
        "matriculas_total",
        "turmas_total",
        "fonte_publica",
    ]
    public = public[columns].rename(columns={"Denominacao": "nome_publica"})

    aggregations = {
        "nome_publica": first_non_null,
        "cre_publica": first_non_null,
        "mat_bercario": "sum",
        "mat_maternal_1": "sum",
        "mat_maternal_2": "sum",
        "matriculas_total": "sum",
        "turmas_total": "sum",
        "fonte_publica": "max",
    }
    return public.groupby("codigo", as_index=False).agg(aggregations)


def load_partner_enrollment() -> pd.DataFrame:
    """Aggregate the May 2025 partner-school monitoring report."""
    partners = pd.read_excel(
        PARTNER_ENROLLMENT_FILE,
        sheet_name="MAIO -2025",
        header=1,
    ).copy()
    partners["codigo"] = normalize_code(partners["CÓDIGO SGA"])
    partners = partners.loc[partners["codigo"].notna()].copy()

    # Partner reports separate Berçário I and II; they are combined for
    # comparability with the public-school Berçário grouping.
    partners["mat_bercario"] = to_numeric(partners["Aluno"]) + to_numeric(
        partners["Aluno.1"]
    )
    partners["mat_maternal_1"] = to_numeric(partners["Aluno.2"])
    partners["mat_maternal_2"] = to_numeric(partners["Aluno.3"])
    partners["matriculas_total"] = to_numeric(partners["Total Alunos"])
    partners["capacidade_meta"] = to_numeric(partners["Meta Total"])
    partners["vagas_reportadas"] = to_numeric(partners["Vagas.4"])
    partners["cre_parceira"] = partners["CRE"].astype("string")
    partners["fonte_parceira"] = True

    columns = [
        "codigo",
        "Denominação SGA",
        "cre_parceira",
        "mat_bercario",
        "mat_maternal_1",
        "mat_maternal_2",
        "matriculas_total",
        "capacidade_meta",
        "vagas_reportadas",
        "fonte_parceira",
    ]
    partners = partners[columns].rename(
        columns={"Denominação SGA": "nome_parceira"}
    )

    aggregations = {
        "nome_parceira": first_non_null,
        "cre_parceira": first_non_null,
        "mat_bercario": "sum",
        "mat_maternal_1": "sum",
        "mat_maternal_2": "sum",
        "matriculas_total": "sum",
        "capacidade_meta": "sum",
        "vagas_reportadas": "sum",
        "fonte_parceira": "max",
    }
    return partners.groupby("codigo", as_index=False).agg(aggregations)


def load_application_metrics() -> pd.DataFrame:
    """Count historical demand and waitlist pressure for each unit in 2025.

    Historical demand counts a child once in every unit selected in any option. Repeated
    rows inside the same child-unit pair are removed, while selections of other units are
    preserved. This is the operational benchmark for future unit-demand forecasts.
    """
    use_columns = [
        "ano",
        "unidade",
        "nome_unidade",
        "grupamento",
        "aluno_anon",
        "situacao",
    ]
    applications = pd.read_csv(
        APPLICATION_FILE,
        sep=";",
        encoding="utf-8-sig",
        compression="gzip",
        usecols=use_columns,
        low_memory=False,
    )
    applications = applications.loc[applications["ano"].eq(REFERENCE_YEAR)].copy()
    applications["codigo"] = normalize_code(applications["unidade"])
    applications["grupamento_limpo"] = applications["grupamento"].str.strip()

    group_map = {
        "Berçário": "bercario",
        "Maternal I": "maternal_1",
        "Maternal II": "maternal_2",
    }
    applications["grupo_mapa"] = applications["grupamento_limpo"].map(group_map)

    historical_total = (
        applications.drop_duplicates(["codigo", "aluno_anon"])
        .groupby("codigo")["aluno_anon"]
        .nunique()
        .rename("demanda_historica")
    )
    historical_by_group = (
        applications.dropna(subset=["grupo_mapa"])
        .drop_duplicates(["codigo", "aluno_anon", "grupo_mapa"])
        .groupby(["codigo", "grupo_mapa"])["aluno_anon"]
        .nunique()
        .unstack(fill_value=0)
        .rename(
            columns={
                "bercario": "demanda_hist_bercario",
                "maternal_1": "demanda_hist_maternal_1",
                "maternal_2": "demanda_hist_maternal_2",
            }
        )
    )

    waiting = applications.loc[applications["situacao"].eq("Lista de espera")].copy()

    # A child can select several units. Counting distinct child-unit pairs
    # measures the queue faced by each unit without double-counting duplicates.
    total_wait = (
        waiting.drop_duplicates(["codigo", "aluno_anon"])
        .groupby("codigo")["aluno_anon"]
        .nunique()
        .rename("fila_total")
    )
    wait_by_group = (
        waiting.dropna(subset=["grupo_mapa"])
        .drop_duplicates(["codigo", "aluno_anon", "grupo_mapa"])
        .groupby(["codigo", "grupo_mapa"])["aluno_anon"]
        .nunique()
        .unstack(fill_value=0)
        .rename(
            columns={
                "bercario": "fila_bercario",
                "maternal_1": "fila_maternal_1",
                "maternal_2": "fila_maternal_2",
            }
        )
    )
    wait_names = applications.groupby("codigo")["nome_unidade"].agg(first_non_null)

    metrics = pd.concat(
        [wait_names, historical_total, historical_by_group, total_wait, wait_by_group],
        axis=1,
    ).reset_index()
    expected_columns = (
        "demanda_hist_bercario",
        "demanda_hist_maternal_1",
        "demanda_hist_maternal_2",
        "fila_bercario",
        "fila_maternal_1",
        "fila_maternal_2",
    )
    for column in expected_columns:
        if column not in metrics.columns:
            metrics[column] = 0
    return metrics.rename(columns={"nome_unidade": "nome_inscricao"})


def load_predicted_demand() -> pd.DataFrame:
    """Load optional Front 1, Front 2, uncertainty, and lagged-capacity outputs.

    Confidence limits must already describe the unit-level effective-demand distribution.
    They are not mechanically summed across age groups because quantiles are not additive.
    """
    output_columns = [
        "codigo",
        "ano_previsao",
        "demanda_prevista_inscritos",
        "demanda_prevista_efetiva",
        "demanda_efetiva_p025",
        "demanda_efetiva_p975",
        "capacidade_ano_anterior",
    ]
    empty = pd.DataFrame(columns=output_columns)
    if not PREDICTED_DEMAND_FILE.exists():
        return empty

    forecast = pd.read_csv(PREDICTED_DEMAND_FILE, low_memory=False)
    code_candidates = ["codigo_unidade", "codigo", "unidade"]
    code_column = next((column for column in code_candidates if column in forecast), None)
    if code_column is None:
        raise ValueError(
            f"{PREDICTED_DEMAND_FILE.name} must contain codigo_unidade, codigo, or unidade."
        )

    forecast["codigo"] = normalize_code(forecast[code_column])
    aliases = {
        "demanda_prevista_inscritos": [
            "demanda_prevista_inscritos",
            "prev_f1",
            "f1_prev",
            "a_hat",
        ],
        "demanda_prevista_efetiva": [
            "demanda_prevista_efetiva",
            "demanda_prevista",
            "prev_f2",
            "d_hat",
            "prev_modelo",
        ],
        "demanda_efetiva_p025": [
            "demanda_efetiva_p025",
            "f2_p025",
            "limite_95_inf",
            "p025",
        ],
        "demanda_efetiva_p975": [
            "demanda_efetiva_p975",
            "f2_p975",
            "limite_95_sup",
            "p975",
        ],
        "capacidade_ano_anterior": [
            "capacidade_ano_anterior",
            "capacidade_t_1",
            "capacidade_2025",
        ],
    }
    available_targets = []
    for target, candidates in aliases.items():
        source = next((column for column in candidates if column in forecast), None)
        if source is None:
            forecast[target] = np.nan
        else:
            forecast[target] = pd.to_numeric(forecast[source], errors="coerce")
            available_targets.append(target)
    if not available_targets:
        raise ValueError(
            f"{PREDICTED_DEMAND_FILE.name} does not contain a recognized forecast field."
        )
    year_column = next(
        (column for column in ["ano_previsao", "ano", "ano_teste"] if column in forecast),
        None,
    )
    if year_column is not None:
        forecast["ano_previsao"] = pd.to_numeric(forecast[year_column], errors="coerce")
        latest_year = forecast["ano_previsao"].max()
        forecast = forecast.loc[forecast["ano_previsao"].eq(latest_year)].copy()
    else:
        forecast["ano_previsao"] = pd.NA

    forecast = forecast.dropna(subset=["codigo"])
    duplicate_units = forecast["codigo"].duplicated(keep=False)
    has_interval = forecast[["demanda_efetiva_p025", "demanda_efetiva_p975"]].notna().any().any()
    if duplicate_units.any() and has_interval:
        raise ValueError(
            "The forecast file has repeated units and confidence limits. Export one row per "
            "unit with uncertainty aggregated from the joint predictive distribution."
        )

    if duplicate_units.any():
        aggregations = {column: "sum" for column in aliases}
        aggregations["ano_previsao"] = first_non_null
        forecast = forecast.groupby("codigo", as_index=False).agg(aggregations)
    else:
        forecast = forecast[output_columns].copy()
    return forecast[output_columns]


def combine_enrollment(
    public: pd.DataFrame,
    partners: pd.DataFrame,
) -> pd.DataFrame:
    """Create one enrollment record per code across both provider types."""
    numeric_columns = [
        "mat_bercario",
        "mat_maternal_1",
        "mat_maternal_2",
        "matriculas_total",
        "turmas_total",
        "capacidade_meta",
        "vagas_reportadas",
    ]
    combined = public.merge(partners, on="codigo", how="outer", suffixes=("_pub", "_par"))

    for column in ("mat_bercario", "mat_maternal_1", "mat_maternal_2", "matriculas_total"):
        combined[column] = combined.get(f"{column}_pub", 0).fillna(0) + combined.get(
            f"{column}_par", 0
        ).fillna(0)

    combined["turmas_total"] = combined.get("turmas_total", 0).fillna(0)
    combined["capacidade_meta"] = combined.get("capacidade_meta", 0).fillna(0)
    combined["vagas_reportadas"] = combined.get("vagas_reportadas", 0).fillna(0)
    combined["fonte_publica"] = combined.get(
        "fonte_publica", pd.Series(False, index=combined.index)
    ).eq(True)
    combined["fonte_parceira"] = combined.get(
        "fonte_parceira", pd.Series(False, index=combined.index)
    ).eq(True)

    combined["nome_oferta"] = combined["nome_publica"].combine_first(
        combined["nome_parceira"]
    )
    combined["cre_oferta"] = combined["cre_publica"].combine_first(
        combined["cre_parceira"]
    )
    combined["tipo_oferta"] = np.select(
        [
            combined["fonte_publica"] & combined["fonte_parceira"],
            combined["fonte_parceira"],
            combined["fonte_publica"],
        ],
        ["Pública e parceira", "Parceira", "Pública"],
        default="Sem oferta identificada",
    )

    keep_columns = [
        "codigo",
        "nome_oferta",
        "cre_oferta",
        "tipo_oferta",
        *numeric_columns,
    ]
    return combined[keep_columns]


def classify_queue_pressure(row: pd.Series) -> str:
    """Create a descriptive queue ratio, not a causal priority score."""
    enrollment = row["matriculas_total"]
    waitlist = row["fila_total"]
    if waitlist <= 0:
        return "Sem fila observada"
    if enrollment <= 0:
        return "Com fila e sem matrícula observada"
    ratio = 100 * waitlist / enrollment
    if ratio < 25:
        return "Até 25 por 100 matriculados"
    if ratio < 75:
        return "25 a 75 por 100 matriculados"
    return "Mais de 75 por 100 matriculados"


def build_panel() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Build the 2025 unit panel and data-quality summary."""
    locations = load_locations()
    public = load_public_enrollment()
    partners = load_partner_enrollment()
    application_metrics = load_application_metrics()
    predicted_demand = load_predicted_demand()
    enrollment = combine_enrollment(public, partners)

    panel = enrollment.merge(application_metrics, on="codigo", how="outer")
    panel = panel.merge(predicted_demand, on="codigo", how="left")
    panel["tipo_oferta"] = panel["tipo_oferta"].fillna("Somente inscrição")
    numeric_columns = [
        "mat_bercario",
        "mat_maternal_1",
        "mat_maternal_2",
        "matriculas_total",
        "turmas_total",
        "capacidade_meta",
        "vagas_reportadas",
        "demanda_historica",
        "demanda_hist_bercario",
        "demanda_hist_maternal_1",
        "demanda_hist_maternal_2",
        "fila_bercario",
        "fila_maternal_1",
        "fila_maternal_2",
        "fila_total",
    ]
    for column in numeric_columns:
        panel[column] = to_numeric(panel[column])

    # Public files contain many schools without creche enrollment. Keep only
    # observed creche activity: enrollment, a 2025 partner record, or a queue.
    active_mask = (
        panel["matriculas_total"].gt(0)
        | panel["demanda_historica"].gt(0)
        | panel["fila_total"].gt(0)
        | panel["tipo_oferta"].isin(["Parceira", "Pública e parceira"])
    )
    panel = panel.loc[active_mask].copy()
    panel = panel.merge(
        locations[
            [
                "codigo",
                "nome_localizacao",
                "cre_localizacao",
                "microarea",
                "endereco",
                "bairro",
                "latitude",
                "longitude",
                "tipo_unidade",
                "coord_valida",
            ]
        ],
        on="codigo",
        how="left",
    )

    panel["nome"] = (
        panel["nome_localizacao"]
        .combine_first(panel["nome_oferta"])
        .combine_first(panel["nome_inscricao"])
    )
    panel["cre"] = panel["cre_localizacao"].combine_first(panel["cre_oferta"])
    panel["ano_referencia"] = REFERENCE_YEAR
    panel["referencia_matriculas"] = np.where(
        panel["tipo_oferta"].eq("Parceira"),
        "Maio de 2025",
        "Consolidado público de 2025",
    )
    panel.loc[
        panel["tipo_oferta"].eq("Somente inscrição"),
        "referencia_matriculas",
    ] = "Sem matrícula localizada"
    panel["fila_por_100_matriculas"] = np.where(
        panel["matriculas_total"].gt(0),
        100 * panel["fila_total"] / panel["matriculas_total"],
        np.nan,
    )
    panel["classe_pressao_fila"] = panel.apply(classify_queue_pressure, axis=1)
    panel["demanda_hist_por_100_matriculas"] = np.where(
        panel["matriculas_total"].gt(0),
        100 * panel["demanda_historica"] / panel["matriculas_total"],
        np.nan,
    )

    # The policy outcome compares effective predicted demand with capacity known before
    # the forecast year. Enrollment is not silently substituted for missing capacity.
    complete_pressure = panel["demanda_prevista_efetiva"].notna() & panel[
        "capacidade_ano_anterior"
    ].notna()
    panel["gap_pressao_efetiva"] = np.where(
        complete_pressure,
        panel["demanda_prevista_efetiva"] - panel["capacidade_ano_anterior"],
        np.nan,
    )
    panel["gap_pressao_p025"] = np.where(
        panel["demanda_efetiva_p025"].notna()
        & panel["capacidade_ano_anterior"].notna(),
        panel["demanda_efetiva_p025"] - panel["capacidade_ano_anterior"],
        np.nan,
    )
    panel["gap_pressao_p975"] = np.where(
        panel["demanda_efetiva_p975"].notna()
        & panel["capacidade_ano_anterior"].notna(),
        panel["demanda_efetiva_p975"] - panel["capacidade_ano_anterior"],
        np.nan,
    )
    panel["gap_significativo_95"] = np.where(
        panel["gap_pressao_p025"].notna() & panel["gap_pressao_p975"].notna(),
        (panel["gap_pressao_p025"] > 0) | (panel["gap_pressao_p975"] < 0),
        pd.NA,
    )
    panel["prioridade_modelo"] = pd.Series(pd.NA, index=panel.index, dtype="string")

    valid_coordinate = panel["coord_valida"].eq(True)
    unmatched = panel.loc[~valid_coordinate].copy()
    located = panel.loc[valid_coordinate].copy()

    export_columns = [
        "ano_referencia",
        "codigo",
        "nome",
        "tipo_oferta",
        "tipo_unidade",
        "cre",
        "microarea",
        "endereco",
        "bairro",
        "latitude",
        "longitude",
        "matriculas_total",
        "mat_bercario",
        "mat_maternal_1",
        "mat_maternal_2",
        "turmas_total",
        "capacidade_meta",
        "vagas_reportadas",
        "demanda_historica",
        "demanda_hist_bercario",
        "demanda_hist_maternal_1",
        "demanda_hist_maternal_2",
        "demanda_hist_por_100_matriculas",
        "fila_total",
        "fila_bercario",
        "fila_maternal_1",
        "fila_maternal_2",
        "fila_por_100_matriculas",
        "classe_pressao_fila",
        "referencia_matriculas",
        "demanda_prevista_inscritos",
        "demanda_prevista_efetiva",
        "demanda_efetiva_p025",
        "demanda_efetiva_p975",
        "ano_previsao",
        "capacidade_ano_anterior",
        "gap_pressao_efetiva",
        "gap_pressao_p025",
        "gap_pressao_p975",
        "gap_significativo_95",
        "prioridade_modelo",
    ]
    located = located[export_columns].sort_values(
        ["demanda_historica", "fila_total"], ascending=False
    )
    unmatched = unmatched[export_columns].sort_values(
        ["demanda_historica", "fila_total"], ascending=False
    )

    try:
        forecast_file_reference = str(PREDICTED_DEMAND_FILE.relative_to(REPOSITORY_ROOT))
    except ValueError:
        forecast_file_reference = str(PREDICTED_DEMAND_FILE)

    summary = {
        "ano_referencia": REFERENCE_YEAR,
        "unidades_no_painel": int(len(panel)),
        "unidades_mapeadas": int(len(located)),
        "unidades_sem_coordenada": int(len(unmatched)),
        "matriculas_mapeadas": int(located["matriculas_total"].sum()),
        "demanda_historica_mapeada_pares_crianca_unidade": int(
            located["demanda_historica"].sum()
        ),
        "criancas_em_fila_mapeadas_por_unidade": int(located["fila_total"].sum()),
        "unidades_com_fila": int(located["fila_total"].gt(0).sum()),
        "f1_disponivel": bool(located["demanda_prevista_inscritos"].notna().any()),
        "f2_disponivel": bool(located["demanda_prevista_efetiva"].notna().any()),
        "pressao_prevista_disponivel": bool(located["gap_pressao_efetiva"].notna().any()),
        "ic_95_disponivel": bool(
            located[["gap_pressao_p025", "gap_pressao_p975"]].notna().all(axis=1).any()
        ),
        "arquivo_previsao_esperado": forecast_file_reference,
        "fontes": {
            "matriculas_publicas": PUBLIC_ENROLLMENT_FILE.name,
            "matriculas_parceiras": PARTNER_ENROLLMENT_FILE.name,
            "fila": APPLICATION_FILE.name,
            "coordenadas": LOCATION_FILE.name,
            "limites_territoriais": MICROAREA_FILE.name,
        },
    }
    return located, unmatched, summary


def format_integer(value: object) -> str:
    """Format spreadsheet-like values for map labels."""
    if pd.isna(value):
        return "—"
    return f"{int(round(float(value))):,}".replace(",", ".")


def format_ratio(value: object) -> str:
    """Format a ratio per 100 enrolled students."""
    if pd.isna(value):
        return "—"
    return f"{float(value):.1f}".replace(".", ",")


def pressure_color(category: str) -> str:
    """Map descriptive queue-pressure categories to accessible colors."""
    colors = {
        "Sem fila observada": "#2a9d8f",
        "Até 25 por 100 matriculados": "#e9c46a",
        "25 a 75 por 100 matriculados": "#f4a261",
        "Mais de 75 por 100 matriculados": "#e76f51",
        "Com fila e sem matrícula observada": "#7b2cbf",
    }
    return colors[category]


def build_popup(row: pd.Series) -> str:
    """Create a compact popup separating historical and predicted demand."""
    safe_name = html.escape(str(row["nome"]))
    safe_code = html.escape(str(row["codigo"]))
    safe_type = html.escape(str(row["tipo_oferta"]))
    safe_unit_type = html.escape(str(row["tipo_unidade"]))
    safe_address = html.escape(str(row["endereco"])) if pd.notna(row["endereco"]) else "—"
    safe_neighborhood = html.escape(str(row["bairro"])) if pd.notna(row["bairro"]) else "—"
    safe_reference = html.escape(str(row["referencia_matriculas"]))
    forecast_year = (
        format_integer(row["ano_previsao"])
        if pd.notna(row["ano_previsao"])
        else "ano futuro"
    )
    if pd.isna(row["gap_significativo_95"]):
        significance_label = "—"
    else:
        significance_label = "Sim" if bool(row["gap_significativo_95"]) else "Não"

    capacity_row = ""
    if row["capacidade_meta"] > 0:
        capacity_row = (
            f"<tr><td>Meta / vagas reportadas</td><td>{format_integer(row['capacidade_meta'])} / "
            f"{format_integer(row['vagas_reportadas'])}</td></tr>"
        )

    return f"""
    <div style="font-family:Arial,sans-serif;min-width:310px;color:#1f2937">
      <h4 style="margin:0 0 6px 0">{safe_name}</h4>
      <div style="font-size:12px;margin-bottom:8px">Código {safe_code} · {safe_type} · {safe_unit_type}</div>
      <div style="font-size:12px;margin-bottom:8px">{safe_address} · {safe_neighborhood}</div>
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead><tr><th style="text-align:left">Indicador (2025)</th><th style="text-align:right">Total</th></tr></thead>
        <tbody>
          <tr><td>Matrículas</td><td style="text-align:right"><strong>{format_integer(row['matriculas_total'])}</strong></td></tr>
          <tr><td>Demanda histórica — qualquer opção</td><td style="text-align:right"><strong>{format_integer(row['demanda_historica'])}</strong></td></tr>
          <tr><td>Demanda histórica por 100 matriculados</td><td style="text-align:right">{format_ratio(row['demanda_hist_por_100_matriculas'])}</td></tr>
          <tr><td>Inscritos previstos — Frente 1 ({forecast_year})</td><td style="text-align:right"><strong>{format_integer(row['demanda_prevista_inscritos'])}</strong></td></tr>
          <tr><td>Demanda efetiva prevista — Frente 2</td><td style="text-align:right"><strong>{format_integer(row['demanda_prevista_efetiva'])}</strong></td></tr>
          <tr><td>IC 95% da demanda efetiva</td><td style="text-align:right">[{format_integer(row['demanda_efetiva_p025'])}; {format_integer(row['demanda_efetiva_p975'])}]</td></tr>
          <tr><td>Capacidade do ano anterior</td><td style="text-align:right">{format_integer(row['capacidade_ano_anterior'])}</td></tr>
          <tr><td>Pressão efetiva prevista</td><td style="text-align:right"><strong>{format_integer(row['gap_pressao_efetiva'])}</strong></td></tr>
          <tr><td>IC 95% do gap</td><td style="text-align:right">[{format_integer(row['gap_pressao_p025'])}; {format_integer(row['gap_pressao_p975'])}]</td></tr>
          <tr><td>Gap significativo a 95%</td><td style="text-align:right">{significance_label}</td></tr>
          <tr><td>Lista de espera</td><td style="text-align:right"><strong>{format_integer(row['fila_total'])}</strong></td></tr>
          <tr><td>Fila por 100 matriculados</td><td style="text-align:right">{format_ratio(row['fila_por_100_matriculas'])}</td></tr>
          {capacity_row}
        </tbody>
      </table>
      <table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px">
        <thead><tr><th style="text-align:left">Faixa</th><th style="text-align:right">Matriculados</th><th style="text-align:right">Demanda hist.</th><th style="text-align:right">Fila</th></tr></thead>
        <tbody>
          <tr><td>Berçário</td><td style="text-align:right">{format_integer(row['mat_bercario'])}</td><td style="text-align:right">{format_integer(row['demanda_hist_bercario'])}</td><td style="text-align:right">{format_integer(row['fila_bercario'])}</td></tr>
          <tr><td>Maternal I</td><td style="text-align:right">{format_integer(row['mat_maternal_1'])}</td><td style="text-align:right">{format_integer(row['demanda_hist_maternal_1'])}</td><td style="text-align:right">{format_integer(row['fila_maternal_1'])}</td></tr>
          <tr><td>Maternal II</td><td style="text-align:right">{format_integer(row['mat_maternal_2'])}</td><td style="text-align:right">{format_integer(row['demanda_hist_maternal_2'])}</td><td style="text-align:right">{format_integer(row['fila_maternal_2'])}</td></tr>
        </tbody>
      </table>
      <div style="font-size:11px;color:#4b5563;margin-top:8px">Demanda histórica: crianças distintas que selecionaram esta unidade em qualquer opção no processo de 2025; a mesma criança pode aparecer em outras creches. Matrículas: {safe_reference}.</div>
    </div>
    """


def demand_radius(value: object) -> float:
    """Scale markers by historical or predicted child-unit demand."""
    demand = 0 if pd.isna(value) else max(float(value), 0)
    return min(12.0, 3.0 + math.sqrt(demand) / 3.2)


def add_microareas(map_object: folium.Map) -> None:
    """Add simplified official SME/IPP microarea boundaries."""
    microareas = gpd.read_file(MICROAREA_FILE)
    microareas["geometry"] = microareas.geometry.simplify(25, preserve_topology=True)
    microareas = microareas.to_crs(epsg=4326)
    microareas["cre"] = microareas["cre"].astype("string")
    microareas["cod_territ"] = microareas["cod_territ"].astype("string")

    folium.GeoJson(
        data=json.loads(microareas.to_json()),
        name="Microáreas SME/IPP",
        show=True,
        style_function=lambda _: {
            "color": "#71869a",
            "weight": 0.9,
            "opacity": 0.75,
            "fillColor": "#e7edf2",
            "fillOpacity": 0.55,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["cre", "cod_territ"],
            aliases=["CRE", "Microárea"],
            localize=True,
            sticky=False,
        ),
    ).add_to(map_object)


def add_legend(map_object: folium.Map, summary: dict[str, object]) -> None:
    """Add a compact legend and coverage note to the map."""
    mapped = format_integer(summary["unidades_mapeadas"])
    total = format_integer(summary["unidades_no_painel"])
    legend = f"""
    <div style="position:fixed;bottom:26px;left:26px;z-index:9999;background:rgba(255,255,255,0.95);padding:12px 14px;border:1px solid #d1d5db;border-radius:6px;font:12px Arial,sans-serif;color:#111827;box-shadow:0 1px 4px rgba(0,0,0,.18)">
      <div style="font-weight:700;margin-bottom:4px">Pressão por creche — 2025</div>
      <div style="margin-bottom:7px"><strong id="demand-mode-label">Demanda histórica (benchmark)</strong><br><span id="demand-mode-description" style="color:#4b5563">Círculo maior = mais crianças–unidade</span></div>
      <div id="demand-color-label" style="font-weight:700;margin-bottom:4px">Cor = pressão da lista de espera</div>
      <div><span style="color:#2a9d8f">●</span> Sem fila observada</div>
      <div><span style="color:#e9c46a">●</span> Até 25 por 100 matriculados</div>
      <div><span style="color:#f4a261">●</span> 25 a 75 por 100 matriculados</div>
      <div><span style="color:#e76f51">●</span> Mais de 75 por 100 matriculados</div>
      <div><span style="color:#7b2cbf">●</span> Com fila e sem matrícula observada</div>
      <div style="margin-top:7px;color:#4b5563">{mapped} de {total} unidades com coordenadas</div>
    </div>
    """
    map_object.get_root().html.add_child(Element(legend))


def add_demand_mode_control(
    map_object: folium.Map,
    marker_configuration: list[dict[str, object]],
    availability: dict[str, bool],
) -> None:
    """Add four demand modes and an optional 95% significant-gap filter."""
    f1_disabled = "" if availability["f1"] else "disabled"
    f2_disabled = "" if availability["f2"] else "disabled"
    pressure_disabled = "" if availability["pressure"] else "disabled"
    significance_disabled = "" if availability["interval"] else "disabled"
    forecast_note = html.escape(
        "Previsões carregadas"
        if availability["f1"] or availability["f2"]
        else f"Aguardando {PREDICTED_DEMAND_FILE.name}"
    )
    control = f"""
    <div style="position:fixed;top:76px;left:12px;z-index:9999;background:rgba(255,255,255,.96);padding:10px 12px;border:1px solid #d1d5db;border-radius:6px;font:12px Arial,sans-serif;color:#111827;box-shadow:0 1px 4px rgba(0,0,0,.18);max-width:255px">
      <div style="font-weight:700;margin-bottom:6px">Indicador de demanda</div>
      <label style="display:block;margin-bottom:4px"><input type="radio" name="demand-mode" checked onclick="setDemandMode('historica')"> Demanda histórica</label>
      <label style="display:block;margin-bottom:4px"><input type="radio" name="demand-mode" {f1_disabled} onclick="setDemandMode('inscritos')"> Inscritos previstos — Frente 1</label>
      <label style="display:block;margin-bottom:4px"><input type="radio" name="demand-mode" {f2_disabled} onclick="setDemandMode('efetiva')"> Demanda efetiva — Frente 2</label>
      <label style="display:block;margin-bottom:7px"><input type="radio" name="demand-mode" {pressure_disabled} onclick="setDemandMode('pressao')"> Pressão efetiva prevista</label>
      <div style="border-top:1px solid #e5e7eb;padding-top:7px">
        <label style="display:block"><input id="significant-gap-only" type="checkbox" {significance_disabled} onclick="setSignificanceFilter(this.checked)"> Apenas gaps significativos (IC 95%)</label>
      </div>
      <div style="color:#6b7280;margin-top:6px">{forecast_note}</div>
    </div>
    """
    map_object.get_root().html.add_child(Element(control))

    marker_entries = []
    for item in marker_configuration:
        marker_entries.append(
            "{"
            f"marker: {item['marker']}, "
            f"historical: {json.dumps(item['historical'])}, "
            f"predictedApplicants: {json.dumps(item['predictedApplicants'])}, "
            f"effectiveDemand: {json.dumps(item['effectiveDemand'])}, "
            f"pressureGap: {json.dumps(item['pressureGap'])}, "
            f"pressureLow: {json.dumps(item['pressureLow'])}, "
            f"pressureHigh: {json.dumps(item['pressureHigh'])}, "
            f"significant: {json.dumps(item['significant'])}, "
            f"historicalColor: {json.dumps(item['historicalColor'])}"
            "}"
        )
    marker_javascript = ",\n".join(marker_entries)
    script = f"""
    const demandMarkers = [{marker_javascript}];
    const gapIntervalAvailable = {str(availability['interval']).lower()};
    let currentDemandMode = 'historica';
    let significantGapOnly = false;
    const maximumPositiveGap = Math.max(1, ...demandMarkers.map(function(item) {{
      return item.pressureGap === null ? 0 : Math.max(Number(item.pressureGap), 0);
    }}));
    function isAvailable(value) {{
      return value !== null && !Number.isNaN(Number(value));
    }}
    function radiusForDemand(value, useAbsolute) {{
      const numericValue = isAvailable(value) ? Number(value) : 0;
      const safeValue = useAbsolute ? Math.abs(numericValue) : Math.max(numericValue, 0);
      return Math.min(12, 3 + Math.sqrt(safeValue) / 3.2);
    }}
    function pressureColor(value) {{
      if (!isAvailable(value)) return '#9ca3af';
      const numericValue = Number(value);
      if (numericValue < 0) return '#3b82f6';
      if (numericValue === 0) return '#9ca3af';
      const intensity = Math.log1p(numericValue) / Math.log1p(maximumPositiveGap);
      const lightness = 82 - 47 * Math.min(Math.max(intensity, 0), 1);
      return `hsl(0 78% ${{lightness}}%)`;
    }}
    function modeValue(item, mode) {{
      if (mode === 'inscritos') return item.predictedApplicants;
      if (mode === 'efetiva') return item.effectiveDemand;
      if (mode === 'pressao') return item.pressureGap;
      return item.historical;
    }}
    function applyDemandView() {{
      demandMarkers.forEach(function(item) {{
        if (!item.marker) return;
        const value = modeValue(item, currentDemandMode);
        const passesSignificance = !significantGapOnly || currentDemandMode !== 'pressao' || item.significant === true;
        const visible = isAvailable(value) && passesSignificance;
        let fillColor = item.historicalColor;
        if (currentDemandMode === 'inscritos') fillColor = '#f59e0b';
        if (currentDemandMode === 'efetiva') fillColor = '#2563eb';
        if (currentDemandMode === 'pressao') fillColor = pressureColor(value);
        item.marker.setRadius(visible ? radiusForDemand(value, currentDemandMode === 'pressao') : 0);
        item.marker.setStyle({{
          fillColor: fillColor,
          opacity: visible ? 1 : 0,
          fillOpacity: visible ? 0.76 : 0
        }});
      }});
      const label = document.getElementById('demand-mode-label');
      const description = document.getElementById('demand-mode-description');
      const colorLabel = document.getElementById('demand-color-label');
      const significance = document.getElementById('significant-gap-only');
      const labels = {{
        historica: ['Demanda histórica (benchmark)', 'Círculo maior = mais crianças–unidade', 'Cor = pressão da lista de espera'],
        inscritos: ['Inscritos previstos — Frente 1', 'Círculo maior = mais inscritos previstos', 'Cor = previsão da Frente 1'],
        efetiva: ['Demanda efetiva — Frente 2', 'Círculo maior = mais demanda efetiva', 'Cor = previsão da Frente 2'],
        pressao: ['Pressão efetiva prevista', 'Círculo maior = maior gap absoluto', 'Vermelho = excesso de demanda; azul = capacidade excedente']
      }};
      if (label) label.textContent = labels[currentDemandMode][0];
      if (description) description.textContent = labels[currentDemandMode][1];
      if (colorLabel) colorLabel.textContent = labels[currentDemandMode][2];
      if (significance) significance.disabled = currentDemandMode !== 'pressao' || !gapIntervalAvailable;
    }}
    window.setDemandMode = function(mode) {{
      currentDemandMode = mode;
      applyDemandView();
    }};
    window.setSignificanceFilter = function(enabled) {{
      significantGapOnly = Boolean(enabled);
      applyDemandView();
    }};
    """
    map_object.get_root().script.add_child(Element(script))


def create_map(located: pd.DataFrame, summary: dict[str, object]) -> None:
    """Create an interactive map with historical and optional predicted demand."""
    map_center = [located["latitude"].median(), located["longitude"].median()]
    map_object = folium.Map(
        location=map_center,
        zoom_start=10,
        tiles=None,
        attribution_control=False,
        control_scale=True,
        prefer_canvas=True,
    )
    # The map uses the local SME/IPP geometry as its geographic background.
    # This avoids depending on an external tile provider and its attribution.
    map_object.get_root().header.add_child(
        Element(
            """
            <style>
              .leaflet-container { background: #f4f7f9; }
            </style>
            """
        )
    )
    map_object.fit_bounds(
        [
            [located["latitude"].min(), located["longitude"].min()],
            [located["latitude"].max(), located["longitude"].max()],
        ],
        padding=(30, 30),
    )
    add_microareas(map_object)

    layer_names = {
        "Pública": "Unidades públicas",
        "Parceira": "Creches parceiras",
        "Pública e parceira": "Unidades de fonte mista",
        "Somente inscrição": "Somente demanda localizada",
    }
    available_types = set(located["tipo_oferta"].dropna())
    feature_groups = {
        provider_type: folium.FeatureGroup(name=layer_name, show=True)
        for provider_type, layer_name in layer_names.items()
        if provider_type in available_types
    }
    for group in feature_groups.values():
        group.add_to(map_object)

    marker_configuration = []
    for _, row in located.iterrows():
        provider_type = row["tipo_oferta"]
        target_group = feature_groups[provider_type]
        color = pressure_color(row["classe_pressao_fila"])
        tooltip = (
            f"{row['nome']} | Demanda histórica: {format_integer(row['demanda_historica'])} | "
            f"Frente 1: {format_integer(row['demanda_prevista_inscritos'])} | "
            f"Frente 2: {format_integer(row['demanda_prevista_efetiva'])} | "
            f"Gap efetivo: {format_integer(row['gap_pressao_efetiva'])}"
        )
        marker = folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=demand_radius(row["demanda_historica"]),
            color="#ffffff",
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.76,
            tooltip=tooltip,
            popup=folium.Popup(build_popup(row), max_width=420),
        )
        marker.add_to(target_group)
        marker_configuration.append(
            {
                "marker": marker.get_name(),
                "historical": float(row["demanda_historica"]),
                "predictedApplicants": (
                    None
                    if pd.isna(row["demanda_prevista_inscritos"])
                    else float(row["demanda_prevista_inscritos"])
                ),
                "effectiveDemand": (
                    None
                    if pd.isna(row["demanda_prevista_efetiva"])
                    else float(row["demanda_prevista_efetiva"])
                ),
                "pressureGap": (
                    None
                    if pd.isna(row["gap_pressao_efetiva"])
                    else float(row["gap_pressao_efetiva"])
                ),
                "pressureLow": (
                    None
                    if pd.isna(row["gap_pressao_p025"])
                    else float(row["gap_pressao_p025"])
                ),
                "pressureHigh": (
                    None
                    if pd.isna(row["gap_pressao_p975"])
                    else float(row["gap_pressao_p975"])
                ),
                "significant": (
                    None
                    if pd.isna(row["gap_significativo_95"])
                    else bool(row["gap_significativo_95"])
                ),
                "historicalColor": color,
            }
        )

    historical_heat = located.loc[
        located["demanda_historica"].gt(0),
        ["latitude", "longitude", "demanda_historica"],
    ]
    if not historical_heat.empty:
        HeatMap(
            data=historical_heat.values.tolist(),
            name="Calor da demanda histórica (benchmark)",
            radius=22,
            blur=20,
            min_opacity=0.25,
            show=False,
        ).add_to(map_object)

    front1_heat = located.loc[
        located["demanda_prevista_inscritos"].gt(0),
        ["latitude", "longitude", "demanda_prevista_inscritos"],
    ]
    if not front1_heat.empty:
        HeatMap(
            data=front1_heat.values.tolist(),
            name="Calor dos inscritos previstos — Frente 1",
            radius=22,
            blur=20,
            min_opacity=0.25,
            show=False,
        ).add_to(map_object)

    front2_heat = located.loc[
        located["demanda_prevista_efetiva"].gt(0),
        ["latitude", "longitude", "demanda_prevista_efetiva"],
    ]
    if not front2_heat.empty:
        HeatMap(
            data=front2_heat.values.tolist(),
            name="Calor da demanda efetiva — Frente 2",
            radius=22,
            blur=20,
            min_opacity=0.25,
            show=False,
        ).add_to(map_object)

    pressure_heat = located.loc[
        located["gap_pressao_efetiva"].gt(0),
        ["latitude", "longitude", "gap_pressao_efetiva"],
    ]
    if not pressure_heat.empty:
        HeatMap(
            data=pressure_heat.values.tolist(),
            name="Calor da pressão efetiva prevista",
            radius=22,
            blur=20,
            min_opacity=0.25,
            show=False,
        ).add_to(map_object)

    heat_data = located.loc[located["fila_total"].gt(0), ["latitude", "longitude", "fila_total"]]
    if not heat_data.empty:
        HeatMap(
            data=heat_data.values.tolist(),
            name="Calor da lista de espera",
            radius=22,
            blur=20,
            min_opacity=0.25,
            show=False,
        ).add_to(map_object)

    Fullscreen(
        position="topleft",
        title="Tela cheia",
        title_cancel="Sair da tela cheia",
    ).add_to(map_object)
    add_demand_mode_control(
        map_object,
        marker_configuration,
        {
            "f1": bool(summary["f1_disponivel"]),
            "f2": bool(summary["f2_disponivel"]),
            "pressure": bool(summary["pressao_prevista_disponivel"]),
            "interval": bool(summary["ic_95_disponivel"]),
        },
    )
    folium.LayerControl(collapsed=False, position="topright").add_to(map_object)
    add_legend(map_object, summary)

    title = """
    <div style="position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:9998;background:rgba(255,255,255,0.94);padding:8px 14px;border-radius:6px;border:1px solid #d1d5db;font:14px Arial,sans-serif;color:#111827;box-shadow:0 1px 4px rgba(0,0,0,.14)">
      <strong>Creches do Rio — pressão de demanda por unidade (2025)</strong>
    </div>
    """
    map_object.get_root().html.add_child(Element(title))
    map_object.save(MAP_FILE)


def export_outputs(
    located: pd.DataFrame,
    unmatched: pd.DataFrame,
    summary: dict[str, object],
) -> None:
    """Save reproducible results without modifying any source dataset."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    located.to_csv(PANEL_FILE, index=False, encoding="utf-8-sig")
    unmatched.to_csv(UNMATCHED_FILE, index=False, encoding="utf-8-sig")
    SUMMARY_FILE.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    create_map(located, summary)


def main() -> None:
    """Run the full latest-year map pipeline."""
    located, unmatched, summary = build_panel()
    export_outputs(located, unmatched, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Map: {MAP_FILE}")
    print(f"Panel: {PANEL_FILE}")
    print(f"Unmatched: {UNMATCHED_FILE}")


if __name__ == "__main__":
    main()
