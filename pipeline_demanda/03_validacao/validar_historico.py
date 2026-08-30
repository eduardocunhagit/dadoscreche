from pathlib import Path
import html
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

VALIDATION_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = VALIDATION_DIR.parent
RESULTS_DIR = VALIDATION_DIR / "resultados"
OUTPUT_DIR = PIPELINE_DIR / "05_visualizacoes" / "output"
PANEL_FILE = PIPELINE_DIR / "01_dados" / "painel_modelo.csv"
FORECAST_2026_FILE = PIPELINE_DIR / "04_previsoes" / "previsao_2026_resumo.csv"
HISTORY_FILE = RESULTS_DIR / "previsao_historica_2021_2026.csv"
PERFORMANCE_FILE = RESULTS_DIR / "performance_historica_2023_2025.csv"
FIGURE_FILE = OUTPUT_DIR / "performance_modelo_demanda.png"
REPORT_FILE = OUTPUT_DIR / "performance_modelo_demanda.html"

sys.path.insert(0, str(PIPELINE_DIR / "02_estimacao"))
import estimar_demanda as core


def aggregate_interval(predictions):
    mean = float(predictions["prev_modelo"].sum())
    alpha = float(predictions["alpha_nb"].iloc[0])
    variance = float(np.sum(predictions["prev_modelo"] + alpha * predictions["prev_modelo"] ** 2))
    sd = np.sqrt(variance)
    return max(0.0, mean - 1.959964 * sd), mean + 1.959964 * sd


def build_tables():
    panel = pd.read_csv(PANEL_FILE)
    observed = (
        panel.loc[(panel["ano"] <= 2025) & (panel["universo_elegivel_proxy"] > 0)]
        .groupby("ano", as_index=False)["inscritos"]
        .sum()
        .set_index("ano")["inscritos"]
    )

    history = [
        {
            "ano": year,
            "tipo": "historico_treino",
            "observado": float(observed.loc[year]),
            "previsto_ppml": np.nan,
            "limite_95_inf": np.nan,
            "limite_95_sup": np.nan,
            "previsto_persistencia": np.nan,
            "quebra_cobertura": False,
        }
        for year in (2021, 2022)
    ]
    performance = []

    for year in (2023, 2024, 2025):
        predictions, metrics = core.run_oos(panel, year - 1, year)
        model_metrics = metrics[0]
        persistence_metrics = metrics[1]
        lower, upper = aggregate_interval(predictions)
        history.append(
            {
                "ano": year,
                "tipo": "backtest_oos",
                "observado": float(model_metrics["observado_total"]),
                "previsto_ppml": float(model_metrics["previsto_total"]),
                "limite_95_inf": lower,
                "limite_95_sup": upper,
                "previsto_persistencia": float(persistence_metrics["previsto_total"]),
                "quebra_cobertura": year == 2024,
            }
        )
        performance.append(
            {
                "ano": year,
                "treino": f"2021-{year - 1}",
                "wape_ppml": float(model_metrics["wape"]),
                "vies_ppml": float(model_metrics["vies_relativo"]),
                "cobertura_95_celulas": float(model_metrics["cobertura_95"]),
                "wape_persistencia": float(persistence_metrics["wape"]),
                "vies_persistencia": float(persistence_metrics["vies_relativo"]),
                "observado_total": float(model_metrics["observado_total"]),
                "previsto_ppml": float(model_metrics["previsto_total"]),
                "quebra_cobertura": year == 2024,
            }
        )

    forecast = pd.read_csv(FORECAST_2026_FILE)
    total = forecast.loc[forecast["grupamento"].eq("Total")].iloc[0]
    history.append(
        {
            "ano": 2026,
            "tipo": "previsao",
            "observado": np.nan,
            "previsto_ppml": float(total["previsao_2026"]),
            "limite_95_inf": float(total["limite_95_inf"]),
            "limite_95_sup": float(total["limite_95_sup"]),
            "previsto_persistencia": float(total["persistencia_2026"]),
            "quebra_cobertura": False,
        }
    )

    history = pd.DataFrame(history)
    performance = pd.DataFrame(performance)
    history["modelo"] = "PPML com efeitos fixos territoriais e por faixa etaria"
    history["intervalo"] = "Preditivo condicional de 95%"
    return history, performance


