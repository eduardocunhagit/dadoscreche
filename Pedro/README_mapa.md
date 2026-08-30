# Mapa de creches — 2025

O pipeline `mapa_creches.py` combina as bases mais recentes disponíveis no repositório e gera um painel por unidade, um diagnóstico de unidades sem coordenadas e um mapa interativo.

## Fontes

- Coordenadas e cadastro: `OferecimentosEvagas/Unidades_Unificadas_com_Localizacao.xlsx`.
- Matrículas públicas: `OferecimentosEvagas/totaalunoscreche2025.xlsx`.
- Matrículas e metas das parceiras: `OferecimentosEvagas/Parceiras2025.xlsx`, aba `MAIO -2025`.
- Lista de espera: `Bases IC_ ClassificadoseFila/01_QueryA_InscricoesPorAno.csv.gz`, processo de 2025.
- Limites territoriais: `Microáreas_SME_revisãoIPP/Microareas_SME_revisao.shp`.

## Definições

- `fila_total`: número de crianças distintas com situação `Lista de espera` em cada unidade no processo de 2025.
- `fila_por_100_matriculas`: `100 × fila_total / matriculas_total`. É um indicador descritivo de pressão, não uma estimativa causal nem uma recomendação de expansão.
- Berçário das parceiras: soma de Berçário I e Berçário II, para manter comparabilidade com a planilha das unidades públicas.
- Uma unidade entra no painel se tiver matrícula positiva, registro como parceira em 2025 ou fila positiva.

As colunas `demanda_prevista`, `gap_demanda_oferta` e `prioridade_modelo` ficam vazias de propósito. Elas são pontos de integração para o modelo de previsão de demanda, evitando confundir fila observada com demanda futura prevista.

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
