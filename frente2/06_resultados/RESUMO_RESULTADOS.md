# Resultados da Frente 2

## Amostra e universo de escolha

- 343.308 episódios de escolha;
- 2.442 mercados `ano × origem × grupamento`;
- 8.422 células de alternativas ativas;
- 1.372.171 linhas mercado–alternativa;
- 95,6% das origens com geografia observada;
- 98,5% das alternativas com coordenadas oficiais;
- 350 creches parceiras, das quais 93,5% com coordenadas oficiais recuperadas.

## Resultado preditivo

Em 2024 há uma quebra de cobertura: as creches parceiras aparecem pela primeira vez na extração. Por isso, o teste economicamente comparável separa incumbentes de parceiras em cold start.

- OOS-2024, incumbentes: participação histórica tem menor log loss, 2,857, contra 3,066 do modelo completo.
- OOS-2024, parceiras novas: o modelo completo tem menor log loss, 3,169, contra 5,694 da participação histórica.
- OOS-2025, amostra completa: participação histórica tem menor log loss, 3,697; o modelo completo tem menor WAPE, 0,564, contra 0,652 da participação histórica.

Conclusão: não existe um vencedor único. Para unidades com histórico, o histórico é forte. Para unidades novas, atributos, distância e concorrência resolvem o cold start. Para planejamento agregado em 2025, o modelo completo distribui melhor o volume entre unidades.

## Incerteza

`model_coefficients.csv` contém, por modelo e fold, a estimativa padronizada, a estimativa na escala original e a média e a escala usadas na padronização. Não há erro-padrão, intervalo de confiança nem razão de chances: quantificar a incerteza dos coeficientes é entrega pendente. As estimativas são associativas e `causal_interpretation` é `False` em todas as linhas.