# Pipeline de previs\u00e3o de demanda por creche

Este diret\u00f3rio cont\u00e9m a sequ\u00eancia reproduz\u00edvel do modelo. Os nomes antigos usados para dividir o trabalho n\u00e3o fazem parte do produto final.

## Ordem de execu\u00e7\u00e3o

A partir da raiz do reposit\u00f3rio:

```powershell
python pipeline_demanda\02_estimacao\estimar_demanda.py
python pipeline_demanda\03_validacao\validar_historico.py
python pipeline_demanda\05_visualizacoes\gerar_mapa.py
```

O primeiro comando estima o PPML e produz o painel tratado, a valida\u00e7\u00e3o OOS e a previs\u00e3o territorial de 2026. O segundo organiza os backtests hist\u00f3ricos e mant\u00e9m os intervalos preditivos de 95%. O terceiro atualiza o mapa por creche.

## Estrutura

### `01_dados/`

Dados tratados usados pelo modelo.

- `painel_modelo.csv`: uma linha por ano, territ\u00f3rio e grupamento.
- `base_modelo/`: tabelas derivadas e contexto por creche.
- `fontes_externas/`: covariadas externas mantidas separadas.

As bases brutas permanecem nas pastas originais da raiz e nunca s\u00e3o sobrescritas.

### `02_estimacao/`

Cont\u00e9m `estimar_demanda.py`. O alvo \u00e9 o n\u00famero de crian\u00e7as inscritas, contando cada crian\u00e7a uma vez. O modelo \u00e9 um PPML com efeitos fixos territoriais e por faixa et\u00e1ria, tend\u00eancia por faixa e exposi\u00e7\u00e3o da coorte eleg\u00edvel.

### `03_validacao/`

Backtests temporais e auditoria.

- 2023 e 2025 s\u00e3o compara\u00e7\u00f5es OOS usuais.
- 2024 deve ser apresentado separando unidades incumbentes e parceiras em cold start; o agregado \u00e9 apenas diagn\u00f3stico de mudan\u00e7a de cobertura.
- `resultados/previsao_historica_2021_2026.csv` cont\u00e9m observado, previsto e intervalo preditivo de 95%.
- `resultados/performance_historica_2023_2025.csv` cont\u00e9m WAPE, vi\u00e9s e cobertura.

### `04_previsoes/`

Sa\u00eddas usadas pelo planejamento.

- `previsao_2026_resumo.csv`: total e grupamentos, com intervalos de 80% e 95%.
- `previsao_2026_territorio_grupamento.csv`: previs\u00e3o detalhada com intervalos.
- `previsao_2026_unidade.csv`: demanda efetiva alocada entre creches.

Intervalos por unidade permanecem ausentes quando n\u00e3o existem draws conjuntos v\u00e1lidos. Quantis de grupamentos n\u00e3o s\u00e3o somados mecanicamente.

### `05_visualizacoes/`

Produtos para decis\u00e3o.

- `gerar_mapa.py`: gera o mapa de creches.
- `output/mapa_creches_2025.html`: mapa com demanda observada em 2025 e prevista para 2026.
- `output/performance_modelo_demanda.html`: performance hist\u00f3rica e previs\u00e3o de 2026.

### `90_arquivo/`

Experimentos, relat\u00f3rios intermedi\u00e1rios, QA e rotinas anteriores. N\u00e3o faz parte da ordem de execu\u00e7\u00e3o.

## Resultado de refer\u00eancia

A previs\u00e3o PPML para 2026 \u00e9 66.800,9 crian\u00e7as, com intervalo preditivo condicional de 95% entre 64.159,0 e 69.442,8. A persist\u00eancia produz 59.717,6 e deve permanecer como benchmark.
