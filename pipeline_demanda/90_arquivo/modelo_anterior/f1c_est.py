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

import f1_est


# Reproducibility: the estimator is deterministic, but the project seed remains fixed.
np.random.seed(42)

MODEL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODEL_DIR / "results"
FIGURES_DIR = MODEL_DIR / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

TEST_YEAR = 2025
TRAIN_START = 2021
TRAIN_END = 2024
# Unit-level rates are much smaller than neighborhood entry rates. A lighter penalty
# preserves persistent differences across facilities while still regularizing sparse units.
RIDGE_ALPHA = 1e-8


def normalize_unit_code(series):
    """Return stable string codes without changing the source column."""
    numeric = pd.to_numeric(series, errors="coerce").astype("Int64")
    return numeric.astype("string")


def load_child_unit_demand():
    """Build one observation per child, year, and selected unit.

    A child is counted once in every unit selected in any option. Repeated rows for the
    same child-unit pair are removed, but the child remains present in other selected
    units. This target measures operational demand pressure, not unique children systemwide.
    """
    _, child_years = f1_est.load_unique_child_years()
    neighborhood_dimension, births_long = f1_est.load_births()
    front1_panel, _ = f1_est.build_panel(
        child_years,
        neighborhood_dimension,
        births_long,
    )
    modeled_cells = front1_panel.loc[
        front1_panel["universo_elegivel_proxy"].gt(0),
        ["ano", "territorio", "grupamento_modelo"],
    ]
    matched_children = (
        child_years.merge(
            modeled_cells,
            how="inner",
            on=["ano", "territorio", "grupamento_modelo"],
        )[["ano", "aluno_anon"]]
        .drop_duplicates()
    )

    columns = [
        "ano",
        "unidade",
        "nome_unidade",
        "opcao",
        "data_criacao",
        "aluno_anon",
    ]
    applications = pd.read_csv(
        f1_est.QUERY_A_PATH,
        sep=";",
        compression="gzip",
        usecols=columns,
        low_memory=False,
    )
    applications["data_criacao"] = pd.to_datetime(
        applications["data_criacao"], errors="coerce"
    )
    applications["codigo_unidade"] = normalize_unit_code(applications["unidade"])
    applications = applications.merge(
        matched_children,
        how="inner",
        on=["ano", "aluno_anon"],
    ).dropna(subset=["codigo_unidade"])

    child_units = (
        applications.sort_values(
            ["ano", "aluno_anon", "codigo_unidade", "data_criacao", "opcao"]
        )
        .drop_duplicates(["ano", "aluno_anon", "codigo_unidade"], keep="first")
        .copy()
    )
    counts = (
        child_units.groupby(["ano", "codigo_unidade"], as_index=False)
        .size()
        .rename(columns={"size": "demanda_observada"})
    )
    latest_names = (
        child_units.dropna(subset=["nome_unidade"])
        .sort_values(["ano", "data_criacao"])
        .groupby("codigo_unidade")["nome_unidade"]
        .last()
        .rename("nome_unidade")
        .reset_index()
    )
    exposure = (
        matched_children.groupby("ano")["aluno_anon"]
        .nunique()
        .rename("criancas_unicas")
        .to_dict()
    )
    return child_units, counts, latest_names, exposure


def load_front1_exposure():
    """Read the strictly out-of-sample total predicted by Front 1 for 2025."""
    path = RESULTS_DIR / "f1_oos_pred.csv"
    front1 = pd.read_csv(path)
    years = set(front1["ano_teste"].astype(int).unique())
    if years != {TEST_YEAR}:
        raise ValueError(
            "Front 1 OOS must contain only 2025 before the unit-level evaluation."
        )
    return float(front1["prev_modelo"].sum())


def build_training_panel(counts, continuing_units, exposure):
    """Create a short unit panel, filling internal observed-history gaps with zero.

    The comparison is conditional on units observed in both 2024 and 2025. This avoids
    pretending that persistence or a unit fixed effect can forecast an unseen opening.
    """
    train_counts = counts[
        counts["ano"].between(TRAIN_START, TRAIN_END)
        & counts["codigo_unidade"].isin(continuing_units)
    ].copy()
    first_year = train_counts.groupby("codigo_unidade")["ano"].min().to_dict()

    rows = []
    for unit in continuing_units:
        for year in range(max(TRAIN_START, int(first_year[unit])), TRAIN_END + 1):
            rows.append((year, unit))
    panel = pd.DataFrame(rows, columns=["ano", "codigo_unidade"])
    panel = panel.merge(
        train_counts,
        how="left",
        on=["ano", "codigo_unidade"],
    )
    panel["demanda_observada"] = panel["demanda_observada"].fillna(0).astype(int)
    panel["exposicao_criancas"] = panel["ano"].map(exposure).astype(float)
    panel["tendencia"] = panel["ano"] - TRAIN_START
    return panel


