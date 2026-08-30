from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from make_f1_pdf import (
    BLUE,
    FONT,
    FONT_BOLD,
    INK,
    LIGHT,
    MUTED,
    NAVY,
    ORANGE,
    PALE_ORANGE,
    PALE_TEAL,
    RED,
    TEAL,
    callout,
    heading,
    paragraph,
    styles,
)


MODEL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODEL_DIR / "results"
FIGURES_DIR = MODEL_DIR / "figures"
TMP_DIR = MODEL_DIR / "tmp" / "pdfs"
OUTPUT_DIR = MODEL_DIR / "output" / "pdf"

BASE_PDF = MODEL_DIR / "modelo_f1.pdf"
APPENDIX_PDF = TMP_DIR / "ap_cov.pdf"
OUTPUT_PDF = OUTPUT_DIR / "modelo_f1_cov.pdf"


def bullet(text):
    return Paragraph(f"• {text}", styles["BulletAudit"])


def appendix_footer(canvas, document):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#D5E0E7"))
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(FONT, 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9.5 * mm, "Apêndice de auditoria - covariadas externas")
    canvas.drawRightString(width - 18 * mm, 9.5 * mm, f"A{document.page}")
    canvas.restoreState()


def audit_table(rows, widths, font_size=7.2, alignments=None):
    formatted = []
    for row_index, row in enumerate(rows):
        style_name = "SmallAudit" if row_index else "SmallAudit"
        formatted.append([Paragraph(escape(str(value)), styles[style_name]) for value in row])
    table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D4DC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if alignments:
        for column, alignment in enumerate(alignments):
            commands.append(("ALIGN", (column, 1), (column, -1), alignment))
    table.setStyle(TableStyle(commands))
    return table