def format_number(value):
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}".replace(",", ".")


def format_percent(value):
    if pd.isna(value):
        return "-"
    return f"{100 * value:.1f}%".replace(".", ",")


def make_figure(history):
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    observed = history[history["observado"].notna()]
    predicted = history[history["previsto_ppml"].notna()]
    interval = predicted[predicted["limite_95_inf"].notna()]

    ax.plot(observed["ano"], observed["observado"], color="#1f2937", marker="o", linewidth=2.2, label="Observado")
    ax.plot(predicted["ano"], predicted["previsto_ppml"], color="#006d77", marker="o", linewidth=2.2, label="PPML")
    ax.fill_between(
        interval["ano"].to_numpy(),
        interval["limite_95_inf"].to_numpy(),
        interval["limite_95_sup"].to_numpy(),
        color="#83c5be",
        alpha=0.35,
        label="Intervalo preditivo 95%",
    )
    ax.scatter([2024], [history.loc[history["ano"].eq(2024), "observado"].iloc[0]], color="#e76f51", s=75, zorder=5)
    ax.axvline(2025.5, color="#9ca3af", linestyle="--", linewidth=1)
    ax.text(2025.55, ax.get_ylim()[0], "projecao", color="#6b7280", fontsize=9, va="bottom")
    ax.set_title("Demanda por creche: observado, backtests e previsao de 2026", loc="left", fontweight="bold")
    ax.set_ylabel("Criancas inscritas")
    ax.set_xticks(range(2021, 2027))
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURE_FILE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_report(history, performance):
    row_2025 = performance.loc[performance["ano"].eq(2025)].iloc[0]
    row_2026 = history.loc[history["ano"].eq(2026)].iloc[0]

    history_rows = []
    for row in history.itertuples(index=False):
        note = "Quebra de cobertura na extracao" if row.quebra_cobertura else row.tipo.replace("_", " ")
        history_rows.append(
            "<tr>"
            f"<td>{row.ano}</td><td>{html.escape(note)}</td>"
            f"<td>{format_number(row.observado)}</td>"
            f"<td>{format_number(row.previsto_ppml)}</td>"
            f"<td>[{format_number(row.limite_95_inf)}; {format_number(row.limite_95_sup)}]</td>"
            f"<td>{format_number(row.previsto_persistencia)}</td>"
            "</tr>"
        )

    performance_rows = []
    for row in performance.itertuples(index=False):
        label = f"{row.ano}" + ("*" if row.quebra_cobertura else "")
        performance_rows.append(
            "<tr>"
            f"<td>{label}</td><td>{row.treino}</td>"
            f"<td>{format_percent(row.wape_ppml)}</td>"
            f"<td>{format_percent(row.vies_ppml)}</td>"
            f"<td>{format_percent(row.cobertura_95_celulas)}</td>"
            f"<td>{format_percent(row.wape_persistencia)}</td>"
            "</tr>"
        )

    document = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Performance historica do modelo de demanda</title>
