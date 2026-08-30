from pathlib import Path
import re
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import nbinom, poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import OneHotEncoder


# Reproducibility: no stochastic step is used in version 0.1, but the project seed is fixed.
np.random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PIPELINE_DIR / "01_dados"
VALIDATION_DIR = PIPELINE_DIR / "03_validacao" / "resultados"
FORECAST_DIR = PIPELINE_DIR / "04_previsoes"
FIGURES_DIR = PIPELINE_DIR / "03_validacao" / "figuras"
for directory in (DATA_DIR, VALIDATION_DIR, FORECAST_DIR, FIGURES_DIR):
    directory.mkdir(parents=True, exist_ok=True)

QUERY_A_PATH = PROJECT_ROOT / "Bases IC_ ClassificadoseFila" / "01_QueryA_InscricoesPorAno.csv.gz"
BIRTHS_PATH = PROJECT_ROOT / "NascidosvivosRJ.xlsx"
DATA_CUTOFF = "2026-08-30"
GROUPS = ["Bercario", "Maternal I", "Maternal II"]


def normalize_text(value):
    """Normalize geographic and grouping labels without changing the source files."""
    if pd.isna(value):
        return None
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    normalized = normalized.upper().strip()
    normalized = re.sub(r"\b(DO|DA|DOS|DAS|DE)\b", " ", normalized)
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return " ".join(normalized.split())


