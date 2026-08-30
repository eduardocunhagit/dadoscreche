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


def load_waitlist() -> pd.DataFrame:
    """Count distinct children waiting for each unit in the 2025 process."""
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
    applications = applications.loc[
        applications["ano"].eq(REFERENCE_YEAR)
        & applications["situacao"].eq("Lista de espera")
    ].copy()
    applications["codigo"] = normalize_code(applications["unidade"])
    applications["grupamento_limpo"] = applications["grupamento"].str.strip()

    group_map = {
        "Berçário": "fila_bercario",
        "Maternal I": "fila_maternal_1",
        "Maternal II": "fila_maternal_2",
    }
    applications["grupo_fila"] = applications["grupamento_limpo"].map(group_map)

    # A child can select several units. Counting distinct child-unit pairs
    # measures the queue faced by each unit without double-counting duplicates.
    total_wait = (
        applications.drop_duplicates(["codigo", "aluno_anon"])
        .groupby("codigo")["aluno_anon"]
        .nunique()
        .rename("fila_total")
    )
    wait_by_group = (
        applications.dropna(subset=["grupo_fila"])
        .drop_duplicates(["codigo", "aluno_anon", "grupo_fila"])
        .groupby(["codigo", "grupo_fila"])["aluno_anon"]
        .nunique()
        .unstack(fill_value=0)
    )
    wait_names = applications.groupby("codigo")["nome_unidade"].agg(first_non_null)

    waitlist = pd.concat([wait_names, total_wait, wait_by_group], axis=1).reset_index()
    for column in ("fila_bercario", "fila_maternal_1", "fila_maternal_2"):
        if column not in waitlist.columns:
            waitlist[column] = 0
    return waitlist.rename(columns={"nome_unidade": "nome_fila"})


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
    waitlist = load_waitlist()
    enrollment = combine_enrollment(public, partners)

    panel = enrollment.merge(waitlist, on="codigo", how="outer")
    panel["tipo_oferta"] = panel["tipo_oferta"].fillna("Somente inscrição")
    numeric_columns = [
        "mat_bercario",
        "mat_maternal_1",
        "mat_maternal_2",
        "matriculas_total",
        "turmas_total",
        "capacidade_meta",
        "vagas_reportadas",
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
        .combine_first(panel["nome_fila"])
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

    # Empty forecast fields are deliberate integration points for the demand
    # model. They avoid mixing descriptive queue pressure with model results.
    panel["demanda_prevista"] = np.nan
    panel["gap_demanda_oferta"] = np.nan
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
        "fila_total",
        "fila_bercario",
        "fila_maternal_1",
        "fila_maternal_2",
        "fila_por_100_matriculas",
        "classe_pressao_fila",
        "referencia_matriculas",
        "demanda_prevista",
        "gap_demanda_oferta",
        "prioridade_modelo",
    ]
    located = located[export_columns].sort_values(
        ["fila_total", "matriculas_total"], ascending=False
    )
    unmatched = unmatched[export_columns].sort_values(
        ["fila_total", "matriculas_total"], ascending=False
    )

    summary = {
        "ano_referencia": REFERENCE_YEAR,
        "unidades_no_painel": int(len(panel)),
        "unidades_mapeadas": int(len(located)),
        "unidades_sem_coordenada": int(len(unmatched)),
        "matriculas_mapeadas": int(located["matriculas_total"].sum()),
        "criancas_em_fila_mapeadas_por_unidade": int(located["fila_total"].sum()),
        "unidades_com_fila": int(located["fila_total"].gt(0).sum()),
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
    """Create a compact popup with enrollment and queue age profiles."""
    safe_name = html.escape(str(row["nome"]))
    safe_code = html.escape(str(row["codigo"]))
    safe_type = html.escape(str(row["tipo_oferta"]))
    safe_unit_type = html.escape(str(row["tipo_unidade"]))
    safe_address = html.escape(str(row["endereco"])) if pd.notna(row["endereco"]) else "—"
    safe_neighborhood = html.escape(str(row["bairro"])) if pd.notna(row["bairro"]) else "—"
    safe_reference = html.escape(str(row["referencia_matriculas"]))

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
          <tr><td>Lista de espera</td><td style="text-align:right"><strong>{format_integer(row['fila_total'])}</strong></td></tr>
          <tr><td>Fila por 100 matriculados</td><td style="text-align:right">{format_ratio(row['fila_por_100_matriculas'])}</td></tr>
          {capacity_row}
        </tbody>
      </table>
      <table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px">
        <thead><tr><th style="text-align:left">Faixa</th><th style="text-align:right">Matriculados</th><th style="text-align:right">Fila</th></tr></thead>
        <tbody>
          <tr><td>Berçário</td><td style="text-align:right">{format_integer(row['mat_bercario'])}</td><td style="text-align:right">{format_integer(row['fila_bercario'])}</td></tr>
          <tr><td>Maternal I</td><td style="text-align:right">{format_integer(row['mat_maternal_1'])}</td><td style="text-align:right">{format_integer(row['fila_maternal_1'])}</td></tr>
          <tr><td>Maternal II</td><td style="text-align:right">{format_integer(row['mat_maternal_2'])}</td><td style="text-align:right">{format_integer(row['fila_maternal_2'])}</td></tr>
        </tbody>
      </table>
      <div style="font-size:11px;color:#4b5563;margin-top:8px">Matrículas: {safe_reference}. Fila: processo de inscrição 2025.</div>
    </div>
    """


def marker_radius(row: pd.Series) -> float:
    """Scale markers by the amount of observed enrollment plus queue demand."""
    observed_scale = max(float(row["matriculas_total"] + row["fila_total"]), 1)
    return min(10.0, 3.0 + math.sqrt(observed_scale) / 3.2)


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
      <div style="font-weight:700;margin-bottom:7px">Pressão descritiva da fila — 2025</div>
      <div><span style="color:#2a9d8f">●</span> Sem fila observada</div>
      <div><span style="color:#e9c46a">●</span> Até 25 por 100 matriculados</div>
      <div><span style="color:#f4a261">●</span> 25 a 75 por 100 matriculados</div>
      <div><span style="color:#e76f51">●</span> Mais de 75 por 100 matriculados</div>
      <div><span style="color:#7b2cbf">●</span> Com fila e sem matrícula observada</div>
      <div style="margin-top:7px;color:#4b5563">Círculo maior = mais matrículas + fila<br>{mapped} de {total} unidades com coordenadas</div>
    </div>
    """
    map_object.get_root().html.add_child(Element(legend))


def create_map(located: pd.DataFrame, summary: dict[str, object]) -> None:
    """Create an interactive map ready for the future demand-model join."""
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
        "Somente inscrição": "Somente fila localizada",
    }
    available_types = set(located["tipo_oferta"].dropna())
    feature_groups = {
        provider_type: folium.FeatureGroup(name=layer_name, show=True)
        for provider_type, layer_name in layer_names.items()
        if provider_type in available_types
    }
    for group in feature_groups.values():
        group.add_to(map_object)

    for _, row in located.iterrows():
        provider_type = row["tipo_oferta"]
        target_group = feature_groups[provider_type]
        color = pressure_color(row["classe_pressao_fila"])
        tooltip = (
            f"{row['nome']} | Matrículas: {format_integer(row['matriculas_total'])} | "
            f"Fila: {format_integer(row['fila_total'])}"
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=marker_radius(row),
            color="#ffffff",
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.76,
            tooltip=tooltip,
            popup=folium.Popup(build_popup(row), max_width=420),
        ).add_to(target_group)

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
    folium.LayerControl(collapsed=False, position="topright").add_to(map_object)
    add_legend(map_object, summary)

    title = """
    <div style="position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:9998;background:rgba(255,255,255,0.94);padding:8px 14px;border-radius:6px;border:1px solid #d1d5db;font:14px Arial,sans-serif;color:#111827;box-shadow:0 1px 4px rgba(0,0,0,.14)">
      <strong>Creches do Rio — matrículas e lista de espera (2025)</strong>
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
