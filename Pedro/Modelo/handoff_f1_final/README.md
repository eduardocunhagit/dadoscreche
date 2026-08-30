# Handoff definitivo da Frente 1

Este diretório contém o resultado utilizável da Frente 1 e os insumos necessários para iniciar a Frente 2. Nenhuma estimação ou transformação da Frente 2 foi executada.

## Recomendação objetiva

Para uma análise da pressão de demanda observada em 2025, use `demanda_bruta_2025.csv` como tabela principal. A variável `demanda_observada` conta uma criança uma vez em cada creche que ela selecionou, independentemente da posição da opção ou da situação posterior da inscrição.

Se for conveniente trabalhar com uma única tabela creche–ano, use `demanda_bruta_cag_fem_2021_2025.csv`. Ela preserva `demanda_observada` como variável dependente e acrescenta as colunas do CAGED feminino pré-corte. O indicador CAGED é municipal: dentro de um mesmo ano, seu valor se repete para todas as creches. Portanto, ele ajuda a ajustar a escala temporal da demanda, mas não explica diferenças de demanda entre creches no mesmo ano.

Para construir concorrência ou co-seleção entre creches, use `pares_crianca_creche_2025.csv`. Cada linha representa um par distinto criança–creche. Creches escolhidas pela mesma `aluno_anon` podem ser conectadas para construir uma rede de concorrência. Esse arquivo não é, sozinho, um conjunto de escolha causal: inscrições repetidas da mesma criança foram consolidadas no ano.

Para comparar previsões, use `validacao_oos_2025.csv`:

- `prev_ppml_base_2025`: cenário principal do PPML-FE da Frente 1;
- `prev_persistencia_2025`: benchmark obrigatório;
- `prev_ppml_cag_fem_2025`: cenário concorrente com CAGED feminino;
- `demanda_bruta_observada_2025`: realizado usado apenas para avaliar o OOS;
- colunas terminadas em `DIAGNOSTICO`: não usar na Frente 2, pois foram reescaladas pelo total observado de 2025 e contêm informação realizada.

## O que os resultados permitem afirmar

No OOS de 2025, em 834 creches continuantes:

| Modelo | WAPE | Viés agregado | Total previsto |
|---|---:|---:|---:|
| PPML-FE base | 19,86% | +3,06% | 158.810 |
| Persistência | 20,15% | +14,63% | 176.639 |
| PPML-FE + CAGED feminino pré-corte | 18,79% | -5,02% | 146.358 |

O PPML-FE base supera a persistência em apenas 0,29 ponto percentual de WAPE. Portanto, a evidência de superioridade é fraca e os dois devem permanecer como cenários.

O CAGED feminino melhora o WAPE principal, mas é instável: sem tendência o WAPE sobe para 47,91%; excluindo 2021, sobe para 23,39%. O motivo é que há somente quatro valores anuais independentes no treino e a variável CAGED é municipal, comum a todas as creches. Use o CAGED feminino como análise de sensibilidade, não como substituição automática do modelo base.

## Limitação urgente sobre 2026

Ainda não existe neste projeto uma previsão validada de 2026 por creche. `contexto_bairro_grupo_2026.csv` contém previsão por bairro × grupamento etário e pode servir como envelope territorial ou restrição agregada. Ela não deve ser tratada como demanda de uma creche individual nem distribuída entre unidades sem a modelagem da Frente 2.

Consequentemente:

- para uma Frente 2 retrospectiva ou de calibração de 2025, use a demanda bruta observada e os pares criança–creche;
- para uma simulação OOS de 2025, use os três cenários de `validacao_oos_2025.csv`;
- para planejamento de 2026 por unidade, a Frente 2 precisa realizar a alocação territorial/concorrencial; não há um número pronto e validado por creche.

## Coeficientes

- `coef_base_comuns.csv`: intercepto, tendência, ridge e exposição do PPML-FE base;
- `coef_base_unidades.csv`: efeitos regularizados das 834 creches continuantes;
- `coef_cag_fem.csv`: coeficientes comuns do cenário CAGED feminino e robustez;
- `coef_cag_fem_unidades.csv`: efeitos das unidades no cenário CAGED principal;
- `cag_fem_feat.csv`: construção e padronização temporal da covariável.

O PPML-FE base pode ser reproduzido por:

`demanda_i = exposição × exp(intercepto + efeito_unidade_i + coef_tendencia × tendencia)`

No OOS de 2025, `tendencia = 4` e a exposição prevista é 65.114,2646 crianças únicas.

## Arquivos

- `demanda_bruta_2021_2025.csv`: histórico agregado por ano e creche;
- `demanda_bruta_cag_fem_2021_2025.csv`: mesmo painel com o CAGED feminino pré-corte já mesclado;
- `demanda_bruta_2025.csv`: resultado bruto principal, incluindo 836 creches;
- `pares_crianca_creche_2025.csv`: 155.312 pares distintos para co-seleção;
- `validacao_oos_2025.csv`: previsões comparáveis em 834 creches continuantes;
- `metricas_oos_2025.csv`: métricas e testes de robustez;
- `contexto_creches_2025.csv`: coordenadas, matrículas e fila para junção por `codigo_unidade`;
- `contexto_bairro_grupo_2026.csv`: previsão agregada territorial, não previsão por creche;
- `resumo_bairro_grupo_2026.csv`: totais da previsão territorial;
- `manifesto.json`: cobertura, definições e hashes;
- `../make_handoff_f1_final.py`: geração reprodutível do pacote.

## Chave de integração

Use `codigo_unidade` para juntar demanda, previsões, coeficientes e contexto das creches. Preserve o código como texto. Das 836 unidades observadas, 820 encontram correspondência no arquivo de contexto; as 16 restantes não devem receber coordenadas imputadas silenciosamente. Apenas 834 unidades são continuantes elegíveis para a comparação OOS.
