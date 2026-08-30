from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


MODEL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODEL_DIR / "results"
FIGURES_DIR = MODEL_DIR / "figures"
OUTPUT_PATH = MODEL_DIR / "modelo_f1.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2C7FB8")
TEAL = colors.HexColor("#168C8C")
ORANGE = colors.HexColor("#F28E2B")
RED = colors.HexColor("#C14953")
INK = colors.HexColor("#24313A")
MUTED = colors.HexColor("#5E6B73")
LIGHT = colors.HexColor("#EEF3F6")
PALE_TEAL = colors.HexColor("#E7F4F2")
PALE_ORANGE = colors.HexColor("#FFF3E6")
WHITE = colors.white


def register_fonts():
    regular = Path(r"C:\Windows\Fonts\arial.ttf")
    bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    italic = Path(r"C:\Windows\Fonts\ariali.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("AuditSans", str(regular)))
        pdfmetrics.registerFont(TTFont("AuditSans-Bold", str(bold)))
        if italic.exists():
            pdfmetrics.registerFont(TTFont("AuditSans-Italic", str(italic)))
        else:
            pdfmetrics.registerFont(TTFont("AuditSans-Italic", str(regular)))
        return "AuditSans", "AuditSans-Bold", "AuditSans-Italic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


FONT, FONT_BOLD, FONT_ITALIC = register_fonts()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName=FONT_BOLD,
        fontSize=27,
        leading=31,
        textColor=NAVY,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSubtitle",
        fontName=FONT,
        fontSize=13,
        leading=18,
        textColor=MUTED,
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        name="H1Audit",
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=NAVY,
        spaceAfter=8,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="H2Audit",
        fontName=FONT_BOLD,
        fontSize=11.5,
        leading=14,
        textColor=TEAL,
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyAudit",
        fontName=FONT,
        fontSize=9.2,
        leading=13.2,
        textColor=INK,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallAudit",
        fontName=FONT,
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletAudit",
        fontName=FONT,
        fontSize=9,
        leading=12.5,
        textColor=INK,
        leftIndent=12,
        firstLineIndent=-7,
        bulletIndent=2,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="EquationAudit",
        fontName=FONT,
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        textColor=NAVY,
        backColor=LIGHT,
        borderColor=colors.HexColor("#D5E0E7"),
        borderWidth=0.5,
        borderPadding=9,
        spaceBefore=8,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="RefAudit",
        fontName=FONT,
        fontSize=7.4,
        leading=10.2,
        textColor=INK,
        leftIndent=13,
        firstLineIndent=-13,
        spaceAfter=4,
    )
)


def paragraph(text, style="BodyAudit"):
    return Paragraph(text, styles[style])


def heading(title, kicker=None):
    items = []
    if kicker:
        items.append(
            Paragraph(
                escape(kicker.upper()),
                ParagraphStyle(
                    name=f"Kicker-{kicker}",
                    parent=styles["SmallAudit"],
                    fontName=FONT_BOLD,
                    textColor=ORANGE,
                    spaceAfter=4,
                ),
            )
        )
    items.append(paragraph(escape(title), "H1Audit"))
    items.append(HRFlowable(width="100%", thickness=1.2, color=TEAL, spaceAfter=10))
    return items


def bullet(text):
    return Paragraph(f"• {text}", styles["BulletAudit"])


def callout(title, text, background=PALE_ORANGE, border=ORANGE):
    content = Paragraph(
        f"<b>{escape(title)}</b><br/>{text}",
        ParagraphStyle(
            name=f"Callout-{title}",
            parent=styles["BodyAudit"],
            fontSize=8.7,
            leading=12.3,
            textColor=INK,
            spaceAfter=0,
        ),
    )
    table = Table([[content]], colWidths=[174 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.8, border),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return KeepTogether([table, Spacer(1, 7)])


def make_table(data, widths, font_size=7.5, header_color=NAVY, alignments=None):
    wrapped = []
    for row_index, row in enumerate(data):
        wrapped_row = []
        for cell in row:
            style = ParagraphStyle(
                name=f"Cell-{row_index}-{len(wrapped_row)}",
                parent=styles["SmallAudit"],
                fontName=FONT_BOLD if row_index == 0 else FONT,
                fontSize=font_size,
                leading=font_size + 2.2,
                textColor=WHITE if row_index == 0 else INK,
                alignment=TA_LEFT,
                spaceAfter=0,
            )
            wrapped_row.append(Paragraph(str(cell), style))
        wrapped.append(wrapped_row)
    table = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D5DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index in range(1, len(wrapped)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT))
    if alignments:
        for column_index, alignment in enumerate(alignments):
            commands.append(("ALIGN", (column_index, 1), (column_index, -1), alignment))
    table.setStyle(TableStyle(commands))
    return table


