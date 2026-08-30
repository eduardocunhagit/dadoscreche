from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import spearmanr
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import OneHotEncoder

import f1c_est


# Reproducibility: all estimators are deterministic, but the project seed remains fixed.
np.random.seed(42)

MODEL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODEL_DIR / "results"
FIGURES_DIR = MODEL_DIR / "figures"
CAGED_MONTHLY_PATH = RESULTS_DIR / "f1_cov_caged_mensal.csv"
CAGED_ANNUAL_PATH = RESULTS_DIR / "f1_cov_caged_anual.csv"
RAIS_VINTAGES_PATH = RESULTS_DIR / "f1_cov_rais_vintages.csv"

TEST_YEAR = 2025
TRAIN_END = 2024


SPECIFICATIONS = [
    {
        "name": "PPML-FE + Caged pre-corte",
        "include_trend": True,
        "last_month": 9,
        "train_start": 2021,
    },
    {
        "name": "PPML-FE Caged pre-corte sem tendencia",
        "include_trend": False,
        "last_month": 9,
        "train_start": 2021,
    },
    {
        "name": "PPML-FE + Caged corte agosto",
        "include_trend": True,
        "last_month": 8,
        "train_start": 2021,
    },
    {
        "name": "PPML-FE + Caged sem 2021",
        "include_trend": True,
        "last_month": 9,
        "train_start": 2022,
    },
]


def build_safe_caged_feature(last_month=9):
    """Create a conservative pre-enrollment municipal Caged indicator.

    For target year t, only January through last_month of t-1 is used. The outcome is the
    accumulated net formal-job flow divided by formal employment at the start of t-1.
    September data precede the November/December enrollment origins in the source data.
    """
    monthly = pd.read_csv(CAGED_MONTHLY_PATH)
    annual = pd.read_csv(CAGED_ANNUAL_PATH).set_index("ano_indicador")
    rows = []
    for target_year in range(2021, 2026):
        indicator_year = target_year - 1
        available = monthly[
            monthly["ano"].eq(indicator_year)
            & monthly["mes"].between(1, last_month)
        ].copy()
        if len(available) != last_month:
            raise ValueError(
                f"Expected {last_month} pre-cutoff Caged months for {indicator_year}; "
                f"found {len(available)}."
            )
        initial_stock = float(
            annual.loc[indicator_year, "estoque_inicio_reconstruido"]
        )
        net_flow = float(available["saldo"].sum())
        rows.append(
            {
                "ano": target_year,
                "ano_caged": indicator_year,
                "ultimo_mes_disponivel": last_month,
                "saldo_jan_corte": net_flow,
                "estoque_inicio": initial_stock,
                "caged_taxa_pre_corte": net_flow / initial_stock,
            }
        )
    feature = pd.DataFrame(rows)
    train_values = feature.loc[
        feature["ano"].le(TRAIN_END), "caged_taxa_pre_corte"
    ]
    feature_mean = float(train_values.mean())
    feature_std = float(train_values.std(ddof=0))
    if feature_std <= 0:
        raise ValueError("The pre-cutoff Caged feature has no training variation.")
    feature["caged_pre_corte_z"] = (
        feature["caged_taxa_pre_corte"] - feature_mean
    ) / feature_std
    feature["media_treino"] = feature_mean
    feature["desvio_treino"] = feature_std
    return feature


def prepare_unit_samples():
    """Reuse the exact Front 1 child-unit target and continuing-unit universe."""
    child_units, counts, names, exposure = f1c_est.load_child_unit_demand()
    predicted_exposure = f1c_est.load_front1_exposure()
    previous_units = set(
        counts.loc[counts["ano"].eq(TRAIN_END), "codigo_unidade"]
    )
    test_units = set(counts.loc[counts["ano"].eq(TEST_YEAR), "codigo_unidade"])
    continuing_units = sorted(previous_units & test_units)
    train = f1c_est.build_training_panel(counts, continuing_units, exposure)
    test = counts[
        counts["ano"].eq(TEST_YEAR)
        & counts["codigo_unidade"].isin(continuing_units)
    ].copy()
    test = test.merge(names, how="left", on="codigo_unidade")
    test["ano_teste"] = TEST_YEAR
    return child_units, train, test, exposure, predicted_exposure