# Only unambiguous spelling/name variants are harmonized. Communities and non-official
# localities are not forced into a neighborhood because that would fabricate geography.
NEIGHBORHOOD_ALIASES = {
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


def normalize_neighborhood(value):
    normalized = normalize_text(value)
    return NEIGHBORHOOD_ALIASES.get(normalized, normalized)


def normalize_group(value):
    normalized = normalize_text(value)
    mapping = {
        "BERCARIO": "Bercario",
        "MATERNAL I": "Maternal I",
        "MATERNAL II": "Maternal II",
    }
    return mapping.get(normalized)


def load_unique_child_years():
    """Build the demand numerator as one child per process year.

    The first chronological record resolves the rare conflicts in neighborhood or grouping
    across multiple registrations for the same anonymized child and year.
    """
    columns = [
        "ano",
        "prm_id",
        "plm_id",
        "ipl_id",
        "opcao",
        "data_criacao",
        "aluno_anon",
        "bairro",
        "grupamento",
    ]
    applications = pd.read_csv(
        QUERY_A_PATH,
        sep=";",
        compression="gzip",
        usecols=columns,
        low_memory=False,
    )
    applications["data_criacao"] = pd.to_datetime(applications["data_criacao"], errors="coerce")
    applications["territorio"] = applications["bairro"].map(normalize_neighborhood)
    applications["grupamento_modelo"] = applications["grupamento"].map(normalize_group)

    child_years = (
        applications.sort_values(["ano", "aluno_anon", "data_criacao", "opcao"])
        .drop_duplicates(["ano", "aluno_anon"], keep="first")
        .copy()
    )
    return applications, child_years


def load_births():
    """Read annual births by maternal residence neighborhood from the local SINASC export."""
    births_raw = pd.read_excel(BIRTHS_PATH, header=4)
    neighborhood_column = births_raw.columns[0]
    births = births_raw[
        births_raw[neighborhood_column].astype(str).str.match(r"^\d{3}\s")
    ].copy()
    births["codigo_bairro"] = births[neighborhood_column].astype(str).str.extract(r"^(\d{3})")[0]
    births["territorio"] = (
        births[neighborhood_column]
        .astype(str)
        .str.replace(r"^\d{3}\s+", "", regex=True)
        .map(normalize_neighborhood)
    )

    # Codes 998 and 999 are non-spatial residual categories and cannot define a territory FE.
    births = births[~births["codigo_bairro"].isin(["998", "999"])].copy()
    year_columns = [column for column in births.columns if isinstance(column, (int, np.integer))]
    births_long = births.melt(
        id_vars=["codigo_bairro", "territorio"],
        value_vars=year_columns,
        var_name="ano_nascimento",
        value_name="nascimentos",
    )
    births_long["ano_nascimento"] = births_long["ano_nascimento"].astype(int)
    births_long["nascimentos"] = pd.to_numeric(births_long["nascimentos"], errors="coerce").fillna(0)
    return births[["codigo_bairro", "territorio"]].drop_duplicates(), births_long


def build_panel(child_years, neighborhood_dimension, births_long):
    """Create neighborhood x grouping x year counts and cohort-based exposure.

    Cohort proxy based on the ages visible in the application records:
    Bercario = births in t-1 plus t-2; Maternal I = t-3; Maternal II = t-4.
    Annual births cannot implement the exact month-level eligibility cutoff.
    """
    valid_territories = set(neighborhood_dimension["territorio"])
    child_years = child_years[
        child_years["territorio"].isin(valid_territories)
        & child_years["grupamento_modelo"].isin(GROUPS)
    ].copy()

    counts = (
        child_years.groupby(["ano", "territorio", "grupamento_modelo"], as_index=False)
        .size()
        .rename(columns={"size": "inscritos"})
    )

    years = list(range(2021, 2027))
    panel = pd.MultiIndex.from_product(
        [years, sorted(valid_territories), GROUPS],
        names=["ano", "territorio", "grupamento_modelo"],
    ).to_frame(index=False)
    panel = panel.merge(counts, how="left", on=["ano", "territorio", "grupamento_modelo"])
    panel["inscritos"] = panel["inscritos"].fillna(0).astype(int)

    birth_lookup = births_long.set_index(["territorio", "ano_nascimento"])["nascimentos"]

    def cohort_exposure(row):
        territory = row["territorio"]
        year = int(row["ano"])
        group = row["grupamento_modelo"]
        if group == "Bercario":
            cohort_years = [year - 1, year - 2]
        elif group == "Maternal I":
            cohort_years = [year - 3]
        else:
            cohort_years = [year - 4]
        return float(sum(birth_lookup.get((territory, cohort_year), 0) for cohort_year in cohort_years))

    panel["universo_elegivel_proxy"] = panel.apply(cohort_exposure, axis=1)
    panel["tendencia"] = panel["ano"] - 2021
    for group in GROUPS:
        safe_name = normalize_text(group).lower().replace(" ", "_")
        panel[f"tend_{safe_name}"] = panel["tendencia"] * (
            panel["grupamento_modelo"] == group
        ).astype(int)
    return panel, child_years


def make_design_matrix(frame, encoder=None, fit=False):
    categorical = frame[["territorio", "grupamento_modelo"]]
    if fit:
        try:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
        except TypeError:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse=True)
        categorical_matrix = encoder.fit_transform(categorical)
    else:
        categorical_matrix = encoder.transform(categorical)
    trend_columns = [column for column in frame.columns if column.startswith("tend_")]
    trend_matrix = sparse.csr_matrix(frame[trend_columns].to_numpy(dtype=float))
    return sparse.hstack([categorical_matrix, trend_matrix], format="csr"), encoder


def fit_ppml(train_frame):
    estimation_sample = train_frame[train_frame["universo_elegivel_proxy"] > 0].copy()
    design, encoder = make_design_matrix(estimation_sample, fit=True)
    exposure = estimation_sample["universo_elegivel_proxy"].to_numpy(dtype=float)
    rate = estimation_sample["inscritos"].to_numpy(dtype=float) / exposure

    # Ridge only stabilizes hundreds of territory indicators in a panel with 3-5 years.
    model = PoissonRegressor(alpha=1e-4, fit_intercept=True, max_iter=3000, tol=1e-9)
    model.fit(design, rate, sample_weight=exposure)
    fitted_mean = model.predict(design) * exposure

    numerator = np.sum((estimation_sample["inscritos"].to_numpy() - fitted_mean) ** 2 - fitted_mean)
    denominator = np.sum(fitted_mean**2)
    dispersion_alpha = max(float(numerator / denominator), 1e-8)
    return model, encoder, dispersion_alpha, estimation_sample


