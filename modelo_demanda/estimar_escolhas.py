"""Executa todos os modelos explicáveis da modelo de escolha em dados reais."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .rotinas.competition import build_colisting_network, colisting_competition
    from .rotinas.episodes import build_choice_episodes
    from .rotinas.io import load_query_a
    from .rotinas.normalization import normalize_code, normalize_text
    from .rotinas.splits import STANDARD_FOLDS
except ImportError:
    from rotinas.competition import build_colisting_network, colisting_competition
    from rotinas.episodes import build_choice_episodes
    from rotinas.io import load_query_a
    from rotinas.normalization import normalize_code, normalize_text
    from rotinas.splits import STANDARD_FOLDS


ROOT = Path(__file__).resolve().parents[1]
QUERY_A = ROOT / "Bases IC_ ClassificadoseFila" / "01_QueryA_InscricoesPorAno.csv.gz"
QUERY_D = ROOT / "Bases IC_ ClassificadoseFila" / "04_UnidadesEscolaresComEndereco.csv"
LOCATIONS = ROOT / "OferecimentosEvagas" / "Unidades_Unificadas_com_Localizacao.xlsx"
OUT = ROOT / "modelo_demanda" / "06_resultados" / "arquivos_gerados"
FRONTEND_RESULTS = ROOT / "modelo_demanda" / "07_painel" / "public" / "results.json"
MARKET = ["ano", "origin_area", "grupamento_norm"]


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(
        np.radians,
        [np.asarray(lat1, float), np.asarray(lon1, float),
         np.asarray(lat2, float), np.asarray(lon2, float)],
    )
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def file_hash(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_units():
    loc = pd.read_excel(LOCATIONS, sheet_name="Unidades_Unificadas")
    loc["unidade"] = normalize_code(loc["DESIGNACAO"])
    public_short = loc["unidade"].str.fullmatch(r"\d{6}", na=False)
    loc.loc[public_short, "unidade"] = loc.loc[public_short, "unidade"].str.zfill(7)
    loc["bairro_loc_norm"] = normalize_text(loc["BAIRRO"])
    loc["nome_loc_norm"] = normalize_text(loc["DENOMINACAO"])
    loc["tipo_unidade_norm"] = normalize_text(loc["Tipo"])
    loc["latitude"] = pd.to_numeric(loc["LATITUDE"], errors="coerce")
    loc["longitude"] = pd.to_numeric(loc["LONGITUDE"], errors="coerce")
    loc = loc.dropna(subset=["unidade"]).drop_duplicates("unidade")

    names = [
        "seq", "esc_codigo", "nome_catalogo", "tipo_catalogo", "logradouro",
        "numero", "complemento", "bairro_catalogo", "cep_unidade",
    ]
    address = pd.read_csv(
        QUERY_D, sep=";", header=None, names=names, encoding="utf-8-sig",
        na_values=["NULL"], dtype="string",
    )
    address["unidade"] = normalize_code(address["esc_codigo"])
    address["bairro_catalogo_norm"] = normalize_text(address["bairro_catalogo"])
    address["nome_catalogo_norm"] = normalize_text(address["nome_catalogo"])
    address = address.dropna(subset=["unidade"]).drop_duplicates("unidade")

    units = address.merge(
        loc[["unidade", "bairro_loc_norm", "tipo_unidade_norm", "latitude", "longitude"]],
        on="unidade", how="outer", validate="one_to_one",
    )
    name_geo = loc.dropna(subset=["nome_loc_norm", "latitude", "longitude"]).copy()
    unique_names = name_geo["nome_loc_norm"].value_counts()
    name_geo = name_geo[name_geo["nome_loc_norm"].map(unique_names).eq(1)]
    name_geo = name_geo[
        ["nome_loc_norm", "latitude", "longitude", "tipo_unidade_norm", "bairro_loc_norm"]
    ].rename(columns={
        "latitude": "latitude_name", "longitude": "longitude_name",
        "tipo_unidade_norm": "tipo_name", "bairro_loc_norm": "bairro_name",
    })
    units = units.merge(
        name_geo, left_on="nome_catalogo_norm", right_on="nome_loc_norm",
        how="left", validate="many_to_one",
    )
    units["latitude"] = units["latitude"].fillna(units["latitude_name"])
    units["longitude"] = units["longitude"].fillna(units["longitude_name"])
    units["tipo_unidade_norm"] = units["tipo_unidade_norm"].fillna(units["tipo_name"])
    units["bairro_loc_norm"] = units["bairro_loc_norm"].fillna(units["bairro_name"])
    units["unit_bairro_norm"] = units["bairro_catalogo_norm"].fillna(units["bairro_loc_norm"])
    official = units["latitude"].notna() & units["longitude"].notna()

    alias_parts = []
    for col in ["bairro_catalogo_norm", "bairro_loc_norm"]:
        part = (
            units.loc[official & units[col].notna()]
            .groupby(col, observed=True)
            .agg(origin_lat=("latitude", "median"), origin_lon=("longitude", "median"))
            .reset_index().rename(columns={col: "origin_area"})
        )
        alias_parts.append(part)
    centroids = (
        pd.concat(alias_parts, ignore_index=True)
        .groupby("origin_area", as_index=False, observed=True)
        .agg(origin_lat=("origin_lat", "median"), origin_lon=("origin_lon", "median"))
    )

    proxy = centroids.rename(columns={
        "origin_area": "unit_bairro_norm",
        "origin_lat": "_proxy_lat", "origin_lon": "_proxy_lon",
    })
    units = units.merge(proxy, on="unit_bairro_norm", how="left", validate="many_to_one")
    units["geo_source"] = np.where(official, "official", "bairro_proxy")
    units["latitude"] = units["latitude"].fillna(units["_proxy_lat"])
    units["longitude"] = units["longitude"].fillna(units["_proxy_lon"])
    city_lat, city_lon = float(loc["latitude"].median()), float(loc["longitude"].median())
    city = units["latitude"].isna() | units["longitude"].isna()
    units.loc[city, "geo_source"] = "city_proxy"
    units["latitude"] = units["latitude"].fillna(city_lat)
    units["longitude"] = units["longitude"].fillna(city_lon)
    units["unit_geo_imputed"] = units["geo_source"].ne("official")
    return units[[
        "unidade", "unit_bairro_norm", "tipo_unidade_norm", "latitude",
        "longitude", "geo_source", "unit_geo_imputed",
    ]], centroids


def build_panel(episodes, units, centroids):
    first = episodes.loc[episodes["primeira_opcao"]].copy()
    first = first.merge(
        centroids, left_on="bairro_norm", right_on="origin_area",
        how="left", validate="many_to_one",
    )
    first["origin_geo_observed"] = first["origin_lat"].notna()
    first["origin_area"] = first["origin_area"].fillna("__SEM_GEO__")
    first["origin_lat"] = first["origin_lat"].fillna(float(units["latitude"].median()))
    first["origin_lon"] = first["origin_lon"].fillna(float(units["longitude"].median()))

    alternatives = episodes[[
        "ano", "grupamento_norm", "alternativa_id", "unidade",
        "horario_norm", "nome_unidade_norm",
    ]].drop_duplicates(["ano", "grupamento_norm", "alternativa_id"])
    alternatives = alternatives.merge(units, on="unidade", how="left", validate="many_to_one")
    if alternatives[["latitude", "longitude"]].isna().any().any():
        raise ValueError("Alternativa sem proxy geografico")

    observed = (
        first.groupby([*MARKET, "alternativa_id"], as_index=False, observed=True)
        .agg(choice_count=("inscricao_id", "nunique"))
    )
    markets = (
        first.groupby(MARKET, as_index=False, observed=True)
        .agg(
            n_choices=("inscricao_id", "nunique"),
            origin_lat=("origin_lat", "first"),
            origin_lon=("origin_lon", "first"),
            origin_geo_observed=("origin_geo_observed", "first"),
        )
    )
    panel = markets.merge(
        alternatives, on=["ano", "grupamento_norm"],
        how="left", validate="many_to_many",
    ).merge(
        observed, on=[*MARKET, "alternativa_id"],
        how="left", validate="one_to_one",
    )
    panel["choice_count"] = panel["choice_count"].fillna(0).astype("int64")
    panel["market_id"] = (
        panel["ano"].astype(str) + "|" + panel["origin_area"].astype(str)
        + "|" + panel["grupamento_norm"].astype(str)
    )
    panel["distance_km"] = haversine(
        panel["origin_lat"], panel["origin_lon"], panel["latitude"], panel["longitude"]
    )
    panel["log_distance"] = np.log1p(panel["distance_km"])
    panel["same_bairro"] = (
        panel["origin_geo_observed"] & panel["origin_area"].eq(panel["unit_bairro_norm"])
    ).fillna(False).astype(float)
    panel["is_partial"] = panel["horario_norm"].eq("PARCIAL").astype(float)
    panel["is_partner"] = panel["unidade"].str.len().eq(5).astype(float)
    panel["is_edi"] = panel["tipo_unidade_norm"].eq("EDI").fillna(False).astype(float)
    panel["unit_geo_imputed"] = panel["unit_geo_imputed"].fillna(True).astype(float)

    got = panel.groupby("market_id", observed=True)["choice_count"].sum()
    expected = panel.groupby("market_id", observed=True)["n_choices"].first()
    if not got.equals(expected.astype("int64")):
        raise AssertionError("Painel nao conserva primeiras escolhas")
    if panel.duplicated(["market_id", "alternativa_id"]).any():
        raise AssertionError("Alternativa duplicada no mercado")

    audit = {
        "n_choice_episodes": int(first["inscricao_id"].nunique()),
        "n_markets": int(panel["market_id"].nunique()),
        "n_active_alternative_cells": int(len(alternatives)),
        "n_panel_rows": int(len(panel)),
        "origin_geo_coverage": float(first["origin_geo_observed"].mean()),
        "unit_geo_official_share": float(alternatives["geo_source"].eq("official").mean()),
        "n_partner_units": int(alternatives.loc[alternatives["unidade"].str.len().eq(5), "unidade"].nunique()),
        "partner_geo_official_share": float(alternatives.loc[alternatives["unidade"].str.len().eq(5), "geo_source"].eq("official").mean()),
    }
    return panel, alternatives, first, audit


def softmax(values, codes, n_groups):
    maximum = np.full(n_groups, -np.inf)
    np.maximum.at(maximum, codes, values)
    exp_value = np.exp(values - maximum[codes])
    total = np.bincount(codes, weights=exp_value, minlength=n_groups)
    return exp_value / total[codes]


@dataclass
class CountConditionalLogit:
    features: list[str]
    l2: float = 0.02
    learning_rate: float = 0.08
    max_iter: int = 120
    tolerance: float = 2e-6

    def fit(self, data):
        x = data[self.features].to_numpy(float)
        y = data["choice_count"].to_numpy(float)
        codes, _ = pd.factorize(data["market_id"], sort=False)
        n_groups = int(codes.max() + 1)
        totals = np.bincount(codes, weights=y, minlength=n_groups)
        self.mean_ = x.mean(axis=0)
        self.scale_ = x.std(axis=0)
        self.scale_[self.scale_ == 0] = 1
        x = (x - self.mean_) / self.scale_
        beta = np.zeros(x.shape[1])
        m = np.zeros_like(beta)
        v = np.zeros_like(beta)
        last = np.inf
        for iteration in range(1, self.max_iter + 1):
            p = softmax(x @ beta, codes, n_groups)
            residual = p * totals[codes] - y
            gradient = x.T @ residual / y.sum() + self.l2 * beta
            m = .9 * m + .1 * gradient
            v = .999 * v + .001 * gradient ** 2
            beta -= self.learning_rate * (m / (1 - .9 ** iteration)) / (
                np.sqrt(v / (1 - .999 ** iteration)) + 1e-8
            )
            if iteration % 10 == 0 or iteration == self.max_iter:
                loss = -np.sum(y * np.log(np.clip(p, 1e-15, 1))) / y.sum()
                loss += .5 * self.l2 * beta @ beta
                if abs(last - loss) < self.tolerance:
                    break
                last = loss
        self.beta_ = beta
        self.iterations_ = iteration
        self.loss_ = float(last)
        probability = softmax(x @ beta, codes, n_groups)
        weighted_mean = np.zeros((n_groups, x.shape[1]))
        np.add.at(weighted_mean, codes, x * probability[:, None])
        information = x.T @ (x * (probability * totals[codes])[:, None])
        information -= (weighted_mean * totals[:, None]).T @ weighted_mean
        information += y.sum() * self.l2 * np.eye(x.shape[1])

        market_score = np.zeros((n_groups, x.shape[1]))
        np.add.at(market_score, codes, x * y[:, None])
        market_score -= weighted_mean * totals[:, None]
        inverse_information = np.linalg.pinv(information)
        covariance = inverse_information @ (market_score.T @ market_score) @ inverse_information
        if n_groups > 1:
            covariance *= n_groups / (n_groups - 1)
        self.standard_errors_ = np.sqrt(np.clip(np.diag(covariance), 0, None))
        self.ci_method_ = "Sanduiche robusto, agrupado por mercado, sobre informacao penalizada"
        return self

    def predict(self, data):
        x = (data[self.features].to_numpy(float) - self.mean_) / self.scale_
        codes, _ = pd.factorize(data["market_id"], sort=False)
        return softmax(x @ self.beta_, codes, int(codes.max() + 1))

    def coefficients(self, model, fold):
        critical_value = 1.959963984540054
        lower = self.beta_ - critical_value * self.standard_errors_
        upper = self.beta_ + critical_value * self.standard_errors_
        estimate_original = self.beta_ / self.scale_
        se_original = self.standard_errors_ / self.scale_
        lower_original = lower / self.scale_
        upper_original = upper / self.scale_
        return pd.DataFrame({
            "model": model,
            "fold": fold,
            "term": self.features,
            "estimate_standardized": self.beta_,
            "standard_error_standardized": self.standard_errors_,
            "ci95_lower_standardized": lower,
            "ci95_upper_standardized": upper,
            "estimate_original_scale": estimate_original,
            "standard_error_original_scale": se_original,
            "ci95_lower_original_scale": lower_original,
            "ci95_upper_original_scale": upper_original,
            "odds_ratio_original_scale": np.exp(np.clip(estimate_original, -700, 700)),
            "odds_ratio_ci95_lower": np.exp(np.clip(lower_original, -700, 700)),
            "odds_ratio_ci95_upper": np.exp(np.clip(upper_original, -700, 700)),
            "training_mean": self.mean_,
            "training_scale": self.scale_,
            "ci_method": self.ci_method_,
            "causal_interpretation": False,
        })


def historical_probabilities(train, target, strength=5.0):
    origin = (
        train.groupby(
            ["origin_area", "grupamento_norm", "alternativa_id"],
            as_index=False, observed=True,
        )["choice_count"].sum().rename(columns={"choice_count": "_origin_count"})
    )
    global_count = (
        train.groupby(["grupamento_norm", "alternativa_id"], as_index=False, observed=True)
        ["choice_count"].sum().rename(columns={"choice_count": "_global_count"})
    )
    scored = target[["market_id", "origin_area", "grupamento_norm", "alternativa_id"]].merge(
        origin, on=["origin_area", "grupamento_norm", "alternativa_id"], how="left"
    ).merge(
        global_count, on=["grupamento_norm", "alternativa_id"], how="left"
    )
    scored["_origin_count"] = scored["_origin_count"].fillna(0)
    scored["_global_count"] = scored["_global_count"].fillna(0)
    denom = scored.groupby("market_id", observed=True)["_global_count"].transform("sum")
    size = scored.groupby("market_id", observed=True)["alternativa_id"].transform("size")
    prior = (scored["_global_count"] + 1) / (denom + size)
    score = scored["_origin_count"] + strength * prior
    return (score / score.groupby(scored["market_id"], observed=True).transform("sum")).to_numpy()


def nearest_probabilities(target):
    minimum = target.groupby("market_id", observed=True)["distance_km"].transform("min")
    chosen = np.isclose(target["distance_km"], minimum, atol=1e-10).astype(float)
    return (chosen / pd.Series(chosen).groupby(target["market_id"].to_numpy()).transform("sum")).to_numpy()


def add_fold_features(panel, episodes, train_years, test_year):
    data = panel.copy()
    train_years = tuple(train_years)
    targets = sorted(set(train_years) | {test_year})
    pieces = []
    first = episodes.loc[episodes["primeira_opcao"]]

    for target_year in targets:
        history_years = tuple(year for year in train_years if year < target_year)
        subset = data.loc[data["ano"].eq(target_year)].copy()
        history_first = first.loc[first["ano"].isin(history_years)]
        history_options = episodes.loc[episodes["ano"].isin(history_years)]

        capacity = (
            history_first.groupby(["grupamento_norm", "unidade"], observed=True)
            .size().rename("lag_first").reset_index()
        )
        pressure = (
            history_options.drop_duplicates(["ano", "inscricao_id", "grupamento_norm", "unidade"])
            .groupby(["grupamento_norm", "unidade"], observed=True)
            .size().rename("lag_list").reset_index()
        )
        subset = subset.merge(capacity, on=["grupamento_norm", "unidade"], how="left")
        subset = subset.merge(pressure, on=["grupamento_norm", "unidade"], how="left")
        subset[["lag_first", "lag_list"]] = subset[["lag_first", "lag_list"]].fillna(0)
        subset["log_lag_first"] = np.log1p(subset["lag_first"])
        subset["log_lag_list"] = np.log1p(subset["lag_list"])

        comp_rows = []
        for group, alt in subset.groupby("grupamento_norm", observed=True):
            unit = alt[["unidade", "latitude", "longitude", "lag_first"]].drop_duplicates("unidade")
            lat = unit["latitude"].to_numpy()
            lon = unit["longitude"].to_numpy()
            distance = haversine(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
            weight = np.exp(-distance / 5.0)
            np.fill_diagonal(weight, 0)
            value = weight @ np.log1p(unit["lag_first"].to_numpy(float))
            comp_rows.append(pd.DataFrame({
                "grupamento_norm": group,
                "unidade": unit["unidade"].to_numpy(),
                "geo_competition": value,
            }))
        subset = subset.merge(
            pd.concat(comp_rows, ignore_index=True),
            on=["grupamento_norm", "unidade"], how="left", validate="many_to_one",
        )

        if history_years:
            lists = history_options.rename(
                columns={"inscricao_id": "choice_id", "unidade": "unit_id"}
            )
            network = build_colisting_network(
                lists, list_col="choice_id", unit_col="unit_id",
                segment_cols=["grupamento_norm"],
            )
            cap_base = pd.concat([
                subset[["grupamento_norm", "unidade"]],
                history_options[["grupamento_norm", "unidade"]],
            ], ignore_index=True).drop_duplicates()
            cap_base = cap_base.merge(
                capacity, on=["grupamento_norm", "unidade"], how="left"
            ).fillna({"lag_first": 0})
            cap_base["capacity_ex_ante"] = cap_base["lag_first"] + 1
            colist = colisting_competition(
                network, cap_base.rename(columns={"unidade": "unit_id"}),
                unit_col="unit_id", capacity_col="capacity_ex_ante",
                segment_cols=["grupamento_norm"],
            ).rename(columns={"unit_id": "unidade"})
            subset = subset.merge(
                colist[["grupamento_norm", "unidade", "competition_colisting", "colisting_weight_sum"]],
                on=["grupamento_norm", "unidade"], how="left", validate="many_to_one",
            )
        else:
            subset["competition_colisting"] = 0.0
            subset["colisting_weight_sum"] = 0.0

        subset[["competition_colisting", "colisting_weight_sum"]] = subset[
            ["competition_colisting", "colisting_weight_sum"]
        ].fillna(0)
        subset["log_geo_competition"] = np.log1p(subset["geo_competition"])
        subset["log_colist_competition"] = np.log1p(subset["competition_colisting"])
        subset["distance_maternal_i"] = (
            subset["log_distance"] * subset["grupamento_norm"].eq("MATERNAL I")
        )
        subset["distance_maternal_ii"] = (
            subset["log_distance"] * subset["grupamento_norm"].eq("MATERNAL II")
        )
        pieces.append(subset)
    return pd.concat(pieces, ignore_index=True)


def metric_rows(data, probability, model, fold, sample, train_units):
    base = data[[
        "ano", "market_id", "grupamento_norm", "alternativa_id", "unidade",
        "horario_norm", "choice_count",
    ]].copy()
    base["probability"] = probability
    base["is_new_unit"] = ~base["unidade"].isin(train_units)
    base["is_partner"] = base["unidade"].str.len().eq(5)

    segment_masks = [
        ("all", np.ones(len(base), dtype=bool)),
        ("incumbent_units", ~base["is_new_unit"].to_numpy()),
        (
            "partner_cold_start",
            (base["is_partner"] & base["is_new_unit"]).to_numpy(),
        ),
        (
            "new_nonpartner",
            (~base["is_partner"] & base["is_new_unit"]).to_numpy(),
        ),
    ]
    rows, unit_parts = [], []
    for segment, mask in segment_masks:
        selected = base.loc[mask].copy()
        if selected.empty:
            continue
        probability_mass = selected.groupby(
            "market_id", observed=True
        )["probability"].transform("sum")
        selected["probability"] = selected["probability"] / probability_mass
        selected["segment_choices"] = selected.groupby(
            "market_id", observed=True
        )["choice_count"].transform("sum")
        selected = selected.loc[selected["segment_choices"].gt(0)].copy()
        if selected.empty:
            continue

        y = selected["choice_count"].to_numpy(float)
        p = np.clip(selected["probability"].to_numpy(float), 1e-15, 1)
        maximum = selected.groupby(
            "market_id", observed=True
        )["probability"].transform("max")
        top = np.isclose(selected["probability"], maximum, atol=1e-12)
        ties = pd.Series(top).groupby(
            selected["market_id"].to_numpy()
        ).transform("sum").to_numpy()
        selected["predicted_demand"] = (
            selected["probability"] * selected["segment_choices"]
        )

        unit = (
            selected.groupby(
                [
                    "ano", "grupamento_norm", "alternativa_id", "unidade",
                    "horario_norm", "is_new_unit", "is_partner",
                ],
                as_index=False, observed=True,
            )
            .agg(
                predicted_demand=("predicted_demand", "sum"),
                observed_demand=("choice_count", "sum"),
            )
        )
        unit["absolute_error"] = (
            unit["predicted_demand"] - unit["observed_demand"]
        ).abs()
        unit["model"], unit["fold"], unit["sample"] = model, fold, sample
        unit["sample_segment"] = segment
        denominator = unit["observed_demand"].sum()
        rows.append({
            "model": model,
            "fold": fold,
            "sample": sample,
            "sample_segment": segment,
            "log_loss": float(-np.sum(y * np.log(p)) / y.sum()),
            "top1": float(np.sum(y * top / ties) / y.sum()),
            "demand_mae": float(unit["absolute_error"].mean()),
            "demand_wape": (
                float(unit["absolute_error"].sum() / denominator)
                if denominator else np.nan
            ),
            "n_choice_episodes": int(y.sum()),
            "n_alternatives": int(len(unit)),
        })
        unit_parts.append(unit)
    return rows, pd.concat(unit_parts, ignore_index=True)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    options = load_query_a(QUERY_A)
    episodes = build_choice_episodes(options)
    units, centroids = load_units()
    panel, alternatives, first, audit = build_panel(episodes, units, centroids)
    print(json.dumps(audit, ensure_ascii=False, indent=2))

    metric_output, demand_output, coefficient_output = [], [], []
    distance_features = ["log_distance"]
    attribute_features = [
        "log_distance", "same_bairro", "is_partial", "is_partner", "is_edi",
        "unit_geo_imputed", "log_lag_first", "log_lag_list",
    ]
    full_features = attribute_features + [
        "log_geo_competition", "log_colist_competition",
        "distance_maternal_i", "distance_maternal_ii",
    ]

    for fold in STANDARD_FOLDS:
        print(f"Estimando {fold.name}")
        featured = add_fold_features(panel, episodes, fold.train_years, fold.test_year)
        train = featured.loc[featured["ano"].isin(fold.train_years)].reset_index(drop=True)
        test = featured.loc[featured["ano"].eq(fold.test_year)].reset_index(drop=True)
        train_units = set(episodes.loc[episodes["ano"].isin(fold.train_years), "unidade"])

        predictions = {
            "historical_share": (
                historical_probabilities(train, train),
                historical_probabilities(train, test),
                None,
            ),
            "nearest_unit": (
                nearest_probabilities(train),
                nearest_probabilities(test),
                None,
            ),
        }
        for name, features in [
            ("conditional_logit_distance", distance_features),
            ("conditional_logit_attributes", attribute_features),
            ("conditional_logit_full", full_features),
        ]:
            print(f"  {name}")
            model = CountConditionalLogit(features).fit(train)
            predictions[name] = (model.predict(train), model.predict(test), model)

        for name, (pred_train, pred_test, model) in predictions.items():
            for sample, data, probability in [
                ("in_sample", train, pred_train),
                ("oos", test, pred_test),
            ]:
                rows, demand = metric_rows(
                    data, probability, name, fold.name, sample, train_units
                )
                metric_output.extend(rows)
                demand_output.append(demand)
            if model is not None:
                coefficient_output.append(model.coefficients(name, fold.name))

    metrics = pd.DataFrame(metric_output)
    demand = pd.concat(demand_output, ignore_index=True)
    coefficients = pd.concat(coefficient_output, ignore_index=True)

    alternatives_out = alternatives[[
        "ano", "grupamento_norm", "alternativa_id", "unidade", "horario_norm",
        "nome_unidade_norm", "unit_bairro_norm", "tipo_unidade_norm", "geo_source",
    ]].copy()
    alternatives_out.to_csv(OUT / "alternative_universe.csv", index=False)
    metrics.to_csv(OUT / "model_metrics.csv", index=False)
    demand.to_csv(OUT / "conditional_demand.csv", index=False)
    coefficients.to_csv(OUT / "model_coefficients.csv", index=False)

    oos = metrics.query("sample == 'oos' and sample_segment == 'all'").copy()
    display = oos[[
        "fold", "model", "log_loss", "top1", "demand_mae", "demand_wape",
    ]].round(4)
    selection_pool = metrics.loc[
        metrics["sample"].eq("oos")
        & (
            (metrics["fold"].eq("oos_2024") & metrics["sample_segment"].eq("incumbent_units"))
            | (metrics["fold"].eq("oos_2025") & metrics["sample_segment"].eq("all"))
        )
    ].copy()
    selected = (
        selection_pool.sort_values(["fold", "log_loss"])
        .groupby("fold", as_index=False).first()[
            ["fold", "sample_segment", "model", "log_loss", "demand_wape"]
        ]
    )
    result_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit": audit,
        "metrics": display.to_dict(orient="records"),
        "selected_by_log_loss": selected.round(4).to_dict(orient="records"),
        "note": "OOS-2024 seleciona em incumbentes; parceiras sao cold start. OOS-2025 seleciona na amostra completa.",
    }
    FRONTEND_RESULTS.write_text(
        json.dumps(result_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "run_id": "full_alternatives_partner_break_v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            str(QUERY_A.relative_to(ROOT)): file_hash(QUERY_A),
            str(QUERY_D.relative_to(ROOT)): file_hash(QUERY_D),
            str(LOCATIONS.relative_to(ROOT)): file_hash(LOCATIONS),
        },
        "choice_set": "Todas as alternativas unidade-turno observadas como ativas no ano e grupamento, para cada area de origem.",
        "origin_geography": "Centroide mediano das unidades no bairro; centroide municipal quando ausente.",
        "capacity_concept": "Nenhuma capacidade inferida. Demanda e pressao de lista defasadas entram como atributos.",
        "folds": [
            {"fold": f.name, "train_years": list(f.train_years), "target_year": f.test_year}
            for f in STANDARD_FOLDS
        ],
        "audit": audit,
        "selected_by_log_loss": selected.to_dict(orient="records"),
        "evaluation_regime": "OOS-2024: incumbentes para selecao e parceiras separadas; OOS-2025: amostra completa.",
        "tests_required": ["probability_sum", "demand_conservation", "temporal_split"],
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(display.to_string(index=False))
    print("\nSelecionados por log loss:")
    print(selected.to_string(index=False))


if __name__ == "__main__":
    run()