def fit_caged_model(train, feature, specification):
    """Fit unit effects with a common, strictly pre-cutoff municipal Caged feature.

    Caged has no cross-unit variation, so it can only change the common annual scale.
    It cannot explain which facilities gain demand relative to their competitors.
    """
    estimation = train.merge(
        feature[["ano", "caged_pre_corte_z"]],
        how="left",
        on="ano",
        validate="many_to_one",
    )
    if estimation["caged_pre_corte_z"].isna().any():
        raise ValueError("Missing pre-cutoff Caged values in the estimation panel.")

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    blocks = [encoder.fit_transform(estimation[["codigo_unidade"]])]
    numeric_names = []
    if specification["include_trend"]:
        blocks.append(
            sparse.csr_matrix(estimation[["tendencia"]].to_numpy(dtype=float))
        )
        numeric_names.append("tendencia")
    blocks.append(
        sparse.csr_matrix(
            estimation[["caged_pre_corte_z"]].to_numpy(dtype=float)
        )
    )
    numeric_names.append("caged_pre_corte_z")
    design = sparse.hstack(blocks, format="csr")

    sample_exposure = estimation["exposicao_criancas"].to_numpy(dtype=float)
    rate = estimation["demanda_observada"].to_numpy(dtype=float) / sample_exposure
    model = PoissonRegressor(
        alpha=f1c_est.RIDGE_ALPHA,
        fit_intercept=True,
        solver="newton-cholesky",
        max_iter=200,
        tol=1e-8,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=ConvergenceWarning)
        model.fit(design, rate, sample_weight=sample_exposure)

    coefficient_offset = design.shape[1] - len(numeric_names)
    numeric_coefficients = dict(
        zip(numeric_names, model.coef_[coefficient_offset:])
    )
    return model, encoder, numeric_coefficients


def predict_caged_model(
    model,
    encoder,
    test,
    feature,
    specification,
    predicted_exposure,
):
    """Predict the 2025 child-unit count without using 2025 Caged data."""
    prediction = test.merge(
        feature[["ano", "caged_pre_corte_z"]],
        how="left",
        on="ano",
        validate="many_to_one",
    )
    prediction["tendencia"] = TEST_YEAR - f1c_est.TRAIN_START
    blocks = [encoder.transform(prediction[["codigo_unidade"]])]
    if specification["include_trend"]:
        blocks.append(
            sparse.csr_matrix(prediction[["tendencia"]].to_numpy(dtype=float))
        )
    blocks.append(
        sparse.csr_matrix(
            prediction[["caged_pre_corte_z"]].to_numpy(dtype=float)
        )
    )
    design = sparse.hstack(blocks, format="csr")
    prediction["previsto"] = model.predict(design) * predicted_exposure
    return prediction


def calculate_metrics(predictions, model_name, evaluation):
    """Calculate per-facility errors without signed cancellation."""
    actual = predictions["demanda_observada"].to_numpy(dtype=float)
    predicted = predictions["previsto"].to_numpy(dtype=float)
    error = predicted - actual
    absolute_error = np.abs(error)
    return {
        "ano_teste": TEST_YEAR,
        "avaliacao": evaluation,
        "modelo": model_name,
        "n_unidades": len(predictions),
        "observado_total": actual.sum(),
        "previsto_total": predicted.sum(),
        "wape": absolute_error.sum() / actual.sum(),
        "mae": absolute_error.mean(),
        "mediana_ae": np.median(absolute_error),
        "rmse": np.sqrt(np.mean(error**2)),
        "vies_relativo": error.sum() / actual.sum(),
        "spearman": spearmanr(actual, predicted).statistic,
    }


def add_conditional_prediction(predictions):
    """Rescale to the realized total only for an allocation diagnostic."""
    result = predictions.copy()
    observed_total = float(result["demanda_observada"].sum())
    predicted_total = float(result["previsto"].sum())
    result["previsto"] = result["previsto"] * observed_total / predicted_total
    return result


def load_baselines(test):
    """Load the already verified Front 1 baseline and persistence predictions."""
    baseline = pd.read_csv(RESULTS_DIR / "f1c_oos_pred.csv")
    baseline = baseline[
        ["codigo_unidade", "prev_modelo", "prev_persistencia"]
    ].copy()
    expected_codes = set(test["codigo_unidade"].astype(str))
    baseline["codigo_unidade"] = baseline["codigo_unidade"].astype(str)
    if set(baseline["codigo_unidade"]) != expected_codes:
        raise ValueError("Baseline and Caged tests do not use the same facility universe.")
    return test.merge(
        baseline,
        how="left",
        on="codigo_unidade",
        validate="one_to_one",
    )


