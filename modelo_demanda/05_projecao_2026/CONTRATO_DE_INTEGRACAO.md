# Contrato da projeção

## Total por território

Uma linha por `ano × origin_area × grupamento_norm`, com:

- `inscricoes_previstas`: total de crianças previsto;
- `p025` e `p975`: limites preditivos opcionais;
- `draw_id`: sorteio opcional para propagação de incerteza.

## Participação por alternativa

Uma linha por `ano × origin_area × grupamento_norm × alternativa_id`, com:

- `unidade`;
- `horario_norm`;
- `choice_share`.

As participações devem somar um dentro de cada célula territorial. A demanda prevista é `inscricoes_previstas × choice_share`, de modo que o total territorial seja conservado.

## Execução genérica

```powershell
python modelo_demanda/combinar_previsoes.py --totais demanda_potencial.csv --participacoes participacoes_escolha.csv --saida demanda_integrada.csv
```

A projeção oficial de 2026 é executada diretamente por `prever_demanda_2026.py`.