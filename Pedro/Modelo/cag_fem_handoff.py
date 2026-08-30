from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
import warnings

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import spearmanr
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import OneHotEncoder

import f1c_est


# The estimator is deterministic, but the project-wide seed is fixed for reproducibility.
np.random.seed(42)

MODEL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODEL_DIR / "results"
OUTPUT_DIR = MODEL_DIR / "handoff_f1_cag_fem"
STOCK_PATH = RESULTS_DIR / "f1_cov_caged_anual.csv"
BASELINE_PATH = RESULTS_DIR / "f1c_oos_pred.csv"

TEST_YEAR = 2025
TRAIN_END = 2024
MUNICIPALITY = "Rio de Janeiro"
MUNICIPALITY_CODE = 3304557
LAST_PRE_CUTOFF_MONTH = 9

# Official public Novo CAGED dashboard published by the Ministry of Labor and Employment.
POWERBI_REPORT_URL = (
    "https://app.powerbi.com/view?pageName=ReportSectionb52b07ec3b5f3ac6c749"
    "&r=eyJrIjoiNWI5NWI0ODEtYmZiYy00Mjg3LTkzNWUtY2UyYjIwMDE1YWI2IiwidCI6"
    "IjNlYzkyOTY5LTVhNTEtNGYxOC04YWM5LWVmOThmYmFmYTk3OCJ9"
)
POWERBI_RESOURCE_KEY = "5b95b481-bfbc-4287-935e-ce2b20015ab6"
POWERBI_API = "https://wabi-brazil-south-d-primary-api.analysis.windows.net"


SPECIFICATIONS = [
    {
        "name": "PPML-FE + Caged feminino pre-corte",
        "include_trend": True,
        "last_month": 9,
        "train_start": 2021,
        "main": True,
    },
    {
        "name": "PPML-FE Caged feminino sem tendencia",
        "include_trend": False,
        "last_month": 9,
        "train_start": 2021,
        "main": False,
    },
    {
        "name": "PPML-FE + Caged feminino corte agosto",
        "include_trend": True,
        "last_month": 8,
        "train_start": 2021,
        "main": False,
    },
    {
        "name": "PPML-FE + Caged feminino sem 2021",
        "include_trend": True,
        "last_month": 9,
        "train_start": 2022,
        "main": False,
    },
]


def request_json(url, method="GET", payload=None):
    """Call the official public dashboard without requiring local credentials."""
    headers = {
        "ActivityId": "00000000-0000-0000-0000-000000000042",
        "RequestId": "00000000-0000-0000-0000-000000000142",
        "X-PowerBI-ResourceKey": POWERBI_RESOURCE_KEY,
        "Origin": "https://app.powerbi.com",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=90) as response:
        content = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip" or content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        return json.loads(content.decode("utf-8"))


def get_model_id():
    """Resolve the current semantic-model identifier used by the public report."""
    url = (
        f"{POWERBI_API}/public/reports/{POWERBI_RESOURCE_KEY}/"
        "modelsAndExploration?preferReadOnlySession=true"
    )
    metadata = request_json(url)
    models = metadata.get("models", [])
    if len(models) != 1:
        raise ValueError(f"Expected one Novo CAGED model; found {len(models)}.")
    return int(models[0]["id"])


def build_query(model_id):
    """Build a monthly query for female formal-job flows in Rio de Janeiro city."""
    source = lambda name, entity: {"Name": name, "Entity": entity, "Type": 0}
    column = lambda source_name, prop: {
        "Expression": {"SourceRef": {"Source": source_name}},
        "Property": prop,
    }
    selections = [
        {"Column": column("d", "competência"), "Name": "d.competência"},
    ]
    for property_name in ["Admitidos", "Desligados", "Saldo"]:
        selections.append(
            {
                "Aggregation": {
                    "Expression": {"Column": column("d", property_name)},
                    "Function": 0,
                },
                "Name": f"Sum(d.{property_name})",
            }
        )
    filters = [
        {
            "Condition": {
                "In": {
                    "Expressions": [{"Column": column("s", "Sexo.1")}],
                    "Values": [[{"Literal": {"Value": "'Mulher'"}}]],
                }
            }
        },
        {
            "Condition": {
                "In": {
                    "Expressions": [{"Column": column("g", "Município")}],
                    "Values": [[{"Literal": {"Value": f"'{MUNICIPALITY}'"}}]],
                }
            }
        },
    ]
    command = {
        "SemanticQueryDataShapeCommand": {
            "Query": {
                "Version": 2,
                "From": [
                    source("d", "Dados - Movimentações"),
                    source("g", "Geográfico"),
                    source("s", "Sexo"),
                ],
                "Select": selections,
                "Where": filters,
            },
            "Binding": {
                "DataReduction": {
                    "DataVolume": 3,
                    "Primary": {"Window": {"Count": 500}},
                },
                "Primary": {"Groupings": [{"Projections": [0, 1, 2, 3]}]},
                "Version": 1,
            },
            "ExecutionMetricsKind": 1,
        }
    }
    return {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {"Commands": [command]},
                "ApplicationContext": {"DatasetId": str(model_id)},
            }
        ],
        "cancelQueries": [],
        "modelId": model_id,
    }