def fit_unit_ppml(train):
    """Estimate unit fixed effects plus one extrapolable common time trend.

    The exposure is the number of unique children entering the system. Unit effects absorb
    persistent attractiveness; the time trend captures changes in options per child. Future
    versions should replace part of the fixed effect with distance and competition measures.
    """
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    unit_matrix = encoder.fit_transform(train[["codigo_unidade"]])
    trend_matrix = sparse.csr_matrix(train[["tendencia"]].to_numpy(dtype=float))
    design = sparse.hstack([unit_matrix, trend_matrix], format="csr")
    exposure = train["exposicao_criancas"].to_numpy(dtype=float)
    rate = train["demanda_observada"].to_numpy(dtype=float) / exposure

    model = PoissonRegressor(
        alpha=RIDGE_ALPHA,
        fit_intercept=True,
        solver="newton-cholesky",
        max_iter=200,
        tol=1e-8,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=ConvergenceWarning)
        model.fit(design, rate, sample_weight=exposure)
    return model, encoder


def predict_continuing_units(counts, names, exposure, predicted_exposure):
    """Forecast 2025 for units present in both 2024 and 2025."""
    previous_units = set(
        counts.loc[counts["ano"].eq(TRAIN_END), "codigo_unidade"]
    )
    test_units = set(counts.loc[counts["ano"].eq(TEST_YEAR), "codigo_unidade"])
    continuing_units = sorted(previous_units & test_units)
    new_units = sorted(test_units - previous_units)
    absent_units = sorted(previous_units - test_units)

    train = build_training_panel(counts, continuing_units, exposure)
    model, encoder = fit_unit_ppml(train)

    test = counts[
        counts["ano"].eq(TEST_YEAR)
        & counts["codigo_unidade"].isin(continuing_units)
    ].copy()
    test["tendencia"] = TEST_YEAR - TRAIN_START
    unit_matrix = encoder.transform(test[["codigo_unidade"]])
    trend_matrix = sparse.csr_matrix(test[["tendencia"]].to_numpy(dtype=float))
    design = sparse.hstack([unit_matrix, trend_matrix], format="csr")
    test["prev_modelo"] = model.predict(design) * predicted_exposure

    previous = counts[counts["ano"].eq(TRAIN_END)][
        ["codigo_unidade", "demanda_observada"]
    ].rename(columns={"demanda_observada": "demanda_2024"})
    test = test.merge(previous, how="left", on="codigo_unidade")
    test["prev_persistencia"] = (
        test["demanda_2024"] / float(exposure[TRAIN_END]) * predicted_exposure
    )

    # These rescaled predictions use the realized aggregate and are diagnostics only. They
    # isolate allocation across units from the Front 1 error in total unique demand.
    observed_total = float(test["demanda_observada"].sum())
    for source, target in [
        ("prev_modelo", "prev_modelo_condicional"),
        ("prev_persistencia", "prev_persistencia_condicional"),
    ]:
        predicted_total = float(test[source].sum())
        test[target] = test[source] * observed_total / predicted_total

    history_years = (
        train.groupby("codigo_unidade")["ano"].nunique().rename("anos_historico")
    )
    test = test.merge(names, how="left", on="codigo_unidade")
    test = test.merge(history_years, how="left", on="codigo_unidade")
    test["ano_teste"] = TEST_YEAR
    test["status_unidade"] = "continuante"
    test["erro_abs_modelo"] = (test["prev_modelo"] - test["demanda_observada"]).abs()
    test["erro_abs_persistencia"] = (
        test["prev_persistencia"] - test["demanda_observada"]
    ).abs()
    test["vencedor"] = np.select(
        [
            test["erro_abs_modelo"] < test["erro_abs_persistencia"],
            test["erro_abs_modelo"] > test["erro_abs_persistencia"],
        ],
        ["PPML-FE unidade", "Persistencia"],
        default="Empate",
    )
    return test, new_units, absent_units, train


def calculate_metrics(predictions, prediction_column, model_name, evaluation):
    """Calculate unit-level errors without cancellation across facilities."""
    actual = predictions["demanda_observada"].to_numpy(dtype=float)
    predicted = predictions[prediction_column].to_numpy(dtype=float)
    error = predicted - actual
    absolute_error = np.abs(error)
    correlation = spearmanr(actual, predicted).statistic
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
        "spearman": correlation,
    }


def build_metrics(predictions):
    """Report deployable performance and an allocation-only diagnostic."""
    rows = [
        calculate_metrics(
            predictions,
            "prev_modelo",
            "PPML-FE unidade",
            "Ponta a ponta com total previsto pela Frente 1",
        ),
        calculate_metrics(
            predictions,
            "prev_persistencia",
            "Persistencia taxa t-1",
            "Ponta a ponta com total previsto pela Frente 1",
        ),
        calculate_metrics(
            predictions,
            "prev_modelo_condicional",
            "PPML-FE unidade",
            "Distribuicao condicional ao total observado",
        ),
        calculate_metrics(
            predictions,
            "prev_persistencia_condicional",
            "Persistencia taxa t-1",
            "Distribuicao condicional ao total observado",
        ),
    ]
    return pd.DataFrame(rows)


