"""Integra o envelope territorial da modelo de demanda potencial às escolhas da modelo de escolha."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline_demanda.executar_frente2 import (
    QUERY_A,
    CountConditionalLogit,
    add_fold_features,
    build_panel,
    haversine,
    historical_probabilities,
    load_units,
)
from pipeline_demanda.rotinas.episodes import build_choice_episodes
from pipeline_demanda.rotinas.io import load_query_a

ENVELOPE_DIR = ROOT / "pipeline_demanda" / "05_integracao_com_frente1" / "insumos_2026"
OUT = ROOT / "pipeline_demanda" / "06_resultados"
GENERATED = OUT / "arquivos_gerados"
TRAIN_YEARS = (2021, 2022, 2023, 2024, 2025)
MARKET = ["ano", "origin_area", "grupamento_norm"]

ALIASES = {
    "MARE": "COMPLEXO MARE",
    "FREGUESIA JACAREPAGUA": "FREGUESIA JPA",
    "FREGUESIA ILHA GOVERNADOR": "FREGUESIA ILHA",
    "SANTA TEREZA": "SANTA TERESA",
    "CAVALCANTI": "CAVALCANTE",
    "BRAZ PINA": "BRAS PINA",
    "ILHA PAQUETA": "PAQUETA",
    "RECREIO": "RECREIO BANDEIRANTES",
    "LINS": "LINS VASCONCELOS",
    "QUINTINO": "QUINTINO BOCAIUVA",
    "GARDENIA": "GARDENIA AZUL",
    "JD CARIOCA": "JARDIM CARIOCA",
    "COPACABAMA": "COPACABANA",
    "SANTOS CRISTO": "SANTO CRISTO",
}


def canonical_area(values: pd.Series) -> pd.Series:
    def clean(value):
        if pd.isna(value):
            return pd.NA
        text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
        text = re.sub(r"\b(DO|DA|DOS|DAS|DE)\b", " ", text.upper().strip())
        text = re.sub(r"[^A-Z0-9]+", " ", text)
        text = " ".join(text.split())
        return ALIASES.get(text, text)

    return values.map(clean).astype("string")


def first_registration_per_child_year(episodes: pd.DataFrame) -> pd.DataFrame:
    registrations = (
        episodes.groupby(["ano", "aluno_anon", "inscricao_id"], as_index=False, observed=True)
        .agg(data_primeiro_registro=("data_criacao", "min"))
        .sort_values(
            ["ano", "aluno_anon", "data_primeiro_registro", "inscricao_id"],
            kind="stable",
        )
        .drop_duplicates(["ano", "aluno_anon"], keep="first")
    )
    return episodes.merge(
        registrations[["ano", "aluno_anon", "inscricao_id"]],
        on=["ano", "aluno_anon", "inscricao_id"],
        how="inner",
        validate="many_to_one",
    )


def load_envelope() -> pd.DataFrame:
    envelope = pd.read_csv(ENVELOPE_DIR / "contexto_bairro_grupo_2026.csv")
    envelope = envelope.rename(
        columns={"territorio": "origin_area", "grupamento_modelo": "grupamento_norm"}
    )
    envelope["origin_area"] = canonical_area(envelope["origin_area"])
    envelope["grupamento_norm"] = envelope["grupamento_norm"].str.upper()
    keys = [*MARKET]
    if envelope.duplicated(keys).any():
        raise ValueError("Envelope da modelo de demanda potencial contém célula duplicada")
    required = ["prev_modelo", "prev_persistencia", "p025", "p975"]
    if envelope[required].isna().any().any() or (envelope[required] < 0).any().any():
        raise ValueError("Envelope da modelo de demanda potencial contém previsão inválida")
    return envelope


def prepare_geography():
    units, centroids = load_units()
    units["unit_bairro_norm"] = canonical_area(units["unit_bairro_norm"])
    centroids["origin_area"] = canonical_area(centroids["origin_area"])
    centroids = (
        centroids.dropna(subset=["origin_area"])
        .groupby("origin_area", as_index=False, observed=True)
        .agg(origin_lat=("origin_lat", "median"), origin_lon=("origin_lon", "median"))
    )
    return units, centroids


def make_target(envelope, alternatives, units, centroids):
    markets = envelope.merge(centroids, on="origin_area", how="left", validate="many_to_one")
    markets["origin_geo_observed"] = markets["origin_lat"].notna()
    markets["origin_lat"] = markets["origin_lat"].fillna(float(units["latitude"].median()))
    markets["origin_lon"] = markets["origin_lon"].fillna(float(units["longitude"].median()))
    markets["n_choices"] = markets["prev_modelo"]

    active = alternatives.loc[alternatives["ano"].eq(2025)].drop(columns="ano")
    target = markets.merge(active, on="grupamento_norm", how="left", validate="many_to_many")
    if target["alternativa_id"].isna().any():
        raise ValueError("Grupamento da modelo de demanda potencial sem alternativas ativas em 2025")
    target["choice_count"] = 0
    target["market_id"] = (
        target["ano"].astype(str)
        + "|" + target["origin_area"].astype(str)
        + "|" + target["grupamento_norm"].astype(str)
    )
    target["distance_km"] = haversine(
        target["origin_lat"], target["origin_lon"], target["latitude"], target["longitude"]
    )
    target["log_distance"] = np.log1p(target["distance_km"])
    target["same_bairro"] = (
        target["origin_geo_observed"] & target["origin_area"].eq(target["unit_bairro_norm"])
    ).fillna(False).astype(float)
    target["is_partial"] = target["horario_norm"].eq("PARCIAL").astype(float)
    target["is_partner"] = target["unidade"].str.len().eq(5).astype(float)
    target["is_edi"] = target["tipo_unidade_norm"].eq("EDI").fillna(False).astype(float)
    target["unit_geo_imputed"] = target["unit_geo_imputed"].fillna(True).astype(float)
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run():
    GENERATED.mkdir(parents=True, exist_ok=True)
    envelope = load_envelope()
    options = load_query_a(QUERY_A)
    episodes_all = build_choice_episodes(options)
    episodes = first_registration_per_child_year(episodes_all)
    episodes["bairro_norm"] = canonical_area(episodes["bairro_norm"])

    units, centroids = prepare_geography()
    panel, alternatives, _, audit = build_panel(episodes, units, centroids)
    target = make_target(envelope, alternatives, units, centroids)
    featured = add_fold_features(
        pd.concat([panel, target], ignore_index=True, sort=False),
        episodes,
        TRAIN_YEARS,
        2026,
    )
    train = featured.loc[featured["ano"].isin(TRAIN_YEARS)].reset_index(drop=True)
    forecast = featured.loc[featured["ano"].eq(2026)].reset_index(drop=True)

    features = [
        "log_distance", "same_bairro", "is_partial", "is_partner", "is_edi",
        "unit_geo_imputed", "log_lag_first", "log_lag_list",
        "log_geo_competition", "log_colist_competition",
        "distance_maternal_i", "distance_maternal_ii",
    ]
    model = CountConditionalLogit(features).fit(train)
    forecast["choice_share"] = model.predict(forecast)
    forecast["choice_share_historical"] = historical_probabilities(train, forecast)

    share_sum = forecast.groupby(MARKET, observed=True)[
        ["choice_share", "choice_share_historical"]
    ].sum()
    if not np.allclose(share_sum.to_numpy(), 1.0, atol=1e-8):
        raise AssertionError("Participações da modelo de escolha não somam um")

    forecast["demanda_2026_ppml"] = forecast["prev_modelo"] * forecast["choice_share"]
    forecast["demanda_2026_persistencia"] = (
        forecast["prev_persistencia"] * forecast["choice_share"]
    )
    forecast["demanda_2026_ppml_historico"] = (
        forecast["prev_modelo"] * forecast["choice_share_historical"]
    )
    forecast["demanda_2026_ppml_p025_condicional"] = forecast["p025"] * forecast["choice_share"]
    forecast["demanda_2026_ppml_p975_condicional"] = forecast["p975"] * forecast["choice_share"]

    totals = {
        "ppml_envelope": float(envelope["prev_modelo"].sum()),
        "persistencia_envelope": float(envelope["prev_persistencia"].sum()),
        "ppml_integrado": float(forecast["demanda_2026_ppml"].sum()),
        "persistencia_integrada": float(forecast["demanda_2026_persistencia"].sum()),
    }
    if not np.isclose(totals["ppml_envelope"], totals["ppml_integrado"]):
        raise AssertionError("Integração não conservou o envelope PPML")
    if not np.isclose(totals["persistencia_envelope"], totals["persistencia_integrada"]):
        raise AssertionError("Integração não conservou o envelope de persistência")

    detail_columns = [
        *MARKET, "alternativa_id", "unidade", "nome_unidade_norm", "horario_norm",
        "choice_share", "choice_share_historical", "prev_modelo", "prev_persistencia",
        "demanda_2026_ppml", "demanda_2026_persistencia",
        "demanda_2026_ppml_historico", "demanda_2026_ppml_p025_condicional",
        "demanda_2026_ppml_p975_condicional", "distance_km", "geo_source",
    ]
    forecast[detail_columns].to_csv(
        GENERATED / "previsao_integrada_detalhada_2026.csv.gz", index=False, compression="gzip"
    )

    alternative = (
        forecast.groupby(
            ["alternativa_id", "unidade", "nome_unidade_norm", "grupamento_norm", "horario_norm"],
            as_index=False,
            observed=True,
        )
        .agg(
            demanda_2026_ppml=("demanda_2026_ppml", "sum"),
            demanda_2026_persistencia=("demanda_2026_persistencia", "sum"),
            demanda_2026_ppml_historico=("demanda_2026_ppml_historico", "sum"),
            limite_p025_condicional=("demanda_2026_ppml_p025_condicional", "sum"),
            limite_p975_condicional=("demanda_2026_ppml_p975_condicional", "sum"),
            territorios_atendidos=("origin_area", "nunique"),
        )
    )
    alternative.to_csv(GENERATED / "previsao_por_alternativa_2026.csv", index=False)

    unit = (
        alternative.groupby(["unidade", "nome_unidade_norm"], as_index=False, observed=True)
        .agg(
            demanda_2026_ppml=("demanda_2026_ppml", "sum"),
            demanda_2026_persistencia=("demanda_2026_persistencia", "sum"),
            demanda_2026_ppml_historico=("demanda_2026_ppml_historico", "sum"),
            limite_p025_condicional=("limite_p025_condicional", "sum"),
            limite_p975_condicional=("limite_p975_condicional", "sum"),
        )
    )
    unit["codigo_unidade"] = unit["unidade"].str.lstrip("0").replace("", "0")
    gross = pd.read_csv(ENVELOPE_DIR / "demanda_bruta_2025.csv", dtype={"codigo_unidade": "string"})
    gross["codigo_unidade"] = gross["codigo_unidade"].str.lstrip("0").replace("", "0")
    gross = gross.rename(columns={"demanda_observada": "interesse_bruto_2025"})
    context = pd.read_csv(ENVELOPE_DIR / "contexto_creches_2025.csv", dtype={"codigo_unidade": "string"})
    context["codigo_unidade"] = context["codigo_unidade"].str.lstrip("0").replace("", "0")
    validation = pd.read_csv(ENVELOPE_DIR / "validacao_oos_2025.csv", dtype={"codigo_unidade": "string"})
    validation["codigo_unidade"] = validation["codigo_unidade"].str.lstrip("0").replace("", "0")
    unit = unit.merge(
        gross[["codigo_unidade", "interesse_bruto_2025", "status_em_2025"]],
        on="codigo_unidade", how="left", validate="one_to_one",
    ).merge(
        context[["codigo_unidade", "tipo_oferta", "tipo_unidade", "cre", "microarea", "bairro",
                 "latitude", "longitude", "matriculas_total", "fila_total"]],
        on="codigo_unidade", how="left", validate="one_to_one",
    ).merge(
        validation[["codigo_unidade", "prev_ppml_base_2025", "prev_persistencia_2025",
                    "prev_ppml_cag_fem_2025"]],
        on="codigo_unidade", how="left", validate="one_to_one",
    )
    unit["tem_contexto_creche_2025"] = unit["latitude"].notna() & unit["longitude"].notna()
    unit = unit.sort_values("demanda_2026_ppml", ascending=False)
    unit.to_csv(OUT / "previsao_integrada_unidade_2026.csv", index=False, encoding="utf-8-sig")

    group = (
        forecast.groupby("grupamento_norm", as_index=False, observed=True)
        .agg(
            demanda_2026_ppml=("demanda_2026_ppml", "sum"),
            demanda_2026_persistencia=("demanda_2026_persistencia", "sum"),
            demanda_2026_ppml_historico=("demanda_2026_ppml_historico", "sum"),
        )
    )
    group.to_csv(OUT / "previsao_integrada_grupamento_2026.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "estimand": "primeira opcao por crianca em 2026, por unidade e turno",
        "territorial_envelope": "PPML-FE bairro x grupamento; persistencia como cenario",
        "choice_distribution": "conditional_logit_full treinado em 2021-2025",
        "competition": "distancia geografica e co-selecao historica",
        "alternatives_2026": "alternativas unidade-turno ativas em 2025",
        "children_training": int(episodes.loc[episodes["primeira_opcao"], "aluno_anon"].count()),
        "markets_2026": int(forecast["market_id"].nunique()),
        "alternatives_2026_count": int(forecast["alternativa_id"].nunique()),
        "origin_geo_coverage_2026": float(
            forecast.groupby("market_id", observed=True)["origin_geo_observed"].first().mean()
        ),
        "unit_context_coverage": float(unit["tem_contexto_creche_2025"].mean()),
        "totals": totals,
        "envelope_input_sha256": sha256(ENVELOPE_DIR / "contexto_bairro_grupo_2026.csv"),
        "historico_bruto_2025_sha256": sha256(ENVELOPE_DIR / "demanda_bruta_2025.csv"),
        "notes": [
            "CAGED feminino permanece sensibilidade OOS de 2025 e não é extrapolado para 2026.",
            "Limites p025/p975 pertencem ao envelope territorial e condicionam-se às participações pontuais do modelo de escolha.",
            "Matrículas e fila são contexto; não são capacidade física.",
        ],
        "audit_choice_model": audit,
    }
    (OUT / "manifesto_integracao_2026.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    model.coefficients("conditional_logit_full_2026", "train_2021_2025").to_csv(
        OUT / "coeficientes_modelo_integrado_2026.csv", index=False, encoding="utf-8-sig"
    )
    evaluation_path = ROOT / "pipeline_demanda" / "07_painel" / "public" / "results.json"
    previous_evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    panel_results = {
        "generated_at": manifest["created_at_utc"],
        "projection": {
            "total_ppml": totals["ppml_integrado"],
            "total_persistence": totals["persistencia_integrada"],
            "markets": manifest["markets_2026"],
            "alternatives": manifest["alternatives_2026_count"],
            "units": int(len(unit)),
            "origin_geo_coverage": manifest["origin_geo_coverage_2026"],
            "unit_context_coverage": manifest["unit_context_coverage"],
        },
        "groups": group.round(2).to_dict(orient="records"),
        "top_units": unit[[
            "codigo_unidade", "nome_unidade_norm", "demanda_2026_ppml",
            "demanda_2026_persistencia", "interesse_bruto_2025", "bairro",
        ]].head(10).fillna("").to_dict(orient="records"),
        "audit": audit,
        "metrics": previous_evaluation.get("metrics", []),
    }
    evaluation_path.write_text(
        json.dumps(panel_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("\nTotais por grupamento")
    print(group.round(1).to_string(index=False))


if __name__ == "__main__":
    run()