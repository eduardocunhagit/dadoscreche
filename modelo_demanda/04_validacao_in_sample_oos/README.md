# Validação in-sample e fora da amostra

## Folds

| Teste | Treino | Regra de leitura |
| --- | --- | --- |
| OOS-2024 | 2021–2023 | incumbentes selecionam o modelo; parceiras são cold start separado |
| OOS-2025 | 2021–2024 | amostra completa, porque as parceiras já têm histórico |

## Métricas

- `log_loss`: qualidade da probabilidade da escolha individual;
- `top1`: frequência da alternativa de maior probabilidade;
- `MAE`: erro médio da demanda por alternativa;
- `WAPE`: erro absoluto total relativo à demanda observada.

## Resultado atual

- 2024, amostra completa: distância vence; o completo piora porque mistura entrada das parceiras com escolha da unidade.
- 2024, incumbentes: participação histórica vence.
- 2024, parceiras condicionais ao cold start: modelo completo vence em log loss.
- 2025: histórico vence em log loss; modelo completo vence em WAPE.

Não se calcula uma média mecânica entre 2024 e 2025: são regimes diferentes.