def save_figure(predictions):
    """Save direct model-versus-persistence diagnostics for individual units."""
    observed = predictions["demanda_observada"].to_numpy(dtype=float)
    model_prediction = predictions["prev_modelo"].to_numpy(dtype=float)
    persistence_prediction = predictions["prev_persistencia"].to_numpy(dtype=float)
    upper = 1.03 * max(observed.max(), model_prediction.max(), persistence_prediction.max())

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.6))
    panels = [
        (model_prediction, "PPML-FE por unidade"),
        (persistence_prediction, "Persistência da taxa de 2024"),
    ]
    for axis, (prediction, title) in zip(axes[:2], panels):
        axis.scatter(observed, prediction, s=17, alpha=0.55, color="#2C7FB8")
        axis.plot([0, upper], [0, upper], color="#F28E2B", linewidth=1.2)
        axis.set_xlim(0, upper)
        axis.set_ylim(0, upper)
        axis.set_xlabel("Demanda observada em 2025")
        axis.set_ylabel("Demanda prevista")
        axis.set_title(title)
        axis.grid(alpha=0.18)

    model_error = np.abs(model_prediction - observed)
    persistence_error = np.abs(persistence_prediction - observed)
    error_upper = 1.03 * max(model_error.max(), persistence_error.max())
    axes[2].scatter(
        persistence_error,
        model_error,
        s=17,
        alpha=0.55,
        color="#17324D",
    )
    axes[2].plot([0, error_upper], [0, error_upper], color="#F28E2B", linewidth=1.2)
    axes[2].set_xlim(0, error_upper)
    axes[2].set_ylim(0, error_upper)
    axes[2].set_xlabel("Erro absoluto da persistência")
    axes[2].set_ylabel("Erro absoluto do PPML-FE")
    axes[2].set_title("Abaixo da diagonal: modelo vence")
    axes[2].grid(alpha=0.18)

    fig.suptitle(
        "Validação OOS por creche — qualquer opção selecionada (2025)",
        fontsize=13,
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "f1c_oos_2025.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_audit(child_units, counts, predictions, new_units, absent_units, exposure, predicted_exposure):
    """Record the evaluation universe and the treatment of network turnover."""
    test_counts = counts[counts["ano"].eq(TEST_YEAR)]
    new_demand = test_counts[test_counts["codigo_unidade"].isin(new_units)][
        "demanda_observada"
    ].sum()
    model_win_share = predictions["vencedor"].eq("PPML-FE unidade").mean()
    return pd.DataFrame(
        [
            {"indicador": "definicao_alvo", "valor": "crianca-unidade distinta em qualquer opcao"},
            {"indicador": "ano_teste_oos", "valor": TEST_YEAR},
            {"indicador": "criancas_unicas_observadas_2025", "valor": exposure[TEST_YEAR]},
            {"indicador": "criancas_unicas_previstas_f1_2025", "valor": predicted_exposure},
            {"indicador": "pares_crianca_unidade_2025", "valor": len(child_units[child_units["ano"].eq(TEST_YEAR)])},
            {"indicador": "unidades_continuantes_avaliadas", "valor": len(predictions)},
            {"indicador": "unidades_novas_ou_reativadas", "valor": len(new_units)},
            {"indicador": "demanda_unidades_novas_ou_reativadas", "valor": int(new_demand)},
            {"indicador": "unidades_ausentes_em_2025", "valor": len(absent_units)},
            {"indicador": "fracao_unidades_modelo_vence", "valor": model_win_share},
        ]
    )


def main():
    child_units, counts, names, exposure = load_child_unit_demand()
    predicted_exposure = load_front1_exposure()
    predictions, new_units, absent_units, train = predict_continuing_units(
        counts,
        names,
        exposure,
        predicted_exposure,
    )
    metrics = build_metrics(predictions)
    audit = build_audit(
        child_units,
        counts,
        predictions,
        new_units,
        absent_units,
        exposure,
        predicted_exposure,
    )

    predictions.to_csv(
        RESULTS_DIR / "f1c_oos_pred.csv", index=False, encoding="utf-8-sig"
    )
    metrics.to_csv(RESULTS_DIR / "f1c_oos.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(RESULTS_DIR / "f1c_audit.csv", index=False, encoding="utf-8-sig")
    metrics.round(4).to_latex(
        RESULTS_DIR / "f1c_oos.tex", index=False, float_format="%.4f"
    )
    audit.to_latex(RESULTS_DIR / "f1c_audit.tex", index=False)
    save_figure(predictions)

    print("AUDITORIA FRENTE 1 - DEMANDA BRUTA POR CRECHE")
    print(audit.to_string(index=False))
    print("\nOOS 2025 POR UNIDADE")
    print(metrics.round(4).to_string(index=False))
    print(f"\nLinhas no painel de treino: {len(train):,}")


if __name__ == "__main__":
    main()