def build_diagnostics(feature, coefficients, rais_vintages):
    """Record the effective time variation and ex-ante admissibility limits."""
    train_feature = feature[feature["ano"].le(TRAIN_END)].copy()
    time_design = np.column_stack(
        [
            np.ones(len(train_feature)),
            train_feature["ano"].to_numpy(dtype=float) - f1c_est.TRAIN_START,
            train_feature["caged_pre_corte_z"].to_numpy(dtype=float),
        ]
    )
    latest_rais_year = int(rais_vintages["ano_rais"].max())
    maximum_revision = float(rais_vintages["revisao_vs_primeira_pct"].max())
    rows = [
        {"indicador": "ano_oos", "valor": TEST_YEAR},
        {"indicador": "anos_independentes_treino_caged", "valor": len(train_feature)},
        {"indicador": "variacao_caged_dentro_ano", "valor": 0.0},
        {
            "indicador": "correlacao_caged_tendencia_treino",
            "valor": train_feature[["ano", "caged_taxa_pre_corte"]]
            .corr()
            .iloc[0, 1],
        },
        {"indicador": "condicao_design_tempo", "valor": np.linalg.cond(time_design)},
        {"indicador": "ultimo_ano_rais_local", "valor": latest_rais_year},
        {"indicador": "maior_revisao_rais_pct", "valor": maximum_revision},
        {
            "indicador": "veredito_rais",
            "valor": "nao estimar: municipal, local do estabelecimento, defasada e revisada",
        },
    ]
    for model_name, model_coefficients in coefficients.items():
        rows.append(
            {
                "indicador": f"coef_caged_padronizado__{model_name}",
                "valor": model_coefficients["caged_pre_corte_z"],
            }
        )
    return pd.DataFrame(rows)


