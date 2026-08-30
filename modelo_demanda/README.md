# Modelo de demanda por creche

O modelo prevê quantas crianças devem procurar a rede e como essa demanda se distribui entre creches e turnos.

A projeção tem duas equações conectadas:

1. crianças previstas por `ano × bairro de origem × grupamento`;
2. participação prevista de cada alternativa `creche × turno`.

O produto dessas duas previsões gera a demanda de primeira opção por creche e turno. A regra legal de alocação vem depois e não é alterada pelo modelo.

## Executar a projeção de 2026

```powershell
python modelo_demanda/05_projecao_2026/prever_demanda_2026.py
```

O script usa o envelope territorial de 2026, treina o modelo de escolha em 2021–2025 e conserva exatamente o total previsto ao distribuí-lo entre as alternativas ativas em 2025.

## Cenários

- principal: PPML-FE territorial distribuído pelo logit completo;
- volume agregado: persistência territorial distribuída pelo mesmo logit;
- distribuição: PPML-FE distribuído pelas participações históricas;
- emprego formal feminino: sensibilidade OOS de 2025, sem extrapolação automática para 2026.

## Resultados

- `06_resultados/previsao_integrada_unidade_2026.csv`;
- `06_resultados/previsao_integrada_grupamento_2026.csv`;
- `06_resultados/coeficientes_modelo_integrado_2026.csv`;
- `06_resultados/manifesto_integracao_2026.json`;
- detalhe por bairro, grupamento, creche e turno em `06_resultados/arquivos_gerados/`.

## Validação

```powershell
python -m unittest discover -s modelo_demanda/testes -v
```

A avaliação temporal compara participação histórica, unidade mais próxima e logits condicionais. Os coeficientes possuem erro-padrão robusto agrupado por mercado e IC95; não têm interpretação causal.

## Painel

```powershell
cd modelo_demanda/07_painel
npm install
npm run dev
```

## Organização

- `01_problema_e_estimando/`: estimando e contrato econômico;
- `02_universo_de_escolha/`: mercados, alternativas e geografia;
- `03_preferencias_e_concorrencia/`: distância, atributos e co-seleção;
- `04_validacao_in_sample_oos/`: testes temporais e benchmarks;
- `05_projecao_2026/`: integração e comando final;
- `06_resultados/`: tabelas e manifesto;
- `07_painel/`: visualização;
- `rotinas/` e `testes/`: funções e invariantes.