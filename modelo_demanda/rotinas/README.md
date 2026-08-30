# Núcleo de modelos da modelo de escolha

Este módulo estima como a demanda manifesta se distribui entre unidades,
condicionalmente à inscrição. Ele não estima entrada na rede, capacidade,
prioridade legal ou alocação.

## Contrato tabular

Cada linha representa uma alternativa disponível em um episódio de escolha.
Antes de usar cada campo:

- `ano` é o ano do processo histórico;
- `choice_id` identifica um episódio de escolha, em geral uma inscrição no ano;
- `unit_id` identifica uma alternativa `unidade × horário` elegível;
- `chosen` vale um apenas para a primeira opção observada e zero nas demais;
- `distance_km` é a distância entre a origem agregada da família e a unidade;
- `grupamento` é a faixa etária atendida;
- `horario` identifica o regime integral ou parcial;
- atributos adicionais são características ex ante da alternativa, como
  capacidade administrativa conhecida, tipo de gestão e concorrência.

Cada `choice_id` deve ter uma única alternativa escolhida. Cada unidade deve
aparecer no máximo uma vez no conjunto. As probabilidades previstas somam um
dentro de cada episódio.

## Modelos

1. `HistoricalShareBenchmark` usa contagens históricas de primeiras escolhas,
   com suavização e fallback para a popularidade global da unidade.
2. `NearestUnitBenchmark` atribui a escolha à menor distância e divide empates.
3. `ConditionalLogit` estima uma utilidade linear e um softmax dentro de cada
   conjunto. `coefficient_table()` expõe coeficientes e escalas;
   `explain()` decompõe a utilidade de cada alternativa por atributo.

O logit é estimado diretamente por máxima verossimilhança, gradiente analítico
e busca de passo. Não há classificador opaco. Os coeficientes são associações
preditivas, não efeitos causais.

## Concorrência por co-listagem

`build_colisting_network()` calcula, usando apenas listas do treino,

```text
omega_ij = n_ij / sqrt(n_i * n_j),
```

em que `n_i` é o número de listas que contêm a unidade `i` e `n_ij` é o número
de listas que contêm simultaneamente `i` e `j`. `colisting_competition()` soma
`omega_ij × capacity_j` para cada unidade `i`, usando capacidade ex ante.

A rede deve ser reconstruída em cada fold. O argumento `fold_transform` de
`run_temporal_evaluation()` existe para ajustar e anexar atributos como esse
somente a partir do treino.

## Validação

Os folds fixos são:

- treino até 2023, teste em 2024;
- treino até 2024, teste em 2025.

Para cada modelo e fold, o avaliador produz previsões in-sample e OOS. Reporta
log loss, top-1 com crédito fracionário em empates, MAE e WAPE da demanda por
unidade. A tabela `unit_demand` compara a soma das probabilidades previstas com
a contagem histórica de primeiras escolhas. A participação histórica é um
benchmark; o modelo completo só é melhor se a comparação OOS mostrar isso.

## Limitações

- O conjunto de alternativas precisa ser construído externamente com unidade,
  grupamento, horário, atividade e elegibilidade. Usar somente as unidades que
  a família listou censura o conjunto de escolha.
- A primeira opção pode refletir preferência e expectativa estratégica de
  acesso. O MVP não identifica esses mecanismos separadamente.
- Fila observada é demanda manifesta sob oferta e fricções passadas, não
  demanda potencial.
- Matrícula não é capacidade. Atributos de capacidade exigem definição
  administrativa harmonizada e disponibilidade ex ante.
- A situação final da opção, dados de 2024 no primeiro fold e dados de 2025 no
  segundo nunca podem entrar como preditores.
- Os níveis históricos anonimizados e perturbados não representam a demanda
  corrente de 2026.

## Testes

Sem dependências além de NumPy e pandas:

```powershell
python -m unittest discover -s modelo_demanda/testes -v
```