def add_prediction_intervals(frame, alpha):
    means = frame["prev_modelo"].to_numpy(dtype=float)
    if alpha <= 1e-7:
        distributions = None
        frame["p10"] = poisson.ppf(0.10, means)
        frame["p90"] = poisson.ppf(0.90, means)
        frame["p025"] = poisson.ppf(0.025, means)
        frame["p975"] = poisson.ppf(0.975, means)
    else:
        size = 1.0 / alpha
        probability = size / (size + means)
        frame["p10"] = nbinom.ppf(0.10, size, probability)
        frame["p90"] = nbinom.ppf(0.90, size, probability)
        frame["p025"] = nbinom.ppf(0.025, size, probability)
        frame["p975"] = nbinom.ppf(0.975, size, probability)
    return frame


def predict_model(model, encoder, frame, dispersion_alpha):
    prediction_sample = frame[frame["universo_elegivel_proxy"] > 0].copy()
    design, _ = make_design_matrix(prediction_sample, encoder=encoder, fit=False)
    prediction_sample["prev_modelo"] = (
        model.predict(design) * prediction_sample["universo_elegivel_proxy"].to_numpy(dtype=float)
    )
    prediction_sample = add_prediction_intervals(prediction_sample, dispersion_alpha)
    prediction_sample["alpha_nb"] = dispersion_alpha
    return prediction_sample


def calculate_metrics(predictions, prediction_column, model_name, test_year):
    actual = predictions["inscritos"].to_numpy(dtype=float)
    predicted = predictions[prediction_column].to_numpy(dtype=float)
    error = predicted - actual
    denominator = actual.sum()
    metrics = {
        "ano_teste": test_year,
        "modelo": model_name,
        "n_celulas": len(predictions),
        "observado_total": actual.sum(),
        "previsto_total": predicted.sum(),
        "erro_total": error.sum(),
        "mae": np.mean(np.abs(error)),
        "rmse": np.sqrt(np.mean(error**2)),
        "wape": np.sum(np.abs(error)) / denominator if denominator > 0 else np.nan,
        "vies_relativo": error.sum() / denominator if denominator > 0 else np.nan,
    }
    if prediction_column == "prev_modelo":
        metrics["cobertura_80"] = np.mean(
            (actual >= predictions["p10"].to_numpy()) & (actual <= predictions["p90"].to_numpy())
        )
        metrics["cobertura_95"] = np.mean(
            (actual >= predictions["p025"].to_numpy()) & (actual <= predictions["p975"].to_numpy())
        )
    else:
        metrics["cobertura_80"] = np.nan
        metrics["cobertura_95"] = np.nan
    return metrics


def run_oos(panel, train_end, test_year):
    train = panel[(panel["ano"] <= train_end) & (panel["ano"] >= 2021)].copy()
    test = panel[panel["ano"] == test_year].copy()
    model, encoder, dispersion_alpha, estimation_sample = fit_ppml(train)
    predictions = predict_model(model, encoder, test, dispersion_alpha)

    previous = panel[panel["ano"] == test_year - 1][
        ["territorio", "grupamento_modelo", "inscritos", "universo_elegivel_proxy"]
    ].copy()
    previous["taxa_anterior"] = previous["inscritos"] / previous[
        "universo_elegivel_proxy"
    ].replace(0, np.nan)
    predictions = predictions.merge(
        previous[["territorio", "grupamento_modelo", "taxa_anterior"]],
        how="left",
        on=["territorio", "grupamento_modelo"],
    )
    fallback_rate = (
        estimation_sample.groupby("grupamento_modelo")["inscritos"].sum()
        / estimation_sample.groupby("grupamento_modelo")["universo_elegivel_proxy"].sum()
    )
    predictions["taxa_anterior"] = predictions["taxa_anterior"].fillna(
        predictions["grupamento_modelo"].map(fallback_rate)
    )
    predictions["prev_persistencia"] = (
        predictions["taxa_anterior"] * predictions["universo_elegivel_proxy"]
    )
    predictions["ano_treino_final"] = train_end
    predictions["ano_teste"] = test_year

    metrics = [
        calculate_metrics(predictions, "prev_modelo", "PPML-FE ridge", test_year),
        calculate_metrics(predictions, "prev_persistencia", "Persistencia taxa t-1", test_year),
    ]
    return predictions, metrics


