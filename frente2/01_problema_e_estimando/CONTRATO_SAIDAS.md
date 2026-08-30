# Contrato de saídas da Frente 2

Este contrato separa produtos de modelagem, integração e visualização. Nenhum arquivo publicado contém identificadores de criança, responsável ou inscrição.

## 1. Convenções comuns

| Campo | Definição |
| --- | --- |
| `run_id` | Identificador imutável da execução. |
| `model_id` | Identificador da especificação estimada. |
| `fold_id` | Identificador do fold, como `insample`, `oos_2024` ou `oos_2025`. |
| `train_years` | Lista dos anos usados na estimação. |
| `target_year` | Ano previsto. |
| `data_snapshot` | Identificador ou hash do snapshot dos insumos. |
| `created_at_utc` | Data e hora de criação do artefato, em UTC. |
| `origin_area` | Código territorial agregado da origem. |
| `group` | Grupamento etário. |
| `unit_id` | Código canônico da unidade. |
| `shift` | Turno da alternativa. |
| `alternative_id` | Chave estável formada por `unit_id + shift`. |
| `is_new_unit` | Indicador de unidade ausente nos anos de treino. |
| `model_role` | Papel da especificação: `benchmark`, `candidate` ou `selected`. |

Arquivos tabulares de pipeline devem usar Parquet. CSV pode ser exportado apenas para métricas pequenas e inspeção. Resultados servidos ao frontend podem ser serializados em JSON pela camada de aplicação, sem criar uma segunda fonte de verdade.

## 2. `choice_shares.parquet`

**Grão:** `run_id × model_id × fold_id × target_year × origin_area × group × alternative_id`.

| Campo | Tipo | Regra |
| --- | --- | --- |
| campos comuns | — | Obrigatórios. |
| `choice_share` | número entre 0 e 1 | Participação prevista da alternativa na célula territorial. |
| `choice_set_size` | inteiro positivo | Número de alternativas elegíveis na célula. |
| `coverage_status` | texto categórico | `covered` ou `no_eligible_alternative`. |
| `geo_competition` | número ou nulo | Índice geográfico calculado com informação ex ante. |
| `colist_competition` | número ou nulo | Índice de co-listagem calculado somente no treino. |
| `hybrid_competition` | número ou nulo | Índice híbrido calculado somente com informação permitida. |
| `capacity_concept` | texto | Nome exato do conceito usado: capacidade, meta, alunos ou turmas defasados. |
| `capacity_value` | número ou nulo | Valor ex ante associado ao conceito declarado. |

**Invariantes:**

- `choice_share` soma 1 em cada `run_id × model_id × fold_id × target_year × origin_area × group` coberto;
- nenhuma alternativa inelegível aparece;
- unidade e turno não são agregados antes da saída;
- células sem cobertura não recebem escolha artificial.

## 3. `conditional_demand.parquet`

**Grão:** `run_id × model_id × fold_id × target_year × group × alternative_id`.

| Campo | Tipo | Regra |
| --- | --- | --- |
| campos comuns aplicáveis | — | Obrigatórios. |
| `observed_enrollment_episodes` | inteiro | Total observado de episódios usado para condicionar a avaliação. |
| `predicted_first_choices_conditional` | número não negativo | Soma das probabilidades individuais OOS. |
| `observed_first_choices` | inteiro não negativo | Contagem observada de primeiras opções. |
| `conditional_error` | número | Previsto menos observado. |
| `observed_list_pressure` | inteiro não negativo | Número de ocorrências em qualquer posição da lista; apenas descritivo. |
| `is_new_unit` | booleano | Calculado em relação aos anos de treino do fold. |

`observed_list_pressure` não é demanda de crianças únicas e não entra como alvo do modelo principal.

## 4. `model_metrics.csv`

**Grão:** `run_id × model_id × fold_id × target_year × sample_segment × metric`.

| Campo | Definição |
| --- | --- |
| `sample_segment` | `all`, `incumbent_units`, `new_units` ou outro subgrupo documentado. |
| `metric` | Nome da métrica, como `log_loss`, `top1_accuracy`, `mae`, `wape` ou `share_mae`. |
| `value` | Valor da métrica. |
| `n_choice_episodes` | Número de episódios avaliados. |
| `n_units` | Número de unidades avaliadas. |
| `benchmark_delta` | Diferença para o benchmark declarado, com orientação registrada. |
| `benchmark_model_id` | Modelo usado na comparação. |

