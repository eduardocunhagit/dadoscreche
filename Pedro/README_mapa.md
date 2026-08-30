# Mapa de creches — 2025

O pipeline `mapa_creches.py` combina as bases mais recentes disponíveis no repositório e gera um painel por unidade, um diagnóstico de unidades sem coordenadas e um mapa interativo.

## Fontes

- Coordenadas e cadastro: `OferecimentosEvagas/Unidades_Unificadas_com_Localizacao.xlsx`.
- Matrículas públicas: `OferecimentosEvagas/totaalunoscreche2025.xlsx`.
- Matrículas e metas das parceiras: `OferecimentosEvagas/Parceiras2025.xlsx`, aba `MAIO -2025`.
- Demanda histórica e lista de espera: `Bases IC_ ClassificadoseFila/01_QueryA_InscricoesPorAno.csv.gz`, processo de 2025.
- Limites territoriais: `Microáreas_SME_revisãoIPP/Microareas_SME_revisao.shp`.

## Definições

- `demanda_historica`: número de crianças distintas que selecionaram a unidade em qualquer opção. A criança é contada uma única vez dentro de cada creche, mas pode aparecer em várias creches. Essa é a medida de pressão histórica usada como benchmark.
- `demanda_hist_por_100_matriculas`: `100 × demanda_historica / matriculas_total`. É uma razão descritiva; não representa probabilidade nem recomendação automática de expansão.
- `fila_total`: número de crianças distintas com situação `Lista de espera` em cada unidade no processo de 2025.
- `fila_por_100_matriculas`: `100 × fila_total / matriculas_total`. É um indicador descritivo de pressão, não uma estimativa causal nem uma recomendação de expansão.
- Berçário das parceiras: soma de Berçário I e Berçário II, para manter comparabilidade com a planilha das unidades públicas.
- Uma unidade entra no painel se tiver matrícula positiva, registro como parceira em 2025, demanda histórica positiva ou fila positiva.

O controle no canto superior esquerdo possui quatro modos:

1. **Demanda histórica:** benchmark observado de pares criança–creche.
2. **Inscritos previstos — Frente 1:** quantidade prevista de crianças que entram no processo.
3. **Demanda efetiva — Frente 2:** quantidade prevista de crianças que selecionarão cada unidade em qualquer opção.
4. **Pressão efetiva prevista:** `demanda_prevista_efetiva - capacidade_ano_anterior`.

No modo de pressão, círculos maiores representam gaps absolutos maiores. Excesso de demanda é exibido em vermelho, com intensidade crescente; capacidade excedente é exibida em azul. O usuário pode marcar **Apenas gaps significativos (IC 95%)**.

O intervalo do gap é construído como:

`[demanda_efetiva_p025 - capacidade_ano_anterior; demanda_efetiva_p975 - capacidade_ano_anterior]`.

O gap é significativo a 95% quando esse intervalo não contém zero. A capacidade é tratada como conhecida no corte da previsão; a versão atual não incorpora incerteza própria da capacidade.

## Integração da previsão

O mapa procura opcionalmente o arquivo `Pedro/Modelo/results/f2_prev_unidade.csv`. Enquanto ele não existir, os três modos previstos permanecem desabilitados e os campos aparecem como `—`.

O arquivo futuro deve conter:

- `codigo_unidade`, `codigo` ou `unidade`;
- `demanda_prevista_inscritos`: saída reconciliada com a Frente 1;
- `demanda_prevista_efetiva`: média preditiva da Frente 2;
- `demanda_efetiva_p025` e `demanda_efetiva_p975`: limites do IC preditivo de 95% da Frente 2;
- `capacidade_ano_anterior`: capacidade conhecida antes do ano previsto;
- opcionalmente `ano_previsao`, `ano` ou `ano_teste`.

Os aliases `prev_f1`/`f1_prev`/`a_hat`, `prev_f2`/`d_hat`/`prev_modelo`, `f2_p025`/`limite_95_inf`, `f2_p975`/`limite_95_sup` e `capacidade_t_1` também são aceitos.

Quando houver intervalo de confiança, o arquivo deve ter uma única linha por unidade. Quantis por faixa etária não podem ser somados mecanicamente; a agregação deve vir da distribuição preditiva conjunta. Se houver vários anos, o pipeline mantém o mais recente.

A Frente 1 atualmente tem grão territorial, não grão de creche. Portanto, o campo `demanda_prevista_inscritos` só deve ser habilitado nos pontos após uma regra explícita de reconciliação/alocação. Alternativamente, a saída territorial bruta da Frente 1 deve ser exibida em polígonos, sem fingir que ela pertence diretamente a uma unidade.

Depois de salvar o arquivo, basta executar novamente `python Pedro\mapa_creches.py` para habilitar os modos disponíveis.

## Execução

```powershell
cd C:\Users\pedro\Documents\2026\ClaudeImpactLab2
python Pedro\mapa_creches.py
```

O script não altera nenhuma base original. Ele atualiza apenas os arquivos derivados em `Pedro/output`.

## Saídas

- `Pedro/output/mapa_creches_2025.html`: mapa interativo.
- `Pedro/output/creches_2025.csv`: painel das unidades mapeadas.
- `Pedro/output/creches_sem_coord_2025.csv`: unidades que não puderam ser exibidas.
- `Pedro/output/resumo_mapa_2025.json`: cobertura e totais da execução.

## Limites de interpretação

Os dados do desafio são anonimizados e os indicadores não representam a realidade operacional da rede. Além disso, as fontes de matrículas têm referências diferentes: parceiras em maio de 2025 e públicas no consolidado de 2025. Antes de recomendar expansão ou redução, o mapa deve ser unido às previsões fora da amostra e a uma medida comparável de capacidade/vagas para as unidades públicas.