def card(number, label, color=TEAL):
    number_style = ParagraphStyle(
        name=f"CardNumber-{label}",
        parent=styles["CoverTitle"],
        fontSize=19,
        leading=22,
        textColor=color,
        alignment=TA_CENTER,
    )
    label_style = ParagraphStyle(
        name=f"CardLabel-{label}",
        parent=styles["SmallAudit"],
        fontSize=7.4,
        leading=9,
        alignment=TA_CENTER,
        textColor=MUTED,
    )
    return [Paragraph(number, number_style), Paragraph(label, label_style)]


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#D5E0E7"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9.5 * mm, "Frente 1 — universo e entrada na rede | versão 0.1 para auditoria")
    canvas.drawRightString(width - 18 * mm, 9.5 * mm, f"p. {doc.page}")
    canvas.restoreState()


def link(label, url):
    return f'<link href="{url}" color="#2C7FB8"><u>{escape(label)}</u></link>'


def build_pdf():
    metrics = pd.read_csv(RESULTS_DIR / "f1_oos.csv")
    forecast = pd.read_csv(RESULTS_DIR / "f1_resumo_2026.csv")
    audit = pd.read_csv(RESULTS_DIR / "f1_auditoria.csv")
    flows = pd.read_csv(RESULTS_DIR / "f1_fluxos.csv")

    metric_model = metrics[metrics["modelo"] == "PPML-FE ridge"].set_index("ano_teste")
    metric_persistence = metrics[metrics["modelo"] == "Persistencia taxa t-1"].set_index("ano_teste")
    forecast_total = forecast[forecast["grupamento"] == "Total"].iloc[0]
    audit_map = dict(zip(audit["indicador"], audit["valor"]))

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title="Frente 1 — Universo e entrada na rede",
        author="Pedro — projeto de previsão de demanda por creches",
        subject="Modelo inicial, auditoria de dados e validação fora da amostra",
    )
    story = []

    # Cover
    story.append(Spacer(1, 16 * mm))
    story.append(paragraph("FRENTE 1 · NOTA TÉCNICA 0.1", "SmallAudit"))
    story.append(paragraph("Universo e entrada<br/>na rede de creches", "CoverTitle"))
    story.append(
        paragraph(
            "Auditoria das bases locais, definição do alvo, primeira estimação e validação fora da amostra em 2024 e 2025.",
            "CoverSubtitle",
        )
    )
    story.append(HRFlowable(width="100%", thickness=2.2, color=TEAL, spaceAfter=12))
    cards = Table(
        [
            [
                card("837.179", "linhas de opções"),
                card("296.084", "crianças-ano únicas", BLUE),
                card("98,7%", "cobertura geográfica", ORANGE),
            ]
        ],
        colWidths=[58 * mm, 58 * mm, 58 * mm],
    )
    cards.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E0E7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E0E7")),
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(cards)
    story.append(Spacer(1, 10 * mm))
    story.append(
        callout(
            "Limite de uso",
            "A documentação local afirma que os registros foram anonimizados e que os indicadores gerados <b>não representam a realidade</b>. Assim, os números desta nota validam o pipeline e a estratégia de previsão; não são estimativas oficiais de demanda para alocação de recursos.",
            background=colors.HexColor("#FCEBEC"),
            border=RED,
        )
    )
    story.append(Spacer(1, 10 * mm))
    story.append(paragraph("Data de corte: 30 de agosto de 2026", "SmallAudit"))
    story.append(paragraph("Arquivos originais preservados; novos artefatos gravados apenas em Pedro/Modelo.", "SmallAudit"))
    story.append(PageBreak())

    # Executive decisions
    story.extend(heading("Decisões que ficam congeladas nesta versão", "Resumo executivo"))
    decision_rows = [
        ["Decisão", "Versão 0.1", "Por quê"],
        ["Alvo", "criança única × ano × território × grupamento", "A chave de inscrição superestima o total em 15,95%; opções e registros repetidos não são novas crianças."],
        ["Território inicial", "bairro de residência", "É a menor unidade comum entre inscrições e nascimentos disponível na pasta."],
        ["Evento", "inscrição inicial, qualquer situação final", "Confirmação, cancelamento e fila ocorrem depois e dependem de capacidade/classificação."],
        ["Universo", "coortes de nascimentos por bairro/ano", "Fluxo administrativo anual observado; é superior a interpolar idade em pequena área quando o dado não existe."],
        ["Estimador", "PPML com offset, indicadores territoriais ridge e tendência por grupamento", "O alvo é contagem e a exposição varia muito entre bairros."],
        ["Validação", "origem expansiva 2024 e 2025", "Replica a informação disponível na data de cada previsão; sem embaralhar anos."],
    ]
    story.append(make_table(decision_rows, [31 * mm, 56 * mm, 87 * mm], font_size=7.4))
    story.append(Spacer(1, 8))
    story.append(
        callout(
            "Conclusão executiva",
            f"A previsão técnica para 2026 é <b>{forecast_total['previsao_2026']:,.0f}</b> inscrições no universo anonimizado, contra <b>{forecast_total['persistencia_2026']:,.0f}</b> no cenário de persistência. O intervalo condicional de 95% do PPML-NB é [{forecast_total['limite_95_inf']:,.0f}; {forecast_total['limite_95_sup']:,.0f}]. A discrepância entre cenários é material e deve permanecer visível para decisão.",
            background=PALE_TEAL,
            border=TEAL,
        )
    )
    story.append(paragraph("O modelo ainda não contém renda, emprego ou CadÚnico, porque nenhuma dessas bases com granularidade residencial local e frequência anual está presente no diretório. Inserir proxies municipais ou do local de trabalho produziria falsa precisão.", "BodyAudit"))
    story.append(PageBreak())

    # Inventory
    story.extend(heading("O que existe na pasta e o que cada base mede", "Auditoria de dados"))
    inventory = [
        ["Base local", "Período / grão", "Cobertura observada", "Uso na Frente 1"],
        ["Query A — inscrições", "2021–2025; uma opção de creche por linha", "837.179 linhas; 343.308 chaves de inscrição; 296.084 crianças-ano", "Numerador após deduplicação por aluno_anon e ano."],
        ["Queries B/C — questionário", "2021–2025; resposta por pergunta/inscrição", "4.357.119 respostas; 97,62% das inscrições; 13 perguntas/ano", "Perfil condicional dos inscritos; não identifica a propensão da população."],
        ["NascidosvivosRJ.xlsx", "2016–2026; bairro × ano", "168 códigos, dos quais 2 residuais; 2026 está parcial", "Exposição por coorte. Para prever 2026 usam-se apenas 2022–2025."],
        ["Microáreas SME", "233 geometrias; estoque", "232 códigos; duplicidade 7.28; 1 geometria inválida", "Dimensão futura. Não há microárea de residência nas inscrições."],
        ["Oferta pública/parceira", "2021–2025; unidade/grupamento; layouts variáveis", "~1.547–1.560 linhas públicas/ano e 218–353 linhas parceiras/ano", "Covariada futura, com data de corte; não é denominador da demanda."],
        ["Unidades unificadas", "unidade; localização", "1.941 linhas principais + 1.914 parceiras; 871/872 unidades da Query A vinculadas", "Localização da unidade: essencial à Frente 2, insuficiente para residência da Frente 1."],
    ]
    story.append(make_table(inventory, [34 * mm, 41 * mm, 48 * mm, 51 * mm], font_size=6.8))
    story.append(Spacer(1, 7))
    story.append(callout("Achado de qualidade", "A malha contém duas geometrias com código <b>7.28</b> e uma geometria inválida. Antes de qualquer spatial join, é preciso definir se as duas partes devem ser dissolvidas e reparar a geometria de modo documentado.", background=PALE_ORANGE, border=ORANGE))
    story.append(paragraph("Fontes locais auditadas: README_dicionario_dados.md; README.txt da pasta OferecimentosEvagas; SME_Processo_Inscricao_Creche_parametrizações.docx; arquivos CSV, XLSX e shapefile do repositório.", "SmallAudit"))
    story.append(PageBreak())

    # Target
    story.extend(heading("Construção do alvo: contar crianças, não linhas", "Numerador A(m,g,t)"))
    story.append(paragraph("A Query A tem três camadas de multiplicidade: várias opções por inscrição, mais de uma inscrição da mesma criança no mesmo processo e reaparecimento da criança em anos distintos. A unidade estatística correta para a entrada anual na rede é (ano, aluno_anon). O endereço e o grupamento da primeira ocorrência cronológica resolvem conflitos raros; os conflitos serão mantidos em log de qualidade.", "BodyAudit"))
    dedup = [
        ["Ano", "chaves de inscrição", "crianças únicas", "excesso se não deduplicar"],
        ["2021", "73.283", "57.690", "27,03%"],
        ["2022", "64.055", "57.820", "10,78%"],
        ["2023", "51.331", "45.918", "11,79%"],
        ["2024", "82.690", "71.757", "15,24%"],
        ["2025", "71.949", "62.899", "14,39%"],
        ["Total", "343.308", "296.084", "15,95%"],
    ]
    story.append(make_table(dedup, [35 * mm, 46 * mm, 44 * mm, 49 * mm], font_size=7.6))
    story.append(Spacer(1, 8))
    story.append(paragraph("Definição operacional", "H2Audit"))
    story.append(paragraph("A(m,g,t) = número de valores distintos de aluno_anon no ano t, com residência harmonizada no território m e grupamento g, independentemente da situação posterior da opção.", "EquationAudit"))
    story.append(bullet("Não somar filas por creche: a mesma criança aparece em várias opções."))
    story.append(bullet("Não condicionar a Confirmado ou Lista de espera: isso mistura demanda inicial com oferta, prioridade e decisão administrativa."))
    story.append(bullet("Não usar endereço da creche para territorializar a criança: isso pertence à escolha condicional da Frente 2."))
    story.append(callout("Cobertura", f"Após harmonizar apenas variantes inequívocas de bairro, {audit_map['cobertura_geografica_pct']:.2f}% das crianças-ano entram no painel. Localidades ambíguas não foram imputadas à força.", background=PALE_TEAL, border=TEAL))
    story.append(PageBreak())

    # First and repeat
    story.extend(heading("Primeira inscrição versus reinscrição observada", "Decomposição de fluxos"))
    flow_table = [["Ano", "primeira observada", "reinscrição observada", "% reinscrição"]]
    for _, row in flows.iterrows():
        first = int(row.get("primeira_observada", 0))
        repeat = int(row.get("reinscricao_observada", 0))
        share = repeat / (first + repeat) if first + repeat else 0
        flow_table.append([str(int(row["ano"])), f"{first:,}".replace(",", "."), f"{repeat:,}".replace(",", "."), f"{100*share:.1f}%"])
    story.append(make_table(flow_table, [36 * mm, 47 * mm, 48 * mm, 43 * mm], font_size=7.8))
    story.append(Spacer(1, 8))
    story.append(paragraph("Uma reinscrição observada é a aparição da mesma hash aluno_anon em ano posterior. Em 2021, todas as crianças são classificadas como primeira observação por censura à esquerda; portanto, esse rótulo não equivale a “primeira inscrição da vida”. O salto para 18.166 reinscrições em 2025 pode refletir política, fila acumulada, mudança de cobertura ou mecanismo de geração da base — precisa de confirmação operacional.", "BodyAudit"))
    story.append(paragraph("Modelo modular recomendado", "H2Audit"))
    story.append(paragraph("A(m,g,t) = A_nova(m,g,t) + A_retorno(m,g,t)", "EquationAudit"))
    story.append(bullet("A_nova: universo de crianças elegíveis que nunca havia aparecido antes do corte observado."))
    story.append(bullet("A_retorno: estoque elegível de inscritos não atendidos e/ou candidatos que precisam renovar a manifestação de interesse."))
    story.append(bullet("Para produção, solicitar à SME a distinção nativa entre inscrição inicial, transferência, renovação automática e permanência em fila."))
    story.append(callout("Não usar o questionário como controle de entrada", "As respostas socioeconômicas são observadas somente depois que a família já se inscreveu. Elas descrevem quem entrou no cadastro, mas não permitem comparar inscritos e não inscritos; usá-las diretamente na equação de propensão cria seleção por construção."))
    story.append(PageBreak())

    # Universe
    story.extend(heading("Universo potencial e a taxa de entrada", "Denominador E(m,g,t)"))
    story.append(paragraph("O arquivo de nascidos vivos é uma exportação do SINASC por bairro de residência e ano. A fonte administrativa é apropriada para seguir coortes; a SMS informa que o SINASC foi implantado no Rio em 1993 e o TABNET oferece consultas de nascimentos desde 2006 [10].", "BodyAudit"))
    exposure_rows = [
        ["Grupamento", "Proxy de coorte na versão 0.1", "Justificativa nos registros"],
        ["Berçário", "Nasc(m,t−1) + Nasc(m,t−2)", "Concentra crianças de até dois anos no ano letivo."],
        ["Maternal I", "Nasc(m,t−3)", "Coorte modal compatível com idade observada."],
        ["Maternal II", "Nasc(m,t−4)", "Coorte modal compatível com idade observada."],
    ]
    story.append(make_table(exposure_rows, [38 * mm, 58 * mm, 78 * mm], font_size=7.6))
    story.append(Spacer(1, 7))
    story.append(paragraph("p(m,g,t) = E[A(m,g,t) | informação disponível antes da inscrição] / E(m,g,t)", "EquationAudit"))
    story.append(paragraph("Essa taxa é uma propensão operacional de manifestação de demanda, não uma probabilidade causal. Na base anonimizada, ela pode inclusive exceder limites substantivos porque o README informa que os indicadores não preservam a realidade. Por isso o estimador trabalha a contagem com offset e o PDF evita interpretar p como porcentagem real.", "BodyAudit"))
    story.append(paragraph("Limitações do denominador atual", "H2Audit"))
    story.append(bullet("Ano, e não mês: o corte exato de 6 meses a 3 anos e 11 meses não pode ser aplicado ao universo."))
    story.append(bullet("Bairro, e não microárea: não há alocação direta dos nascimentos aos 232 códigos territoriais."))
    story.append(bullet("Mudanças de bairro: novos códigos têm séries históricas nulas e exigem ponte territorial estável."))
    story.append(bullet("Migração entre nascimento e inscrição não é observada."))
    story.append(callout("Próxima base prioritária", "Solicitar SINASC com mês de nascimento e residência geocodificada ou já agregada por microárea, sob governança adequada. Esse pedido melhora mais o denominador do que adicionar muitas covariadas de baixa granularidade."))
    story.append(PageBreak())

    # Model
    story.extend(heading("Primeiro modelo estimado", "PPML com exposição"))
    story.append(paragraph("Para cada bairro m, grupamento g e ano t, a versão 0.1 estima:", "BodyAudit"))
    story.append(paragraph("A(m,g,t) ~ Poisson(μ(m,g,t))<br/>log μ(m,g,t) = log E(m,g,t) + α(m) + γ(g) + δ(g)·(t−2021)", "EquationAudit"))
    story.append(paragraph("α(m) são indicadores de bairro, γ(g) diferenças médias entre grupamentos e δ(g) tendências específicas. Os indicadores são estabilizados com ridge (α = 10⁻⁴) porque há até 166 bairros, três grupamentos e somente três a cinco anos no treino. O PPML é coerente com uma média condicional multiplicativa de contagem e tem fundamentos para painéis com heterogeneidade multiplicativa [4]. Modelar diretamente uma fração seria alternativa quando o denominador real estiver validado [5].", "BodyAudit"))
    model_rows = [
        ["Componente", "Incluído agora?", "Regra temporal"],
        ["Coorte elegível", "Sim, como offset", "Conhecida antes do ano previsto."],
        ["Efeito territorial", "Sim, bairro", "Somente histórico do treino."],
        ["Tendência por grupamento", "Sim", "Extrapolável para ano futuro."],
        ["Efeito fixo de ano", "Não no forecast", "Um dummy de 2025 não existe ao prever 2025; seria inestimável fora da amostra."],
        ["Demanda defasada", "Benchmark, não regressora", "Painel curto gera risco de viés dinâmico [9]."],
        ["Renda/emprego/CadÚnico", "Não", "Ausentes em granularidade residencial compatível."],
        ["Oferta/capacidade", "Não nesta versão", "Precisa estar congelada antes da inscrição e ligada ao território de residência."],
    ]
    story.append(make_table(model_rows, [42 * mm, 37 * mm, 95 * mm], font_size=7.3))
    story.append(Spacer(1, 8))
    story.append(paragraph("A literatura econômica torna renda, emprego materno, preço/acesso e estrutura familiar candidatos substantivos [1–3]. Porém, acesso à creche também altera emprego e renda; no experimento do Rio, acesso gratuito afetou resultados laborais maternos [1]. Logo, covariadas contemporâneas podem ter causalidade reversa. Para previsão, usar valores defasados e tratar coeficientes como preditivos, não causais.", "BodyAudit"))
    story.append(PageBreak())

    # OOS
    story.extend(heading("Validação fora da amostra: 2024 e 2025", "Resultados"))
    story.append(paragraph("A avaliação segue origem expansiva: treina 2021–2023 e prevê 2024; depois treina 2021–2024 e prevê 2025. Esse desenho preserva a ordem temporal e explicita atualização/reestimação, como recomendado na literatura de testes OOS [7].", "BodyAudit"))
    metric_rows = [["Teste", "Modelo", "Obs.", "Prev.", "WAPE", "Viés", "MAE", "Cob. 95%"]]
    for year in [2024, 2025]:
        for label, table in [("PPML-FE", metric_model), ("Persistência", metric_persistence)]:
            row = table.loc[year]
            coverage = "—" if pd.isna(row["cobertura_95"]) else f"{100*row['cobertura_95']:.1f}%"
            metric_rows.append(
                [
                    str(year),
                    label,
                    f"{row['observado_total']:,.0f}".replace(",", "."),
                    f"{row['previsto_total']:,.0f}".replace(",", "."),
                    f"{100*row['wape']:.1f}%",
                    f"{100*row['vies_relativo']:+.1f}%",
                    f"{row['mae']:.1f}",
                    coverage,
                ]
            )
    story.append(make_table(metric_rows, [18 * mm, 30 * mm, 25 * mm, 25 * mm, 20 * mm, 20 * mm, 18 * mm, 18 * mm], font_size=6.9))
    story.append(Spacer(1, 7))
    image_path = FIGURES_DIR / "f1_oos.png"
    if image_path.exists():
        story.append(Image(str(image_path), width=167 * mm, height=86.8 * mm))
    story.append(Spacer(1, 4))
    story.append(paragraph("Leitura: 2024 é uma quebra estrutural/operacional, não um erro pequeno de calibração. O PPML subestima o total em 39,8% e a persistência em 38,9%. Em 2025, o PPML reduz o viés agregado para +5,2%, mas a persistência tem WAPE menor (16,0% contra 24,0%). Os intervalos condicionais também subcobrem, sobretudo em 2024; seguindo Gneiting e Raftery [8], cobertura e largura precisam ser avaliadas conjuntamente, e não apenas o ponto médio.", "SmallAudit"))
    story.append(PageBreak())

    # Forecast
    story.extend(heading("Primeira estimativa para 2026", "Cenário técnico"))
    forecast_rows = [["Grupamento", "universo proxy", "PPML-FE", "persistência", "intervalo PPML 95%"]]
    for _, row in forecast.iterrows():
        forecast_rows.append(
            [
                row["grupamento"],
                f"{row['universo_proxy']:,.0f}".replace(",", "."),
                f"{row['previsao_2026']:,.0f}".replace(",", "."),
                f"{row['persistencia_2026']:,.0f}".replace(",", "."),
                f"[{row['limite_95_inf']:,.0f}; {row['limite_95_sup']:,.0f}]".replace(",", "."),
            ]
        )
    story.append(make_table(forecast_rows, [36 * mm, 34 * mm, 30 * mm, 31 * mm, 43 * mm], font_size=7.3))
    story.append(Spacer(1, 10))
    story.append(callout("Número de referência", f"PPML-FE: <b>{forecast_total['previsao_2026']:,.0f}</b>. Persistência: <b>{forecast_total['persistencia_2026']:,.0f}</b>. Diferença: <b>{forecast_total['previsao_2026']-forecast_total['persistencia_2026']:,.0f}</b> crianças na base anonimizada.", background=PALE_TEAL, border=TEAL))
    story.append(paragraph("O intervalo exibido usa uma distribuição binomial negativa com dispersão estimada nos resíduos (α ≈ 0,0529), condicionada aos parâmetros e ao universo proxy. Ele não incorpora integralmente erro no SINASC, incerteza de geocodificação, mudança de política ou erro de estimação dos efeitos territoriais. Portanto, é um intervalo mínimo, não uma banda de risco de política pública.", "BodyAudit"))
    story.append(paragraph("Por que não escolher automaticamente o PPML", "H2Audit"))
    story.append(bullet("Há apenas dois anos OOS; um deles contém quebra severa."))
    story.append(bullet("O challenger de persistência venceu o PPML em WAPE nos dois testes."))
    story.append(bullet("A previsão pontual deve ser reportada como faixa de cenários até que 2024 seja explicado e os dados reais substituam os anonimizados."))
    story.append(paragraph("Recomendação de auditoria: manter ambos os cenários no painel decisório; promover um modelo a campeão somente após reprocessar dados reais, fixar o corte anual e repetir backtests em mais anos ou origens mensais.", "BodyAudit"))
    story.append(PageBreak())

    # Socioeconomic bases
    story.extend(heading("Renda, emprego e vulnerabilidade: o que é utilizável", "Bases externas e Data Lake"))
    sources = [
        ["Fonte", "Frequência", "Granularidade pública", "Veredito para a Frente 1"],
        ["RAIS / Novo Caged", "anual / mensal", "microdados não identificados; geografia pública não garante residência em microárea", "Não usar como emprego residencial local sem validar campo e série; local do estabelecimento mede outra coisa [14]."],
        ["CadÚnico aberto", "amostra anual; agregados municipais mensais", "público chega tipicamente ao município; acesso identificado exige autorização", "Insuficiente para microárea pública. Solicitar agregado anual/mensal por residência à gestão municipal [15]."],
        ["Questionário da inscrição", "anual", "resposta individual dos inscritos", "Não estima a probabilidade de entrar; pode caracterizar composição e classificação."],
        ["Data Lake municipal", "depende da tabela", "BigQuery com permissões por projeto", "Infraestrutura confirmada, mas o catálogo público não comprova tabelas específicas de CadÚnico/SME. É necessário acesso e inventário de schema [13]."],
        ["Habite-se / novas moradias", "não presente", "não verificada nesta pasta", "Candidata, desde que geocodificada e congelada antes do ano previsto."],
    ]
    story.append(make_table(sources, [34 * mm, 26 * mm, 55 * mm, 59 * mm], font_size=6.7))
    story.append(Spacer(1, 8))
    story.append(paragraph("Pedido mínimo ao Data Lake / SME", "H2Audit"))
    story.append(bullet("Snapshot anual da inscrição inicial, hash estável da criança, data do evento, grupamento e microárea de residência."))
    story.append(bullet("CadÚnico agregado por microárea e ano-mês: crianças elegíveis, renda per capita, monoparentais, responsável feminino ocupado e benefícios; sem identificadores."))
    story.append(bullet("Estoque anterior: matriculados, não atendidos e renovações por microárea/grupamento, todos no mesmo corte."))
    story.append(bullet("Oferta conhecida antes da inscrição: capacidade pública/parceira, turno, abertura e fechamento."))
    story.append(callout("Critério de admissibilidade", "Uma variável só entra no forecast se tiver: residência local compatível; atualização ao menos anual; histórico 2021–2025; data de disponibilidade anterior ao alvo; dicionário estável; e plano explícito para revisões."))
    story.append(PageBreak())

    # Risks and roadmap
    story.extend(heading("Riscos, testes de robustez e próxima iteração", "Plano de auditoria"))
    risk_rows = [
        ["Risco", "Evidência atual", "Teste / correção"],
        ["Quebra em 2024", "inscritos sobem de 45.918 para 71.757; unidades na Query A de 496 para 844", "Separar mudança de cobertura, inclusão de parceiras e mudança de processo; reconstruir universo comparável."],
        ["Geografia", "bairro informado; 1,1% dos registros múltiplos têm CEP conflitante", "Usar residência na data da primeira inscrição; crosswalk CEP→microárea versionado; auditoria de fronteiras."],
        ["Denominador", "nascimentos anuais, sem mês", "Obter mês/microárea; comparar com projeção etária e matrículas passadas."],
        ["Painel curto", "cinco anos e muitos efeitos", "Shrinkage hierárquico; comparar pooling, ridge e intercepto aleatório [6]."],
        ["Dinâmica", "reinscrições crescem fortemente em 2025", "Modelar fluxos separadamente; evitar FE dinâmico ingênuo devido ao viés de painel curto [9]."],
        ["Intervalos", "cobertura 95% de 43,9% em 2024 e 86,3% em 2025", "Bootstrap por território + cenários de coorte/política; avaliar interval score [8]."],
    ]
    story.append(make_table(risk_rows, [37 * mm, 64 * mm, 73 * mm], font_size=6.9))
    story.append(Spacer(1, 8))
    story.append(paragraph("Sequência recomendada", "H2Audit"))
    story.append(bullet("1. Explicar e documentar a quebra de 2024; sem isso, nenhum modelo de tendência é auditável."))
    story.append(bullet("2. Substituir a base anonimizada pelo extrato real agregado, com a mesma lógica de deduplicação."))
    story.append(bullet("3. Congelar a ponte bairro/microárea e a regra mensal de elegibilidade por grupamento."))
    story.append(bullet("4. Estimar A_nova e A_retorno separadamente; depois somar distribuições, não só médias."))
    story.append(bullet("5. Acrescentar covariadas uma a uma, exigindo ganho OOS contra persistência."))
    story.append(bullet("6. Publicar ficha do modelo: corte, versão das bases, cobertura, métricas e falhas conhecidas."))
    story.append(PageBreak())

    # Integration
    story.extend(heading("Contrato com a Frente 2", "Integração modular"))
    story.append(paragraph("A Frente 1 termina na quantidade prevista de inscrições por origem territorial e grupamento. A Frente 2 distribui essa massa entre unidades elegíveis. Nenhuma característica da unidade deve ser necessária para estimar o universo; e a Frente 2 deve validar escolha condicionando ao total efetivamente inscrito.", "BodyAudit"))
    story.append(paragraph("D_hat(i,g,t) = Σ_m A_hat(m,g,t) × P_hat(i | inscrição,m,g,t)", "EquationAudit"))
    contract = [
        ["Campo", "Frente 1", "Frente 2", "Regra"],
        ["ano", "obrigatório", "obrigatório", "Ano letivo/processo, não ano de criação bruto."],
        ["cod_territorio", "bairro na v0.1; microárea alvo", "origem da criança", "Uma tabela de ponte versionada."],
        ["grupamento", "Bercario, Maternal I, Maternal II", "mesmo domínio", "Sem renomear silenciosamente."],
        ["codigo_unidade", "não aparece no output granular", "obrigatório", "Entra somente na probabilidade condicional."],
        ["a_hat", "média prevista", "insumo", "Nunca arredondar antes da soma."],
        ["incerteza", "quantis/distribuição", "combinar com P_hat", "Evitar somar limites célula a célula como se fossem independentes."],
    ]
    story.append(make_table(contract, [31 * mm, 43 * mm, 38 * mm, 62 * mm], font_size=7.2))
    story.append(Spacer(1, 9))
    story.append(paragraph("Schema proposto para entrega", "H2Audit"))
    story.append(paragraph("ano | cod_territorio | tipo_territorio | grupamento | e_hat | a_hat | p10 | p50 | p90 | modelo | data_corte | versao", "EquationAudit"))
    story.append(callout("Auditoria antes da integração", "A soma de P_hat sobre unidades elegíveis deve ser 1 para cada (m,g,t). A Frente 1 deve reconciliar a soma de A_hat com seus totais publicados. O produto só é liberado quando ambas as identidades passarem."))
    story.append(PageBreak())

    # Reproducibility and references
    story.extend(heading("Reprodutibilidade e referências", "Materiais de auditoria"))
    files_table = [
        ["Artefato", "Função"],
        ["f1_est.py", "Leitura, deduplicação, painel, PPML, OOS, projeção e exportação."],
        ["results/f1_panel.csv", "Painel bairro × grupamento × ano construído sem sobrescrever originais."],
        ["results/f1_oos_pred.csv", "Previsões célula a célula nos dois testes."],
        ["results/f1_oos.csv / .tex", "Tabela de métricas."],
        ["results/f1_prev_2026.csv", "Primeira projeção territorial completa."],
        ["results/f1_resumo_2026.csv / .tex", "Resumo por grupamento e total."],
        ["figures/f1_oos.png", "Figura usada nesta nota."],
    ]
    story.append(make_table(files_table, [60 * mm, 114 * mm], font_size=7.2))
    story.append(Spacer(1, 8))
    story.append(paragraph("Referências acadêmicas", "H2Audit"))
    references = [
        ("[1]", "Barros, R. P.; Olinto, P.; Lunde, T.; Carvalho, M. (2013). The impact of access to free childcare on women's labor market outcomes: evidence from a randomized trial in low-income neighborhoods of Rio de Janeiro. World Bank.", "https://documents.worldbank.org/en/publication/documents-reports/documentdetail/672391468231860498"),
        ("[2]", "Heckman, J. J. (1974). Effects of Child-Care Programs on Women's Work Effort. Journal of Political Economy, 82(2).", "https://doi.org/10.1086/260297"),
        ("[3]", "Blau, D. M.; Robins, P. K. (1988). Child-Care Costs and Family Labor Supply. Review of Economics and Statistics, 70(3), 374–381.", "https://www.jstor.org/stable/1926774"),
        ("[4]", "Wooldridge, J. M. (1999). Distribution-free estimation of some nonlinear panel data models. Journal of Econometrics, 90(1), 77–97.", "https://doi.org/10.1016/S0304-4076(98)00033-5"),
        ("[5]", "Papke, L. E.; Wooldridge, J. M. (1996). Econometric methods for fractional response variables. Journal of Applied Econometrics, 11(6), 619–632.", "https://doi.org/10.1002/(SICI)1099-1255(199611)11:6%3C619::AID-JAE418%3E3.0.CO;2-1"),
        ("[6]", "Rao, J. N. K.; Molina, I. (2015). Small Area Estimation, 2nd ed. Wiley.", "https://onlinelibrary.wiley.com/doi/book/10.1002/9781118735855"),
        ("[7]", "Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: an analysis and review. International Journal of Forecasting, 16(4), 437–450.", "https://doi.org/10.1016/S0169-2070(00)00065-0"),
        ("[8]", "Gneiting, T.; Raftery, A. E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. JASA, 102(477), 359–378.", "https://doi.org/10.1198/016214506000001437"),
        ("[9]", "Nickell, S. (1981). Biases in Dynamic Models with Fixed Effects. Econometrica, 49(6), 1417–1426.", "https://doi.org/10.2307/1911408"),
    ]
    for number, citation, url in references:
        story.append(Paragraph(f"{number} {escape(citation)} {link('fonte', url)}", styles["RefAudit"]))
    story.append(paragraph("Fontes oficiais e documentação", "H2Audit"))
    official = [
        ("[10]", "SMS Rio — SINASC e TABNET municipal.", "https://saude.prefeitura.rio/vigilancia-saude/dados-vitais/nascimentos/"),
        ("[11]", "SME Rio — Matrícula 2024: calendário, elegibilidade e processo classificatório.", "https://educacao.prefeitura.rio/matricula-2024/"),
        ("[12]", "SME Rio — Transparência Creches: fila, matrículas e capacidade com atualização prevista mensal.", "https://educacao.prefeitura.rio/transparenciacreches/"),
        ("[13]", "IplanRio — Data Lake Municipal e acesso via BigQuery.", "https://docs.dados.rio/data-lake/acesso-aos-dados/bigquery"),
        ("[14]", "MTE — Microdados RAIS e CAGED.", "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/microdados-rais-e-caged"),
        ("[15]", "MDS — dados e acesso ao Cadastro Único.", "https://www.gov.br/mds/pt-br/acoes-e-programas/cadastro-unico/dados-e-ferramentas-do-cadastro-unico"),
    ]
    for number, citation, url in official:
        story.append(Paragraph(f"{number} {escape(citation)} {link('fonte', url)}", styles["RefAudit"]))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build_pdf()