Não preencher segmentos sem observações com zero. Use valor nulo e registre o motivo.

## 5. `model_coefficients.csv`

**Grão:** `run_id × model_id × term`.

| Campo | Definição |
| --- | --- |
| `term` | Nome estável do atributo ou interação. |
| `term_label` | Descrição legível. |
| `estimate` | Coeficiente estimado. |
| `std_error` | Erro-padrão. |
| `conf_low`, `conf_high` | Limites do intervalo declarado. |
| `unit_change` | Variação do atributo usada na explicação. |
| `odds_ratio` | Razão de chances para `unit_change`, quando aplicável. |
| `average_probability_change` | Mudança média estimada na probabilidade para `unit_change`. |
| `causal_interpretation` | Sempre `false` neste produto. |

Efeitos fixos de unidade, quando estimados, não devem dominar a visualização nem ser usados para explicar unidade nova.

## 6. `competition_edges.parquet`

**Grão:** `run_id × fold_id × target_year × group × alternative_id_a × alternative_id_b`.

| Campo | Definição |
| --- | --- |
| `distance_between_units` | Distância entre as unidades. |
| `colist_count_train` | Número agregado de episódios do treino que listaram o par. |
| `colist_weight_train` | Peso normalizado de co-listagem. |
| `geo_weight` | Peso de decaimento geográfico. |
| `hybrid_weight` | Produto dos pesos de co-listagem e geográfico. |

O arquivo contém somente relações agregadas entre unidades. A publicação no frontend pode aplicar limiar mínimo de suporte para evitar ruído e reduzir risco de exposição indireta.

## 7. `integrated_demand.parquet`

Este arquivo é produzido pela etapa de integração, não pela estimação isolada da Frente 2.

**Grão:** `run_id × model_id × target_year × group × alternative_id × draw_id`.

| Campo | Definição |
| --- | --- |
| `draw_id` | Identificador do sorteio de incerteza recebido da Frente 1 e, quando implementado, da Frente 2. |
| `predicted_entries` | Total territorial previsto pela Frente 1 antes da distribuição. |
| `choice_share` | Participação prevista pela Frente 2. |
| `predicted_demand` | Demanda integrada por alternativa. |
| `capacity_scenario` | Valor da capacidade no cenário, quando disponível. |
| `planning_gap` | Demanda prevista menos capacidade do cenário. |

**Invariante de integração:** a soma de `predicted_demand` sobre as alternativas deve ser igual ao total de `predicted_entries` das células cobertas, dentro da tolerância numérica documentada.

`planning_gap` orienta planejamento. Não determina qual criança recebe a vaga.

## 8. `run_manifest.json`

O manifesto registra:

- hashes ou versões dos insumos;
- comando de execução;
- versão do código;
- folds e anos;
- regras do conjunto de escolha;
- conceito e data de referência da oferta;
- transformações ajustadas em cada fold;
- modelos comparados e modelo selecionado;
- limitações e avisos de uso;
- resultado dos testes de invariantes.

Uma execução sem manifesto válido não pode ser publicada no dashboard.

## 9. Contrato mínimo com o dashboard

O frontend consome somente dados agregados e deve exibir:

1. demanda histórica de primeira opção;
2. demanda condicional prevista e erro OOS;
3. demanda integrada quando a Frente 1 estiver disponível;
4. participação histórica, distância e modelo selecionado lado a lado;
5. métricas in-sample e OOS claramente separadas;
6. segmentos de unidades incumbentes e novas;
7. decomposição explicável da previsão;
8. conceito de oferta usado e sua data de referência;
9. avisos de anonimização, reconstrução do conjunto de escolha e ausência de interpretação causal;
10. separação explícita entre previsão de demanda e alocação legal.

O dashboard não deve mostrar identificadores individuais, inferir aceitação de unidade não listada ou apresentar o modelo de preferência como regra de convocação.