def decode_powerbi_rows(rows, number_of_columns):
    """Decode Power BI's compact row representation, including repeated values."""
    decoded = []
    previous = [None] * number_of_columns
    for raw_row in rows:
        compressed_values = iter(raw_row.get("C", []))
        repeated_mask = int(raw_row.get("R", 0))
        current = []
        for index in range(number_of_columns):
            if repeated_mask & (1 << index):
                current.append(previous[index])
            else:
                current.append(next(compressed_values, None))
        decoded.append(current)
        previous = current
    return decoded


def extract_female_caged():
    """Extract official monthly female admissions, dismissals, and net balance."""
    model_id = get_model_id()
    url = f"{POWERBI_API}/public/reports/querydata?synchronous=true"
    response = request_json(url, method="POST", payload=build_query(model_id))
    try:
        data = response["results"][0]["result"]["data"]
        rows = data["dsr"]["DS"][0]["PH"][0]["DM0"]
    except (KeyError, IndexError) as error:
        raise ValueError("The Novo CAGED dashboard returned an unexpected schema.") from error
    decoded = decode_powerbi_rows(rows, number_of_columns=4)
    monthly = pd.DataFrame(
        decoded,
        columns=["competencia", "admissoes_fem", "desligamentos_fem", "saldo_fem"],
    )
    monthly["competencia"] = pd.to_numeric(monthly["competencia"], errors="raise").astype(int)
    for column_name in ["admissoes_fem", "desligamentos_fem", "saldo_fem"]:
        monthly[column_name] = pd.to_numeric(monthly[column_name], errors="raise").astype(int)
    monthly["ano"] = monthly["competencia"] // 100
    monthly["mes"] = monthly["competencia"] % 100
    monthly["municipio"] = MUNICIPALITY
    monthly["codigo_municipio_ibge"] = MUNICIPALITY_CODE
    monthly["sexo"] = "Mulher"
    monthly["extraido_em_utc"] = datetime.now(timezone.utc).isoformat()
    monthly["fonte"] = POWERBI_REPORT_URL
    return monthly.sort_values("competencia").reset_index(drop=True), model_id


def build_features(monthly, last_month):
    """Use only female flows available before each target-year enrollment process.

    The numerator is female net formal-job creation from January through the cutoff in
    t-1. The denominator is total municipal formal employment at the start of t-1.
    This is a labor-market flow indicator, not a female employment-stock measure.
    """
    stock = pd.read_csv(STOCK_PATH).set_index("ano_indicador")
    rows = []
    for target_year in range(f1c_est.TRAIN_START, TEST_YEAR + 1):
        indicator_year = target_year - 1
        period = monthly[
            monthly["ano"].eq(indicator_year)
            & monthly["mes"].between(1, last_month)
        ]
        if len(period) != last_month:
            raise ValueError(
                f"Expected {last_month} months for {indicator_year}; found {len(period)}."
            )
        initial_total_stock = float(stock.loc[indicator_year, "estoque_inicio_reconstruido"])
        rows.append(
            {
                "ano_alvo": target_year,
                "ano_caged": indicator_year,
                "mes_corte": last_month,
                "admissoes_fem_jan_corte": int(period["admissoes_fem"].sum()),
                "desligamentos_fem_jan_corte": int(period["desligamentos_fem"].sum()),
                "saldo_fem_jan_corte": int(period["saldo_fem"].sum()),
                "estoque_formal_total_inicio": initial_total_stock,
            }
        )
    features = pd.DataFrame(rows)
    features["cag_fem_taxa"] = (
        features["saldo_fem_jan_corte"] / features["estoque_formal_total_inicio"]
    )
    training = features[features["ano_alvo"].le(TRAIN_END)]["cag_fem_taxa"]
    mean = float(training.mean())
    std = float(training.std(ddof=0))
    if std <= 0:
        raise ValueError("Female CAGED feature has no training variation.")
    features["cag_fem_z"] = (features["cag_fem_taxa"] - mean) / std
    features["media_treino"] = mean
    features["desvio_treino"] = std
    return features


