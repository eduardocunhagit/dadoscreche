from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import f1c_est


np.random.seed(42)

MODEL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODEL_DIR / "results"
MAP_OUTPUT_DIR = MODEL_DIR.parent / "output"
CAGED_DIR = MODEL_DIR / "handoff_f1_cag_fem"
OUTPUT_DIR = MODEL_DIR / "insumos_modelo_demanda"


def sha256(path):
    """Return an integrity hash without modifying the artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_observed_outputs(child_units, counts, names):
    """Create the final observed Front 1 target and the co-selection edge list.

    The economic object is gross operational pressure: one child is counted once in every
    facility selected. The child-facility edge list preserves the information needed to
    construct competition measures later, without estimating Front 2 here.
    """
    demand_history = counts.merge(
        names, how="left", on="codigo_unidade", validate="many_to_one"
    )
    units_2024 = set(counts.loc[counts["ano"].eq(2024), "codigo_unidade"])
    demand_2025 = demand_history[demand_history["ano"].eq(2025)].copy()
    demand_2025["status_em_2025"] = np.where(
        demand_2025["codigo_unidade"].isin(units_2024),
        "continuante",
        "nova_ou_reativada",
    )
    selected_edges = child_units[child_units["ano"].eq(2025)][
        [
            "ano",
            "aluno_anon",
            "codigo_unidade",
            "nome_unidade",
            "opcao",
            "data_criacao",
        ]
    ].copy()
    selected_edges = selected_edges.rename(
        columns={
            "opcao": "opcao_primeiro_registro",
            "data_criacao": "data_primeiro_registro",
        }
    )
    return demand_history, demand_2025, selected_edges


def fit_and_export_base_coefficients(counts, exposure):
    """Re-estimate the deterministic OOS base model and export its full coefficient set."""
    previous_units = set(counts.loc[counts["ano"].eq(2024), "codigo_unidade"])
    test_units = set(counts.loc[counts["ano"].eq(2025), "codigo_unidade"])
    continuing_units = sorted(previous_units & test_units)
    train = f1c_est.build_training_panel(counts, continuing_units, exposure)
    model, encoder = f1c_est.fit_unit_ppml(train)
    number_of_units = len(encoder.categories_[0])
    unit_coefficients = pd.DataFrame(
        {
            "codigo_unidade": encoder.categories_[0],
            "coef_efeito_unidade": model.coef_[:number_of_units],
        }
    )
    common_coefficients = pd.DataFrame(
        [
            {
                "modelo": "PPML-FE unidade base",
                "intercepto": float(model.intercept_),
                "coef_tendencia": float(model.coef_[number_of_units]),
                "ridge_alpha": f1c_est.RIDGE_ALPHA,
                "inicio_treino": f1c_est.TRAIN_START,
                "fim_treino": f1c_est.TRAIN_END,
                "ano_oos": f1c_est.TEST_YEAR,
                "exposicao_prevista_2025": f1c_est.load_front1_exposure(),
                "n_unidades": number_of_units,
            }
        ]
    )
    return common_coefficients, unit_coefficients


def build_validation_output():
    """Combine the base, persistence, and female-CAGED OOS predictions by facility."""
    base = pd.read_csv(
        RESULTS_DIR / "f1c_oos_pred.csv", dtype={"codigo_unidade": "string"}
    )
    caged = pd.read_csv(
        CAGED_DIR / "prev_creche_2025.csv", dtype={"codigo_unidade": "string"}
    )
    caged = caged[["codigo_unidade", "prev_f1_cag_fem"]]
    validation = base.merge(
        caged, how="left", on="codigo_unidade", validate="one_to_one"
    )
    validation = validation.rename(
        columns={
            "demanda_observada": "demanda_bruta_observada_2025",
            "prev_modelo": "prev_ppml_base_2025",
            "prev_persistencia": "prev_persistencia_2025",
            "prev_modelo_condicional": "prev_ppml_cond_total_observado_DIAGNOSTICO",
            "prev_persistencia_condicional": (
                "prev_persistencia_cond_total_observado_DIAGNOSTICO"
            ),
            "prev_f1_cag_fem": "prev_ppml_cag_fem_2025",
        }
    )
    selected_columns = [
        "ano_teste",
        "codigo_unidade",
        "nome_unidade",
        "status_unidade",
        "anos_historico",
        "demanda_bruta_observada_2025",
        "demanda_2024",
        "prev_ppml_base_2025",
        "prev_persistencia_2025",
        "prev_ppml_cag_fem_2025",
        "prev_ppml_cond_total_observado_DIAGNOSTICO",
        "prev_persistencia_cond_total_observado_DIAGNOSTICO",
    ]
    return validation[selected_columns]


def build_metrics():
    """Put primary, benchmark, and challenger metrics in one auditable table."""
    base = pd.read_csv(RESULTS_DIR / "f1c_oos.csv")
    base = base[
        base["avaliacao"].eq("Ponta a ponta com total previsto pela Frente 1")
    ].copy()
    base["papel"] = np.where(
        base["modelo"].str.contains("Persistencia"), "benchmark", "modelo_base"
    )
    caged = pd.read_csv(CAGED_DIR / "metricas_2025.csv")
    caged = caged[caged["modelo"].str.contains("Caged feminino")].copy()
    caged["avaliacao"] = "Ponta a ponta com total previsto pela Frente 1"
    caged["papel"] = np.where(
        caged["modelo"].eq("PPML-FE + Caged feminino pre-corte"),
        "challenger_caged_feminino",
        "robustez_caged_feminino",
    )
    common = [
        "ano_teste",
        "avaliacao",
        "papel",
        "modelo",
        "n_unidades",
        "observado_total",
        "previsto_total",
        "wape",
        "mae",
        "rmse",
        "vies_relativo",
        "spearman",
    ]
    return pd.concat([base[common], caged[common]], ignore_index=True)


def build_facility_context():
    """Expose geography and service-pressure fields as context, not as Front 1 forecasts."""
    path = MAP_OUTPUT_DIR / "creches_2025.csv"
    context = pd.read_csv(path, dtype={"codigo": "string"})
    columns = [
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
        "fila_total",
        "fila_bercario",
        "fila_maternal_1",
        "fila_maternal_2",
        "referencia_matriculas",
    ]
    return context[columns].rename(columns={"codigo": "codigo_unidade"})


def validate_outputs(outputs):
    """Fail before export if the handoff violates the documented target or coverage."""
    demand_2025 = outputs["demanda_bruta_2025.csv"]
    edges = outputs["pares_crianca_creche_2025.csv"]
    validation = outputs["validacao_oos_2025.csv"]
    if len(demand_2025) != 836 or demand_2025["demanda_observada"].sum() != 155312:
        raise ValueError("Unexpected 2025 gross-demand coverage.")
    if len(edges) != 155312:
        raise ValueError("The child-facility edge list does not reproduce gross demand.")
    rebuilt = (
        edges.groupby("codigo_unidade").size().sort_index().astype(int)
    )
    expected = (
        demand_2025.set_index("codigo_unidade")["demanda_observada"]
        .sort_index()
        .astype(int)
    )
    if not rebuilt.equals(expected):
        raise ValueError("Child-facility edges do not aggregate to facility demand.")
    if len(validation) != 834 or validation.isna().any().any():
        raise ValueError("Unexpected OOS prediction coverage or missing values.")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    child_units, counts, names, exposure = f1c_est.load_child_unit_demand()
    history, demand_2025, selected_edges = build_observed_outputs(
        child_units, counts, names
    )
    common_coefficients, unit_coefficients = fit_and_export_base_coefficients(
        counts, exposure
    )
    validation = build_validation_output()
    metrics = build_metrics()
    context = build_facility_context()
    context_codes = set(context["codigo_unidade"].dropna())
    demand_2025["tem_contexto_creche_2025"] = demand_2025[
        "codigo_unidade"
    ].isin(context_codes)

    caged_common = pd.read_csv(CAGED_DIR / "coef_modelo.csv")
    caged_units = pd.read_csv(
        CAGED_DIR / "coef_unidades.csv", dtype={"codigo_unidade": "string"}
    )
    caged_feature = pd.read_csv(CAGED_DIR / "cag_fem_feat.csv")
    forecast_2026 = pd.read_csv(RESULTS_DIR / "f1_prev_2026.csv")
    summary_2026 = pd.read_csv(RESULTS_DIR / "f1_resumo_2026.csv")

    outputs = {
        "demanda_bruta_2021_2025.csv": history,
        "demanda_bruta_2025.csv": demand_2025,
        "pares_crianca_creche_2025.csv": selected_edges,
        "validacao_oos_2025.csv": validation,
        "metricas_oos_2025.csv": metrics,
        "coef_base_comuns.csv": common_coefficients,
        "coef_base_unidades.csv": unit_coefficients,
        "coef_cag_fem.csv": caged_common,
        "coef_cag_fem_unidades.csv": caged_units,
        "cag_fem_feat.csv": caged_feature,
        "contexto_creches_2025.csv": context,
        "contexto_bairro_grupo_2026.csv": forecast_2026,
        "resumo_bairro_grupo_2026.csv": summary_2026,
    }
    validate_outputs(outputs)
    for filename, frame in outputs.items():
        frame.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    base_prediction = validation["prev_ppml_base_2025"].to_numpy(float)
    existing_prediction = pd.read_csv(RESULTS_DIR / "f1c_oos_pred.csv")[
        "prev_modelo"
    ].to_numpy(float)
    maximum_reproduction_error = float(
        np.max(np.abs(base_prediction - existing_prediction))
    )
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "front": 1,
        "front_2_executed": False,
        "recommended_primary_input_2025": "demanda_bruta_2025.csv",
        "competition_edge_list": "pares_crianca_creche_2025.csv",
        "oos_scenarios": "validacao_oos_2025.csv",
        "production_forecast_by_facility_2026_available": False,
        "gross_demand_definition": (
            "one distinct child-facility pair for every facility selected in any option"
        ),
        "number_of_facilities_observed_2025": int(len(demand_2025)),
        "number_of_child_facility_pairs_2025": int(len(selected_edges)),
        "number_of_continuing_facilities_oos": int(len(validation)),
        "number_of_facilities_with_context_2025": int(
            demand_2025["tem_contexto_creche_2025"].sum()
        ),
        "maximum_base_prediction_reproduction_error": maximum_reproduction_error,
        "files": {},
    }
    for filename, frame in outputs.items():
        path = OUTPUT_DIR / filename
        manifest["files"][filename] = {
            "rows": int(len(frame)),
            "sha256": sha256(path),
        }
    readme = OUTPUT_DIR / "README.md"
    if readme.exists():
        manifest["files"]["README.md"] = {
            "bytes": readme.stat().st_size,
            "sha256": sha256(readme),
        }
    manifest["files"]["../make_insumos_modelo_demanda.py"] = {
        "bytes": Path(__file__).stat().st_size,
        "sha256": sha256(Path(__file__)),
    }
    with (OUTPUT_DIR / "manifesto.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