def aggregate_forecast_summary(forecast):
    rows = []
    for group, part in forecast.groupby("grupamento_modelo", sort=False):
        mean_total = part["prev_modelo"].sum()
        alpha = float(part["alpha_nb"].iloc[0])
        variance_total = np.sum(part["prev_modelo"] + alpha * part["prev_modelo"] ** 2)
        standard_deviation = np.sqrt(variance_total)
        rows.append(
            {
                "grupamento": group,
                "universo_proxy": part["universo_elegivel_proxy"].sum(),
                "previsao_2026": mean_total,
                "persistencia_2026": part["prev_persistencia"].sum(),
                "limite_80_inf": max(0, mean_total - 1.281552 * standard_deviation),
                "limite_80_sup": mean_total + 1.281552 * standard_deviation,
                "limite_95_inf": max(0, mean_total - 1.959964 * standard_deviation),
                "limite_95_sup": mean_total + 1.959964 * standard_deviation,
            }
        )
    summary = pd.DataFrame(rows)
    numeric_columns = [column for column in summary.columns if column != "grupamento"]
    total = {"grupamento": "Total"}
    total["universo_proxy"] = summary["universo_proxy"].sum()
    total["previsao_2026"] = summary["previsao_2026"].sum()
    total["persistencia_2026"] = summary["persistencia_2026"].sum()
    alpha = float(forecast["alpha_nb"].iloc[0])
    variance_total = np.sum(forecast["prev_modelo"] + alpha * forecast["prev_modelo"] ** 2)
    standard_deviation = np.sqrt(variance_total)
    total["limite_80_inf"] = max(0, total["previsao_2026"] - 1.281552 * standard_deviation)
    total["limite_80_sup"] = total["previsao_2026"] + 1.281552 * standard_deviation
    total["limite_95_inf"] = max(0, total["previsao_2026"] - 1.959964 * standard_deviation)
    total["limite_95_sup"] = total["previsao_2026"] + 1.959964 * standard_deviation
    summary = pd.concat([summary, pd.DataFrame([total])], ignore_index=True)
    summary[numeric_columns] = summary[numeric_columns].round(1)
    return summary


def save_figures(oos_predictions):
    grouped = (
        oos_predictions.groupby(["ano_teste", "grupamento_modelo"])[
            ["inscritos", "prev_modelo", "prev_persistencia"]
        ]
        .sum()
        .reset_index()
    )
    x = np.arange(len(grouped))
    width = 0.26
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.bar(x - width, grouped["inscritos"], width, label="Observado", color="#17324D")
    ax.bar(x, grouped["prev_modelo"], width, label="PPML-FE", color="#2C7FB8")
    ax.bar(x + width, grouped["prev_persistencia"], width, label="Persistência", color="#F28E2B")
    labels = [f"{year}\n{group}" for year, group in zip(grouped["ano_teste"], grouped["grupamento_modelo"])]
    ax.set_xticks(x, labels)
    ax.set_ylabel("Crianças (base anonimizada)")
    ax.set_title("Validação fora da amostra por grupamento")
    ax.legend(frameon=False, ncol=3)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "validacao_oos.png", dpi=180)
    plt.close(fig)