def prepare_samples():
    """Reuse the verified Front 1 gross child-unit target and continuing-unit universe."""
    _, counts, names, exposure = f1c_est.load_child_unit_demand()
    predicted_exposure = f1c_est.load_front1_exposure()
    previous_units = set(counts.loc[counts["ano"].eq(TRAIN_END), "codigo_unidade"])
    test_units = set(counts.loc[counts["ano"].eq(TEST_YEAR), "codigo_unidade"])
    continuing_units = sorted(previous_units & test_units)
    train = f1c_est.build_training_panel(counts, continuing_units, exposure)
    test = counts[
        counts["ano"].eq(TEST_YEAR)
        & counts["codigo_unidade"].isin(continuing_units)
    ].copy()
    test = test.merge(names, how="left", on="codigo_unidade")
    test["ano_teste"] = TEST_YEAR
    return train, test, predicted_exposure


def fit_model(train, features, specification):
    """Estimate unit effects plus common trend and pre-cutoff female CAGED variation."""
    estimation = train.merge(
        features[["ano_alvo", "cag_fem_z"]],
        how="left",
        left_on="ano",
        right_on="ano_alvo",
        validate="many_to_one",
    )
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    unit_block = encoder.fit_transform(estimation[["codigo_unidade"]])
    blocks = [unit_block]
    coefficient_names = []
    if specification["include_trend"]:
        blocks.append(sparse.csr_matrix(estimation[["tendencia"]].to_numpy(float)))
        coefficient_names.append("tendencia")
    blocks.append(sparse.csr_matrix(estimation[["cag_fem_z"]].to_numpy(float)))
    coefficient_names.append("cag_fem_z")
    design = sparse.hstack(blocks, format="csr")
    exposure = estimation["exposicao_criancas"].to_numpy(float)
    rate = estimation["demanda_observada"].to_numpy(float) / exposure
    model = PoissonRegressor(
        alpha=f1c_est.RIDGE_ALPHA,
        fit_intercept=True,
        solver="newton-cholesky",
        max_iter=200,
        tol=1e-8,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=ConvergenceWarning)
        model.fit(design, rate, sample_weight=exposure)
    numeric_start = unit_block.shape[1]
    numeric_coefficients = dict(
        zip(coefficient_names, model.coef_[numeric_start:])
    )
    unit_coefficients = pd.DataFrame(
        {
            "codigo_unidade": encoder.categories_[0],
            "coef_efeito_unidade": model.coef_[:numeric_start],
        }
    )
    return model, encoder, numeric_coefficients, unit_coefficients


def predict_model(model, encoder, test, features, specification, predicted_exposure):
    """Predict 2025 gross child-unit demand without using any 2025 CAGED observation."""
    prediction = test.merge(
        features[["ano_alvo", "cag_fem_z"]],
        how="left",
        left_on="ano",
        right_on="ano_alvo",
        validate="many_to_one",
    )
    prediction["tendencia"] = TEST_YEAR - f1c_est.TRAIN_START
    blocks = [encoder.transform(prediction[["codigo_unidade"]])]
    if specification["include_trend"]:
        blocks.append(sparse.csr_matrix(prediction[["tendencia"]].to_numpy(float)))
    blocks.append(sparse.csr_matrix(prediction[["cag_fem_z"]].to_numpy(float)))
    design = sparse.hstack(blocks, format="csr")
    prediction["previsto"] = model.predict(design) * predicted_exposure
    return prediction


def metrics(prediction, model_name):
    """Calculate facility-level errors without allowing signed cancellation."""
    actual = prediction["demanda_observada"].to_numpy(float)
    predicted = prediction["previsto"].to_numpy(float)
    error = predicted - actual
    return {
        "ano_teste": TEST_YEAR,
        "modelo": model_name,
        "n_unidades": len(prediction),
        "observado_total": actual.sum(),
        "previsto_total": predicted.sum(),
        "wape": np.abs(error).sum() / actual.sum(),
        "mae": np.abs(error).mean(),
        "rmse": np.sqrt(np.mean(error**2)),
        "vies_relativo": error.sum() / actual.sum(),
        "spearman": spearmanr(actual, predicted).statistic,
    }