<style>
:root{{--ink:#16212b;--muted:#5f6b76;--teal:#006d77;--pale:#edf7f6;--line:#d8e0e5;--warn:#fff4e8}}
*{{box-sizing:border-box}} body{{margin:0;background:#f4f6f7;color:var(--ink);font:15px/1.5 Arial,sans-serif}}
main{{max-width:1050px;margin:32px auto;padding:0 22px}} .hero{{background:white;border-radius:14px;padding:28px 30px;border:1px solid var(--line)}}
h1{{margin:0 0 8px;font-size:30px;letter-spacing:-.4px}} h2{{margin-top:30px;font-size:20px}} p{{color:var(--muted)}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}} .card{{background:var(--pale);padding:15px;border-radius:10px}}
.card span{{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}} .card strong{{font-size:23px;color:var(--teal)}}
img{{width:100%;background:white;border-radius:10px;border:1px solid var(--line);margin:8px 0 12px}}
table{{width:100%;border-collapse:collapse;background:white;font-size:13px}} th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:right}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}} th{{background:#eef2f3}}
.note{{background:var(--warn);border-left:4px solid #e76f51;padding:12px 14px;color:#6b4b2a}} code{{background:#eef2f3;padding:2px 5px;border-radius:4px}}
@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}} .table-wrap{{overflow:auto}}}}
</style>
</head>
<body><main><section class="hero">
<h1>Performance historica e previsao de demanda</h1>
<p><strong>Alvo:</strong> numero de criancas inscritas, contando cada crianca uma vez. O modelo e um PPML com efeitos fixos de territorio e faixa etaria, tendencia por faixa e exposicao da coorte elegivel.</p>
<div class="cards">
<div class="card"><span>WAPE OOS 2025</span><strong>{format_percent(row_2025["wape_ppml"])}</strong></div>
<div class="card"><span>Vies 2025</span><strong>{format_percent(row_2025["vies_ppml"])}</strong></div>
<div class="card"><span>Previsao 2026</span><strong>{format_number(row_2026["previsto_ppml"])}</strong></div>
<div class="card"><span>Intervalo 95%</span><strong>{format_number(row_2026["limite_95_inf"])}-{format_number(row_2026["limite_95_sup"])}</strong></div>
</div>
<img src="performance_modelo_demanda.png" alt="Observado, previsao e intervalo preditivo">
<div class="note"><strong>Leitura de 2024:</strong> o salto inclui a entrada de centenas de creches parceiras na extracao. O erro desse ano mede conjuntamente previsao e mudanca de cobertura; por isso 2025 e o teste operacional mais comparavel.</div>

<h2>Serie anual</h2>
<div class="table-wrap"><table><thead><tr><th>Ano</th><th>Status</th><th>Observado</th><th>PPML</th><th>Intervalo 95%</th><th>Persistencia</th></tr></thead>
<tbody>{''.join(history_rows)}</tbody></table></div>

<h2>Performance fora da amostra</h2>
<div class="table-wrap"><table><thead><tr><th>Ano</th><th>Treino</th><th>WAPE PPML</th><th>Vies PPML</th><th>Cobertura 95%</th><th>WAPE persistencia</th></tr></thead>
<tbody>{''.join(performance_rows)}</tbody></table></div>
<p>* 2024 tem quebra de cobertura. WAPE e o erro absoluto total dividido pela demanda observada. A cobertura mede a proporcao de celulas territorio-faixa cujo realizado caiu no intervalo.</p>

<h2>Como interpretar</h2>
<p>O ponto de 2026 e a melhor estimativa do modelo. O intervalo de 95% e preditivo e condicional: incorpora a dispersao historica das contagens, mas nao incerteza sobre revisoes futuras da base ou mudancas de cobertura. Ele e mais apropriado para planejamento do que um intervalo apenas dos coeficientes.</p>
<p>Arquivos reproduziveis: <code>previsao_historica_2021_2026.csv</code> e <code>performance_historica_2023_2025.csv</code>.</p>
</section></main></body></html>"""
    REPORT_FILE.write_text(document, encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history, performance = build_tables()
    history.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    performance.to_csv(PERFORMANCE_FILE, index=False, encoding="utf-8-sig")
    make_figure(history)
    make_report(history, performance)
    print(history.to_string(index=False))
    print(f"\nRelatorio: {REPORT_FILE}")
    print(f"Historico: {HISTORY_FILE}")
    print(f"Performance: {PERFORMANCE_FILE}")


if __name__ == "__main__":
    main()