def save_figure(metrics):
    """Compare only Front 1 variants and persistence in the 2025 OOS."""
    end_to_end = metrics[
        metrics["avaliacao"].eq("Ponta a ponta com total previsto pela Frente 1")
    ].copy()
    labels = {
        "PPML-FE base": "Base",
        "PPML-FE + Caged pre-corte": "Caged + tendência",
        "PPML-FE Caged pre-corte sem tendencia": "Caged sem tendência",
        "PPML-FE + Caged corte agosto": "Caged até agosto",
        "PPML-FE + Caged sem 2021": "Caged sem 2021",
        "Persistencia taxa t-1": "Persistência",
    }
    end_to_end["rotulo"] = end_to_end["modelo"].map(labels)
    color_map = {
        "PPML-FE base": "#2C7FB8",
        "PPML-FE + Caged pre-corte": "#008C8C",
        "PPML-FE Caged pre-corte sem tendencia": "#76B7B2",
        "PPML-FE + Caged corte agosto": "#4E9F85",
        "PPML-FE + Caged sem 2021": "#9C755F",
        "Persistencia taxa t-1": "#F28E2B",
    }
    colors = end_to_end["modelo"].map(color_map)
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.4))
    axes[0].bar(end_to_end["rotulo"], 100 * end_to_end["wape"], color=colors)
    axes[0].set_ylabel("WAPE (%)")
    axes[0].set_title("Erro por creche")
    axes[0].tick_params(axis="x", rotation=18)
    axes[0].grid(axis="y", alpha=0.2)
    axes[1].bar(
        end_to_end["rotulo"],
        100 * end_to_end["vies_relativo"],
        color=colors,
    )
    axes[1].axhline(0, color="#17324D", linewidth=1)
    axes[1].set_ylabel("Viés agregado (%)")
    axes[1].set_title("Calibração do total")
    axes[1].tick_params(axis="x", rotation=18)
    axes[1].grid(axis="y", alpha=0.2)
    fig.suptitle("CAGED pré-corte na demanda bruta por creche - OOS 2025")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "f1c_cag_oos.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    features = {
        month: build_safe_caged_feature(last_month=month)
        for month in sorted({item["last_month"] for item in SPECIFICATIONS})
    }
    feature = features[9]
    _, train, test, _, predicted_exposure = prepare_unit_samples()
    baseline = load_baselines(test)
    rais_vintages = pd.read_csv(RAIS_VINTAGES_PATH)

    prediction_frames = []
    metric_rows = []
    coefficient_rows = {}

    baseline_models = [
        ("PPML-FE base", "prev_modelo"),
        ("Persistencia taxa t-1", "prev_persistencia"),
    ]
    for model_name, column in baseline_models:
        predictions = baseline[
            ["ano_teste", "codigo_unidade", "nome_unidade", "demanda_observada"]
        ].copy()
        predictions["modelo"] = model_name
        predictions["previsto"] = baseline[column]
        prediction_frames.append(predictions)
        metric_rows.append(
            calculate_metrics(
                predictions,
                model_name,
                "Ponta a ponta com total previsto pela Frente 1",
            )
        )
        metric_rows.append(
            calculate_metrics(
                add_conditional_prediction(predictions),
                model_name,
                "Distribuicao condicional ao total observado",
            )
        )

    for specification in SPECIFICATIONS:
        specification_feature = features[specification["last_month"]]
        specification_train = train[
            train["ano"].ge(specification["train_start"])
        ].copy()
        model, encoder, coefficients = fit_caged_model(
            specification_train,
            specification_feature,
            specification,
        )
        predictions = predict_caged_model(
            model,
            encoder,
            test,
            specification_feature,
            specification,
            predicted_exposure,
        )
        predictions["modelo"] = specification["name"]
        prediction_frames.append(
            predictions[
                [
                    "ano_teste",
                    "codigo_unidade",
                    "nome_unidade",
                    "demanda_observada",
                    "modelo",
                    "previsto",
                ]
            ]
        )
        metric_rows.append(
            calculate_metrics(
                predictions,
                specification["name"],
                "Ponta a ponta com total previsto pela Frente 1",
            )
        )
        metric_rows.append(
            calculate_metrics(
                add_conditional_prediction(predictions),
                specification["name"],
                "Distribuicao condicional ao total observado",
            )
        )
        coefficient_rows[specification["name"]] = coefficients

    predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)
    baseline_wape = metrics.loc[
        metrics["modelo"].eq("PPML-FE base"),
        ["avaliacao", "wape"],
    ].rename(columns={"wape": "wape_base"})
    persistence_wape = metrics.loc[
        metrics["modelo"].eq("Persistencia taxa t-1"),
        ["avaliacao", "wape"],
    ].rename(columns={"wape": "wape_persistencia"})
    metrics = metrics.merge(baseline_wape, how="left", on="avaliacao")
    metrics = metrics.merge(persistence_wape, how="left", on="avaliacao")
    metrics["delta_wape_pp_vs_base"] = 100 * (
        metrics["wape"] - metrics["wape_base"]
    )
    metrics["delta_wape_pp_vs_persistencia"] = 100 * (
        metrics["wape"] - metrics["wape_persistencia"]
    )
    diagnostics = build_diagnostics(feature, coefficient_rows, rais_vintages)

    feature_output = pd.concat(
        [
            frame.assign(cenario_corte=f"jan-{month:02d}")
            for month, frame in features.items()
        ],
        ignore_index=True,
    )
    feature_output.to_csv(
        RESULTS_DIR / "f1c_cag_feat.csv", index=False, encoding="utf-8-sig"
    )
    predictions.to_csv(
        RESULTS_DIR / "f1c_cag_pred.csv", index=False, encoding="utf-8-sig"
    )
    metrics.to_csv(
        RESULTS_DIR / "f1c_cag_oos.csv", index=False, encoding="utf-8-sig"
    )
    diagnostics.to_csv(
        RESULTS_DIR / "f1c_cag_diag.csv", index=False, encoding="utf-8-sig"
    )
    metrics.round(5).to_latex(
        RESULTS_DIR / "f1c_cag_oos.tex", index=False, float_format="%.5f"
    )
    save_figure(metrics)

    print("CAGED PRE-CORTE")
    print(feature_output.round(6).to_string(index=False))
    print("\nOOS 2025 - DEMANDA BRUTA POR CRECHE")
    print(metrics.round(5).to_string(index=False))
    print("\nDIAGNOSTICOS")
    print(diagnostics.to_string(index=False))


if __name__ == "__main__":
    main()