def sha256(path):
    """Return a portable integrity hash for each handoff artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    monthly, model_id = extract_female_caged()
    features_by_cutoff = {
        month: build_features(monthly, month)
        for month in sorted({item["last_month"] for item in SPECIFICATIONS})
    }
    train, test, predicted_exposure = prepare_samples()
    baseline = pd.read_csv(BASELINE_PATH)
    baseline["codigo_unidade"] = baseline["codigo_unidade"].astype(str)
    test["codigo_unidade"] = test["codigo_unidade"].astype(str)
    baseline = test.merge(
        baseline[["codigo_unidade", "prev_modelo", "prev_persistencia"]],
        on="codigo_unidade",
        how="left",
        validate="one_to_one",
    )

    metric_rows = []
    coefficient_rows = []
    main_prediction = None
    main_unit_coefficients = None
    for specification in SPECIFICATIONS:
        features = features_by_cutoff[specification["last_month"]]
        estimation_sample = train[train["ano"].ge(specification["train_start"])]
        model, encoder, numeric_coefficients, unit_coefficients = fit_model(
            estimation_sample, features, specification
        )
        prediction = predict_model(
            model, encoder, test, features, specification, predicted_exposure
        )
        metric_rows.append(metrics(prediction, specification["name"]))
        coefficient_rows.append(
            {
                "modelo": specification["name"],
                "intercepto": float(model.intercept_),
                "coef_tendencia": numeric_coefficients.get("tendencia", np.nan),
                "coef_cag_fem_z": numeric_coefficients["cag_fem_z"],
                "ridge_alpha": f1c_est.RIDGE_ALPHA,
                "inicio_treino": specification["train_start"],
                "fim_treino": TRAIN_END,
                "mes_corte": specification["last_month"],
                "media_cag_fem_treino": float(features["media_treino"].iloc[0]),
                "desvio_cag_fem_treino": float(features["desvio_treino"].iloc[0]),
                "exposicao_prevista_2025": predicted_exposure,
            }
        )
        if specification["main"]:
            main_prediction = prediction
            main_unit_coefficients = unit_coefficients

    baseline_model = baseline.rename(columns={"prev_modelo": "previsto"})
    persistence = baseline.rename(columns={"prev_persistencia": "previsto"})
    metric_rows.append(metrics(baseline_model, "PPML-FE base"))
    metric_rows.append(metrics(persistence, "Persistencia taxa t-1"))
    metric_table = pd.DataFrame(metric_rows)
    base_wape = float(metric_table.loc[metric_table["modelo"].eq("PPML-FE base"), "wape"].iloc[0])
    persistence_wape = float(
        metric_table.loc[metric_table["modelo"].eq("Persistencia taxa t-1"), "wape"].iloc[0]
    )
    metric_table["delta_wape_pp_vs_base"] = 100 * (metric_table["wape"] - base_wape)
    metric_table["delta_wape_pp_vs_persistencia"] = 100 * (
        metric_table["wape"] - persistence_wape
    )

    predictions = main_prediction[
        ["ano_teste", "codigo_unidade", "nome_unidade", "demanda_observada", "previsto"]
    ].rename(columns={"previsto": "prev_f1_cag_fem"})
    predictions = predictions.merge(
        baseline[["codigo_unidade", "prev_modelo", "prev_persistencia"]],
        on="codigo_unidade",
        how="left",
        validate="one_to_one",
    )
    predictions["erro_abs_cag_fem"] = (
        predictions["prev_f1_cag_fem"] - predictions["demanda_observada"]
    ).abs()

    monthly_output = monthly[monthly["ano"].between(2020, 2024)].copy()
    feature_output = pd.concat(
        [
            frame.assign(cenario_corte=f"jan-{month:02d}")
            for month, frame in features_by_cutoff.items()
        ],
        ignore_index=True,
    )
    main_unit_coefficients["modelo"] = "PPML-FE + Caged feminino pre-corte"
    outputs = {
        "cag_fem_mensal.csv": monthly_output,
        "cag_fem_feat.csv": feature_output,
        "coef_modelo.csv": pd.DataFrame(coefficient_rows),
        "coef_unidades.csv": main_unit_coefficients,
        "prev_creche_2025.csv": predictions,
        "metricas_2025.csv": metric_table,
    }
    for filename, frame in outputs.items():
        frame.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "front": 1,
        "front_2_executed": False,
        "target": "gross distinct child-unit demand for every selected facility",
        "test_year": TEST_YEAR,
        "training_years": [2021, 2022, 2023, 2024],
        "municipality": MUNICIPALITY,
        "municipality_code_ibge": MUNICIPALITY_CODE,
        "female_caged_definition": (
            "female net formal-job flow from January through September of t-1, "
            "divided by total formal employment at the start of t-1"
        ),
        "source_report": POWERBI_REPORT_URL,
        "source_model_id_at_extraction": model_id,
        "files": {},
    }
    for filename in outputs:
        path = OUTPUT_DIR / filename
        manifest["files"][filename] = {"sha256": sha256(path), "rows": len(outputs[filename])}
    readme_path = OUTPUT_DIR / "README.md"
    if readme_path.exists():
        manifest["files"]["README.md"] = {
            "sha256": sha256(readme_path),
            "bytes": readme_path.stat().st_size,
        }
    manifest["files"]["../cag_fem_handoff.py"] = {
        "sha256": sha256(Path(__file__).resolve()),
        "bytes": Path(__file__).resolve().stat().st_size,
    }
    with (OUTPUT_DIR / "manifesto.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

    print(metric_table.round(6).to_string(index=False))
    print(f"\nHandoff saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
