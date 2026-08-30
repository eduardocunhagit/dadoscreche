# Contrato de integração com a Frente 1

## Divisão de responsabilidades

- Frente 1 prevê o número de inscrições por `ano × território de origem × grupamento`.
- Frente 2 prevê a participação de cada `unidade × turno` dentro da mesma célula.
- A integração multiplica quantidade por participação.

## Arquivo entregue pela Frente 1

`previsao_frente1.csv` deve conter:

| Campo | Definição |
| --- | --- |
| `ano` | ano previsto |
| `origin_area` | território com a mesma codificação da Frente 2 |
| `grupamento_norm` | `BERCARIO`, `MATERNAL I` ou `MATERNAL II` |
| `inscricoes_previstas` | total não negativo previsto pela Frente 1 |
| `draw_id` | opcional; sorteio ou cenário de incerteza |

O grão é uma linha por célula e, quando existir, por `draw_id`.

## Arquivo entregue pela Frente 2

`participacoes_frente2.csv` deve conter:

| Campo | Definição |
| --- | --- |
| `ano`, `origin_area`, `grupamento_norm` | mesmas chaves da Frente 1 |
| `alternativa_id` | `unidade × turno` |
| `unidade` | código canônico |
| `horario_norm` | turno |
| `choice_share` | participação entre zero e um |

As participações devem somar um em cada célula.

## Saída integrada

```text
demanda_prevista = inscricoes_previstas × choice_share
```

A soma da demanda prevista sobre alternativas deve reproduzir o total da Frente 1. Capacidade e `planning_gap` entram depois dessa multiplicação.

## Comando

```powershell
python pipeline_demanda/integrar_frentes.py `
  --frente1 caminho/previsao_frente1.csv `
  --frente2 caminho/participacoes_frente2.csv `
  --saida caminho/demanda_integrada.csv
```
