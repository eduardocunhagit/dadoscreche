from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT_PATH = Path(r"C:\Users\pedro\Documents\2026\ClaudeImpactLab2\Pedro\Modelo\modelo_creches.pdf")


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5DCE6"))
    canvas.line(2.0 * cm, 1.55 * cm, A4[0] - 2.0 * cm, 1.55 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#65758B"))
    canvas.drawString(2.0 * cm, 1.05 * cm, "Esboco de modelo - demanda por creches no municipio do Rio de Janeiro")
    canvas.drawRightString(A4[0] - 2.0 * cm, 1.05 * cm, f"Pagina {document.page}")
    canvas.restoreState()


def p(text, style):
    return Paragraph(text, style)


def main():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#163B65"),
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#52667D"),
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="HeadingCustom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#163B65"),
        spaceBefore=13,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#1E2936"),
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.3,
        leading=11,
        textColor=colors.HexColor("#263746"),
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        parent=styles["Small"],
        fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="Equation",
        parent=styles["BodyText"],
        fontName="Courier",
        fontSize=8.6,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#102A43"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#D4DEE9"),
        borderWidth=0.5,
        borderPadding=7,
        spaceBefore=5,
        spaceAfter=9,
    ))

    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=2.0 * cm,
        leftMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2.1 * cm,
        title="Esboco de modelo - demanda por creches",
        author="Pedro Forlevezi",
    )

    body = styles["BodyCustom"]
    story = [
        p("Esboco de modelo", styles["TitleCustom"]),
        p("Previsao de matriculas e demanda local por creches no municipio do Rio de Janeiro", styles["Subtitle"]),
        p("<b>Objetivo.</b> Construir um painel anual de creches para prever matriculas, ocupacao e, quando houver informacao complementar, demanda potencial por vagas. A unidade de observacao e a creche i no ano t.", body),
        p("<b>Questao central.</b> Matriculas observadas nao equivalem necessariamente a demanda: quando a unidade opera perto da capacidade, a oferta limita o resultado observado. Por isso, o modelo deve tratar capacidade, ocupacao e lista de espera como componentes distintos sempre que os dados permitirem.", body),
        p("Matriculas_it = min{Demanda_it, Capacidade_it}", styles["Equation"]),
        p("<b>Estrutura do painel.</b> O Censo Escolar do INEP e a base central porque permite acompanhar estabelecimentos ao longo do tempo. As covariadas demograficas e territoriais sao associadas a cada creche por bairro, Regiao Administrativa (RA) ou, preferencialmente, por uma area de influencia espacial.", body),
        p("1. Variavel-alvo e amostra", styles["HeadingCustom"]),
        p("A especificacao deve ser estimada separadamente - ou ao menos permitir heterogeneidade - entre creches municipais, conveniadas e privadas. A escolha das familias, a regra de acesso e a restricao de capacidade diferem substancialmente entre esses grupos.", body),
    ]

    target_data = [
        [p("Medida", styles["TableHeader"]), p("Interpretacao", styles["TableHeader"]), p("Uso", styles["TableHeader"])],
        [p("Matriculas_it", styles["Small"]), p("Numero de criancas matriculadas na creche i no ano t.", styles["Small"]), p("Alvo principal para previsao.", styles["Small"])],
        [p("Ocupacao_it", styles["Small"]), p("Matriculas_it / Capacidade_it, quando capacidade for observada.", styles["Small"]), p("Distingue crescimento de demanda de expansao de vagas.", styles["Small"])],
        [p("ListaEspera_it", styles["Small"]), p("Inscricoes nao atendidas, se obtida junto a rede municipal.", styles["Small"]), p("Proxy mais direta de demanda latente.", styles["Small"])],
    ]
    target_table = Table(target_data, colWidths=[3.0 * cm, 8.0 * cm, 4.0 * cm], repeatRows=1)
    target_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163B65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [target_table, Spacer(1, 5)]

    story += [
        p("2. Especificacao inicial", styles["HeadingCustom"]),
        p("A primeira especificacao combina efeito fixo de creche, efeito fixo de ano, coorte demografica local, concorrencia e capacidade. O efeito fixo de creche absorve fatores permanentes, como localizacao, qualidade estrutural e perfil historico da unidade. O efeito fixo de ano absorve choques comuns ao Rio de Janeiro, incluindo a pandemia e mudancas gerais de politica publica.", body),
        p("Matriculas_it = alpha_i + lambda_t + beta CoorteLocal_it + gamma Concorrencia_it + eta Capacidade_it + delta X_it + epsilon_it", styles["Equation"]),
        p("Em uma extensao dinamica, inclui-se a defasagem da matricula:", body),
        p("Matriculas_it = alpha_i + lambda_t + rho Matriculas_i,t-1 + beta CoorteLocal_it + gamma Concorrencia_it + eta Capacidade_it + delta X_it + epsilon_it", styles["Equation"]),
        p("A versao dinamica pode melhorar a previsao, mas requer cautela para inferencia causal com poucos periodos por creche, pois efeitos fixos com variavel dependente defasada podem gerar vies de painel dinamico. A qualidade preditiva deve ser avaliada por validacao temporal fora da amostra.", body),
        PageBreak(),
        p("3. Blocos de variaveis", styles["HeadingCustom"]),
    ]

    variable_data = [
        [p("Bloco", styles["TableHeader"]), p("Variaveis prioritarias", styles["TableHeader"]), p("Fonte / construcao", styles["TableHeader"])],
        [p("Demografia", styles["Small"]), p("Nascimentos defasados; coortes de idade elegivel; entrada e saida da faixa etaria.", styles["Small"]), p("SINASC e Data.Rio; somas por bairro, RA ou area de influencia.", styles["Small"])],
        [p("Oferta propria", styles["Small"]), p("Matriculas, etapa, dependencia administrativa, capacidade e ocupacao.", styles["Small"]), p("Censo Escolar / INEP; registros administrativos para capacidade e espera.", styles["Small"])],
        [p("Concorrencia", styles["Small"]), p("Numero de unidades proximas, matriculas/capacidade concorrente e entradas de novas creches.", styles["Small"]), p("Censo Escolar; geocodificacao de estabelecimentos.", styles["Small"])],
        [p("Territorio", styles["Small"]), p("Novas unidades habitacionais, emprego e renda local; cobertura de creche.", styles["Small"]), p("IPP/Data.Rio, RAIS e indicadores construidos.", styles["Small"])],
    ]
    variable_table = Table(variable_data, colWidths=[2.8 * cm, 7.7 * cm, 4.5 * cm], repeatRows=1)
    variable_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163B65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [variable_table]

    story += [
        p("4. Coorte elegivel e area de influencia", styles["HeadingCustom"]),
        p("Em vez de associar mecanicamente cada creche ao bairro onde esta localizada, a recomendacao e construir medidas espaciais. Uma creche proxima a uma fronteira administrativa pode atrair familias de varios bairros. A area de influencia pode ser definida por raio, tempo de deslocamento ou pesos que diminuem com a distancia.", body),
        p("CoorteLocal_it = sum_r w_ir [Nasc_r,t + Nasc_r,t-1 + Nasc_r,t-2 + Nasc_r,t-3]", styles["Equation"]),
        p("Os pesos w_ir podem ser inicialmente binarios (por exemplo, raio de 1 km) e depois comparados a alternativas com decaimento por distancia. A mesma logica vale para a pressao competitiva:", body),
        p("Concorrencia_it = sum_(j != i) w(d_ij) Capacidade_jt", styles["Equation"]),
        p("A oferta concorrente deve ser desagregada, sempre que possivel, entre rede publica, conveniada e privada. A abertura de uma nova creche pode responder a uma demanda local em crescimento; por isso, sua interpretacao causal exige cautela, embora ela continue util para previsao se for observavel antes do periodo a prever.", body),
        p("5. Estrategia de previsao e validacao", styles["HeadingCustom"]),
        p("A avaliacao deve reproduzir a decisao real de previsao. Para prever o ano t, usar apenas informacao disponivel ate t-1 ou variaveis cujo valor de t possa ser previamente projetado. Uma janela expansiva e adequada: estimar ate 2018 e prever 2019; estimar ate 2019 e prever 2020; e assim sucessivamente.", body),
    ]

    validation_data = [
        [p("Etapa", styles["TableHeader"]), p("Decisao", styles["TableHeader"])],
        [p("Baselines", styles["Small"]), p("Comparar com matricula do ano anterior, media movel e tendencia por creche.", styles["Small"])],
        [p("Modelos", styles["Small"]), p("Comparar efeitos fixos, efeitos fixos dinamicos e modelos de previsao regularizados como benchmark.", styles["Small"])],
        [p("Metricas", styles["Small"]), p("Reportar MAE e RMSE; avaliar tambem erro por dependencia administrativa e por tamanho da creche.", styles["Small"])],
        [p("Vazamento", styles["Small"]), p("Excluir covariadas de t que somente se tornam conhecidas apos o fechamento do ano escolar.", styles["Small"])],
    ]
    validation_table = Table(validation_data, colWidths=[3.1 * cm, 11.9 * cm], repeatRows=1)
    validation_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163B65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [validation_table]

    implementation_section = KeepTogether([
        p("6. Sequencia recomendada de implementacao", styles["HeadingCustom"]),
        p("(1) Harmonizar o painel Censo Escolar - creche x ano. (2) Definir o desfecho e criar medidas de capacidade/ocupacao. (3) Construir nascimentos e coortes defasadas por area. (4) Geocodificar unidades e criar concorrencia espacial. (5) Estimar modelos basicos e validar fora da amostra. (6) Adicionar habitacao, mercado de trabalho e outros controles apenas quando sua cobertura temporal e territorial estiver comprovada.", body),
        Spacer(1, 4),
        p("<b>Nucleo empirico proposto:</b> Censo Escolar + nascimentos espacialmente ponderados + concorrencia local + capacidade. Esse nucleo permite um modelo util mesmo antes da incorporacao de covariadas mais dificeis de obter.", body),
    ])
    story += [implementation_section]

    story += [p("7. Decisoes a fechar na etapa de dados", styles["HeadingCustom"])]
    decisions_data = [
        [p("Decisao", styles["TableHeader"]), p("Opcao inicial recomendada", styles["TableHeader"]), p("Implicacao", styles["TableHeader"])],
        [p("Mercado relevante", styles["Small"]), p("Raio de 1 km e, como robustez, decaimento por distancia.", styles["Small"]), p("Define os pesos da coorte e da concorrencia.", styles["Small"])],
        [p("Faixa etaria", styles["Small"]), p("Modelos por etapa/faixa, alem do agregado da creche.", styles["Small"]), p("Alinha nascimentos defasados a idade atendida.", styles["Small"])],
        [p("Capacidade", styles["Small"]), p("Usar medida administrativa quando disponivel; senao, tratar como limitacao observacional.", styles["Small"]), p("Evita confundir demanda com vagas ofertadas.", styles["Small"])],
        [p("Dependencia", styles["Small"]), p("Estimar por rede ou permitir interacoes com a dependencia administrativa.", styles["Small"]), p("Reconhece regras de acesso e formacao de preco distintas.", styles["Small"])],
    ]
    decisions_table = Table(decisions_data, colWidths=[3.2 * cm, 7.6 * cm, 4.2 * cm], repeatRows=1)
    decisions_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163B65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [decisions_table]

    story += [
        p("8. Interpretacao e riscos", styles["HeadingCustom"]),
        p("O objetivo primario deste esboco e previsao, e nao identificacao causal. Nesse contexto, uma variavel pode ser mantida se melhora de forma estavel a previsao fora da amostra e estiver disponivel antes do periodo previsto. Ainda assim, tres riscos merecem monitoramento:", body),
        p("<b>Endogeneidade da oferta.</b> Novas creches e expansoes de capacidade podem surgir precisamente onde a demanda ja cresce. Isso limita uma leitura causal do efeito da concorrencia.", body),
        p("<b>Restricao de capacidade.</b> Estabilidade nas matriculas pode refletir lotacao, nao estabilidade da procura. Medidas de ocupacao e lista de espera sao particularmente valiosas.", body),
        p("<b>Vazamento temporal.</b> Bases consolidadas no fim do ano nao devem ser usadas para prever o proprio ano. A construcao da base deve registrar a data em que cada variavel estaria efetivamente disponivel.", body),
    ]

    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