def make_appendix():
    metrics = pd.read_csv(RESULTS_DIR / "f1_cov_oos.csv")
    pooled = pd.read_csv(RESULTS_DIR / "f1_cov_oos_pooled.csv")
    annual_caged = pd.read_csv(RESULTS_DIR / "f1_cov_caged_anual.csv")
    rais_vintages = pd.read_csv(RESULTS_DIR / "f1_cov_rais_vintages.csv")
    forecast = pd.read_csv(RESULTS_DIR / "f1_cov_resumo_2026.csv")

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(APPENDIX_PDF),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=19 * mm,
        title="Apêndice de auditoria: RAIS, Novo Caged e Habite-se",
        author="Frente 1 - Universo e entrada na rede",
    )

    story = []
    story.extend(heading("Teste de RAIS, Novo Caged e Habite-se", "APÊNDICE DE AUDITORIA • 30 AGO 2026"))
    story.append(
        callout(
            "Resultado executivo",
            "O Novo Caged municipal <b>não melhorou a previsão de modo estável</b>. "
            "A variante que reduz o WAPE em 2024 piora 2025; as variantes que apenas adicionam "
            "Caged à especificação atual pioram os dois anos. RAIS e Habite-se não entram na "
            "estimação principal: a primeira não varia entre bairros e tem atraso/quebra de série; "
            "a segunda só foi localizada publicamente até 2015.",
            background=PALE_ORANGE,
            border=ORANGE,
        )
    )
    story.append(paragraph("Pergunta testada", "H2Audit"))
    story.append(
        paragraph(
            "A evolução do emprego formal pode explicar a fração do universo elegível que se inscreve? "
            "A literatura sustenta a relação entre cuidado infantil e oferta de trabalho parental, "
            "mas isso não torna qualquer medida de emprego uma boa covariada. Morrissey (2017) documenta "
            "heterogeneidade substancial nas respostas; Blau e Currie (2006) destacam a interação entre "
            "arranjos familiares, oferta e políticas de cuidado. Por isso o indicador precisa respeitar "
            "residência, tempo de disponibilidade e geografia do modelo."
        )
    )
    story.append(paragraph("Informação usada no teste", "H2Audit"))
    story.append(
        paragraph(
            "Foi extraída da Tabela 8.1 do Novo Caged a série mensal ajustada do município do Rio de "
            "Janeiro, 2020-2025. Para prever o ano t, usa-se somente a taxa de saldo formal do ano t-1 "
            "sobre o estoque inicial reconstruído. Assim, 2024 usa 2023 e 2025 usa 2024. A variável é "
            "idêntica para todos os bairros e grupamentos em cada ano."
        )
    )
    caged_rows = [["Ano", "Estoque inicial", "Estoque dez.", "Saldo", "Taxa (%)"]]
    for _, row in annual_caged.iterrows():
        caged_rows.append(
            [
                int(row["ano_indicador"]),
                f"{row['estoque_inicio_reconstruido']:,.0f}".replace(",", "."),
                f"{row['estoque_dezembro']:,.0f}".replace(",", "."),
                f"{row['saldo_ano']:,.0f}".replace(",", "."),
                f"{100 * row['taxa_saldo_estoque_inicio']:.2f}",
            ]
        )
    story.append(audit_table(caged_rows, [22 * mm, 39 * mm, 39 * mm, 32 * mm, 25 * mm], alignments=["CENTER"] * 5))
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "Interpretação correta",
            "É um choque conjuntural <b>municipal</b>, não emprego no entorno da creche e não emprego "
            "dos responsáveis residentes na microárea. Em um modelo com efeito fixo de ano, seria "
            "absorvido integralmente.",
            background=PALE_TEAL,
            border=TEAL,
        )
    )

    story.append(PageBreak())
    story.extend(heading("Desempenho fora da amostra", "2024 E 2025 • ORIGEM EXPANSIVA"))
    model_order = [
        "PPML-FE base replicado",
        "PPML-FE + Caged comum",
        "PPML-FE + Caged x grupo",
        "PPML-FE Caged x grupo sem tendencia",
        "Persistencia taxa t-1",
    ]
    labels = {
        "PPML-FE base replicado": "PPML-FE base",
        "PPML-FE + Caged comum": "+ Caged comum",
        "PPML-FE + Caged x grupo": "+ Caged x grupamento",
        "PPML-FE Caged x grupo sem tendencia": "Caged x grupo, sem tendência",
        "Persistencia taxa t-1": "Persistência t-1",
    }
    metric_rows = [["Modelo", "WAPE 2024", "WAPE 2025", "WAPE combinado", "Viés combinado"]]
    for model_name in model_order:
        model_metrics = metrics[metrics["modelo"] == model_name].set_index("ano_teste")
        pooled_row = pooled[pooled["modelo"] == model_name].iloc[0]
        metric_rows.append(
            [
                labels[model_name],
                f"{100 * model_metrics.loc[2024, 'wape']:.2f}%",
                f"{100 * model_metrics.loc[2025, 'wape']:.2f}%",
                f"{100 * pooled_row['wape_pooled']:.2f}%",
                f"{100 * pooled_row['vies_relativo_pooled']:.2f}%",
            ]
        )
    story.append(audit_table(metric_rows, [56 * mm, 27 * mm, 27 * mm, 30 * mm, 29 * mm], alignments=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Image(str(FIGURES_DIR / "f1_cov_oos.png"), width=169 * mm, height=85.3 * mm))
    story.append(paragraph("Leitura do teste", "H2Audit"))
    story.append(bullet("Adicionar Caged à tendência existente piora o WAPE em 10,68 p.p. em 2024 e 5,97 p.p. em 2025 na versão comum."))
    story.append(bullet("Substituir a tendência por Caged x grupamento melhora 2024 em 5,55 p.p., mas piora 2025 em 2,60 p.p.; o sinal de ganho não é replicado."))
    story.append(bullet("No agregado dos dois anos, a variante sem tendência tem WAPE de 31,33%, mas viés de -26,14%; a persistência continua melhor, com WAPE de 28,69%."))
    story.append(
        callout(
            "Decisão",
            "<b>Não incorporar Caged ao modelo principal nesta versão.</b> Manter como análise de "
            "sensibilidade e repetir quando houver mais origens OOS. Tashman (2000) recomenda múltiplas "
            "origens para reduzir conclusões dependentes de um único período.",
            background=PALE_ORANGE,
            border=ORANGE,
        )
    )

    story.append(PageBreak())
    story.extend(heading("Por que RAIS e Habite-se ficaram fora", "AUDITORIA DE ADMISSIBILIDADE"))
    story.append(paragraph("RAIS: estoque municipal, atraso e revisão", "H2Audit"))
    story.append(
        paragraph(
            "A RAIS pública permite município, não bairro ou microárea. Ela localiza o estabelecimento, "
            "não a residência do responsável. Além disso, o estoque de 2023 passou de 2.248.944 na "
            "divulgação 2022x2023 para 2.455.284 na divulgação 2023x2024: revisão de 9,18%. A nota técnica "
            "da RAIS 2023 alerta para quebra de série durante a transição ao eSocial. Croushore e Stark "
            "(2001) mostram por que testes de previsão devem preservar a vintage disponível em cada origem."
        )
    )
    rais_rows = [["Vintage", "Ano", "Estoque", "Revisão vs. 1ª (%)"]]
    for _, row in rais_vintages.iterrows():
        rais_rows.append(
            [
                row["arquivo_vintage"].replace(".xlsx", ""),
                int(row["ano_rais"]),
                f"{row['estoque_formal']:,.0f}".replace(",", "."),
                f"{row['revisao_vs_primeira_pct']:.3f}",
            ]
        )
    story.append(audit_table(rais_rows, [50 * mm, 24 * mm, 42 * mm, 42 * mm], alignments=["LEFT", "CENTER", "RIGHT", "RIGHT"]))
    story.append(Spacer(1, 4 * mm))
    story.append(
        callout(
            "Veredito RAIS",
            "Não somar RAIS e Caged ao mesmo painel curto como se fossem duas covariadas locais. "
            "Com apenas cinco anos, ambas carregam essencialmente variação temporal comum; a RAIS ainda "
            "chega tarde para uma previsão operacional no início do ano.",
            background=PALE_TEAL,
            border=TEAL,
        )
    )
    story.append(paragraph("Habite-se: geografia adequada, período inadequado", "H2Audit"))
    story.append(
        paragraph(
            "O catálogo oficial do Data.Rio contém planilhas por bairro/RA/AP, mas as séries localizadas "
            "terminam em 2014 ou 2015. O serviço db_MI_Licenciamento_2023 encontrado no ArcGIS contém "
            "apenas dois totais agregados do Reviver Centro até junho de 2023, sem endereço, bairro ou "
            "histórico anual municipal. Nenhuma dessas fontes se sobrepõe adequadamente ao painel 2021-2025."
        )
    )
    story.append(
        audit_table(
            [
                ["Fonte", "Frequência", "Geografia", "Período útil", "Decisão"],
                ["Novo Caged", "mensal", "município", "2020-2025", "testado; não retido"],
                ["RAIS", "anual", "município", "2020-2024", "auditoria; não estimar junto"],
                ["Habite-se Data.Rio", "anual", "bairro/RA/AP", "até 2015", "fora do período"],
                ["db_MI Licenciamento", "snapshot", "Reviver Centro agregado", "jun. 2023", "incompatível"],
            ],
            [37 * mm, 24 * mm, 38 * mm, 29 * mm, 41 * mm],
        )
    )

    story.append(PageBreak())
    story.extend(heading("Implicações para a previsão e próximos dados", "RECOMENDAÇÃO OPERACIONAL"))
    story.append(paragraph("Sensibilidade para 2026", "H2Audit"))
    forecast_rows = [["Especificação", "Previsão 2026", "Diferença vs. base"]]
    base_value = float(forecast.loc[forecast["modelo"] == "PPML-FE base replicado", "previsao_2026"].iloc[0])
    for _, row in forecast.iterrows():
        forecast_rows.append(
            [
                labels.get(row["modelo"], row["modelo"]),
                f"{row['previsao_2026']:,.0f}".replace(",", "."),
                f"{row['previsao_2026'] - base_value:+,.0f}".replace(",", "."),
            ]
        )
    forecast_rows.append(["Persistência t-1", "59.718", "-7.083"])
    story.append(audit_table(forecast_rows, [82 * mm, 40 * mm, 40 * mm], alignments=["LEFT", "RIGHT", "RIGHT"]))
    story.append(
        paragraph(
            "A amplitude de 49,7 mil a 73,7 mil inscrições mostra que, neste painel curto, trocar a forma "
            "da tendência por um único indicador temporal muda muito a extrapolação. Isso é evidência de "
            "instabilidade de especificação, não de informação local suficiente. A previsão principal de "
            "66,8 mil permanece inalterada; a persistência de 59,7 mil continua como benchmark obrigatório."
        )
    )
    story.append(paragraph("Extração que deve ser solicitada à Prefeitura", "H2Audit"))
    story.append(bullet("Habite-se/licenciamento de 2020-2025 com data de emissão, endereço ou coordenada, bairro, RA, uso e número de unidades residenciais."))
    story.append(bullet("Identificador estável do processo e status de cancelamento/retificação, para evitar duplicações e medir a vintage disponível em cada previsão."))
    story.append(bullet("RAIS/Caged agregados por residência dos responsáveis, ou microárea anonimizada da SME/CadÚnico, se juridicamente autorizado; estabelecimento não substitui residência."))
    story.append(bullet("Construir unidades residenciais concluídas em t-1, t-2 e t-3 por microárea e testá-las com as mesmas origens OOS de 2024 e 2025."))
    story.append(
        callout(
            "Regra de entrada futura",
            "Uma covariada só entra no modelo principal se (i) estiver disponível antes da previsão, "
            "(ii) variar na geografia de residência relevante, (iii) tiver definição estável e (iv) "
            "reduzir erro em mais de uma origem OOS sem ampliar materialmente o viés.",
            background=PALE_TEAL,
            border=TEAL,
        )
    )
    story.append(paragraph("Fontes de dados e literatura", "H2Audit"))
    references = [
        "[A1] MTE. Novo Caged - dezembro de 2025, Tabelas.xlsx, Tabela 8.1. https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/novo-caged/2025/dezembro/pagina-inicial",
        "[A2] MTE. RAIS 2024 - material de divulgação e tabelas 2023x2024. https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2024",
        "[A3] MTE. Nota Técnica RAIS 2023: transição ao eSocial e quebra de série. https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2023/nota-tecnica-rais-2023_11-12-2024.pdf",
        "[A4] Data.Rio. Habite-se por AP/RP/RA/bairro, 2013-2015. https://pcrj.maps.arcgis.com/home/item.html?id=c8c00560df354f89862ab2fab03966f1",
        "[A5] Blau, D.; Currie, J. (2006). Pre-School, Day Care, and After-School Care. DOI: 10.1016/S1574-0692(06)02020-4.",
        "[A6] Morrissey, T. W. (2017). Child care and parent labor force participation. DOI: 10.1007/s11150-016-9331-3.",
        "[A7] Croushore, D.; Stark, T. (2001). A real-time data set for macroeconomists. DOI: 10.1016/S0304-4076(01)00072-0.",
        "[A8] Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy. DOI: 10.1016/S0169-2070(00)00065-0.",
    ]
    for reference in references:
        story.append(Paragraph(escape(reference), styles["RefAudit"]))

    document.build(story, onFirstPage=appendix_footer, onLaterPages=appendix_footer)


def merge_pdfs():
    writer = PdfWriter()
    writer.append(str(BASE_PDF))
    writer.append(str(APPENDIX_PDF))
    with OUTPUT_PDF.open("wb") as stream:
        writer.write(stream)


def validate_pdf():
    reader = PdfReader(str(OUTPUT_PDF))
    expected_pages = len(PdfReader(str(BASE_PDF)).pages) + len(PdfReader(str(APPENDIX_PDF)).pages)
    if len(reader.pages) != expected_pages:
        raise ValueError(f"Expected {expected_pages} pages, found {len(reader.pages)}.")
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages[-4:])
    required_terms = ["Novo Caged", "RAIS", "Habite-se", "Desempenho fora da amostra"]
    missing_terms = [term for term in required_terms if term not in extracted_text]
    if missing_terms:
        raise ValueError(f"Missing expected appendix terms: {missing_terms}")
    print(OUTPUT_PDF)
    print(f"pages={len(reader.pages)}")


def main():
    make_appendix()
    merge_pdfs()
    validate_pdf()


if __name__ == "__main__":
    main()