def main():
    applications, child_years = load_unique_child_years()
    neighborhood_dimension, births_long = load_births()
    panel, matched_child_years = build_panel(child_years, neighborhood_dimension, births_long)

    oos_2025, metrics_2025 = run_oos(panel, train_end=2024, test_year=2025)
    oos_predictions = oos_2025.copy()
    metrics = pd.DataFrame(metrics_2025)

    final_model, final_encoder, final_alpha, _ = fit_ppml(panel[panel["ano"] <= 2025])
    forecast_2026 = predict_model(
        final_model,
        final_encoder,
        panel[panel["ano"] == 2026],
        final_alpha,
    )
    previous_2025 = panel[panel["ano"] == 2025][
        ["territorio", "grupamento_modelo", "inscritos", "universo_elegivel_proxy"]
    ].copy()
    previous_2025["taxa_2025"] = previous_2025["inscritos"] / previous_2025[
        "universo_elegivel_proxy"
    ].replace(0, np.nan)
    forecast_2026 = forecast_2026.merge(
        previous_2025[["territorio", "grupamento_modelo", "taxa_2025"]],
        how="left",
        on=["territorio", "grupamento_modelo"],
    )
    final_group_rate = (
        panel.loc[(panel["ano"] <= 2025) & (panel["universo_elegivel_proxy"] > 0)]
        .groupby("grupamento_modelo")["inscritos"].sum()
        / panel.loc[(panel["ano"] <= 2025) & (panel["universo_elegivel_proxy"] > 0)]
        .groupby("grupamento_modelo")["universo_elegivel_proxy"].sum()
    )
    forecast_2026["taxa_2025"] = forecast_2026["taxa_2025"].fillna(
        forecast_2026["grupamento_modelo"].map(final_group_rate)
    )
    forecast_2026["prev_persistencia"] = (
        forecast_2026["taxa_2025"] * forecast_2026["universo_elegivel_proxy"]
    )
    forecast_2026["data_corte"] = DATA_CUTOFF
    forecast_2026["modelo"] = "PPML-FE ridge v0.1"
    forecast_2026["versao"] = "0.1-auditoria"
    forecast_summary = aggregate_forecast_summary(forecast_2026)

    audit = pd.DataFrame(
        [
            {"indicador": "linhas_query_a", "valor": len(applications)},
            {"indicador": "criancas_ano_unicas", "valor": len(child_years)},
            {"indicador": "criancas_ano_geografia_valida", "valor": len(matched_child_years)},
            {
                "indicador": "cobertura_geografica_pct",
                "valor": 100 * len(matched_child_years) / len(child_years),
            },
            {"indicador": "bairros_modelo", "valor": neighborhood_dimension["territorio"].nunique()},
            {"indicador": "alpha_nb_final", "valor": final_alpha},
        ]
    )
    first_observed_year = child_years.groupby("aluno_anon")["ano"].min()
    child_years_with_flow = child_years.copy()
    child_years_with_flow["fluxo"] = np.where(
        child_years_with_flow["ano"].eq(
            child_years_with_flow["aluno_anon"].map(first_observed_year)
        ),
        "primeira_observada",
        "reinscricao_observada",
    )
    flows = (
        child_years_with_flow.groupby(["ano", "fluxo"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    panel.to_csv(DATA_DIR / "painel_modelo.csv", index=False, encoding="utf-8-sig")
    oos_predictions.to_csv(VALIDATION_DIR / "previsoes_oos_2025.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(VALIDATION_DIR / "metricas_oos_2025.csv", index=False, encoding="utf-8-sig")
    forecast_2026.to_csv(FORECAST_DIR / "previsao_2026_territorio_grupamento.csv", index=False, encoding="utf-8-sig")
    forecast_summary.to_csv(FORECAST_DIR / "previsao_2026_resumo.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(VALIDATION_DIR / "auditoria_modelo.csv", index=False, encoding="utf-8-sig")
    flows.to_csv(VALIDATION_DIR / "fluxos_amostra.csv", index=False, encoding="utf-8-sig")

    metrics.round(4).to_latex(VALIDATION_DIR / "metricas_oos_2025.tex", index=False, float_format="%.4f")
    forecast_summary.to_latex(FORECAST_DIR / "previsao_2026_resumo.tex", index=False, float_format="%.1f")
    audit.round(4).to_latex(VALIDATION_DIR / "auditoria_modelo.tex", index=False, float_format="%.4f")
    flows.to_latex(VALIDATION_DIR / "fluxos_amostra.tex", index=False)
    save_figures(oos_predictions)

    print("AUDITORIA")
    print(audit.to_string(index=False))
    print("\nOOS")
    print(metrics.round(4).to_string(index=False))
    print("\nPREVISAO 2026")
    print(forecast_summary.to_string(index=False))


if __name__ == "__main__":
    main()
