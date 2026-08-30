# Previsão integrada de demanda para 2026

A modelo de demanda potencial fornece o envelope de crianças previstas por `bairro × grupamento`. A modelo de escolha estima a participação de cada alternativa `creche × turno`. O produto dos dois objetos gera demanda prevista de primeira opção por alternativa.

## Entradas

- `pipeline_demanda/05_integracao_com_frente1/insumos_2026/contexto_bairro_grupo_2026.csv`: envelope territorial;
- `pipeline_demanda/05_integracao_com_frente1/insumos_2026/demanda_bruta_2025.csv`: interesse bruto histórico por unidade;
- Query A de 2021–2025: preferências, primeira opção e rede histórica;
- cadastro geográfico das unidades.

## Cenários

- principal: envelope PPML-FE da modelo de demanda potencial distribuído pelo logit completo da modelo de escolha;
- demanda agregada: persistência da modelo de demanda potencial distribuída pelo mesmo logit;
- distribuição: envelope PPML distribuído por participações históricas;
- CAGED feminino: permanece sensibilidade OOS de 2025 e não é extrapolado para 2026.

## Execução

```powershell
python pipeline_demanda/05_integracao_com_frente1/prever_demanda_2026.py
```

## Saídas

- `pipeline_demanda/06_resultados/previsao_integrada_unidade_2026.csv`: previsão principal por creche e cenários;
- `pipeline_demanda/06_resultados/previsao_integrada_grupamento_2026.csv`: conservação do envelope por grupamento;
- `pipeline_demanda/06_resultados/coeficientes_modelo_integrado_2026.csv`: estimativas e IC95;
- `pipeline_demanda/06_resultados/manifesto_integracao_2026.json`: estimando, insumos e checks;
- `pipeline_demanda/06_resultados/arquivos_gerados/`: detalhe por território, grupamento, creche e turno.

A projeção é de demanda de primeira opção. `interesse_bruto_2025` conta todas as creches selecionadas pela criança e entra apenas como contexto histórico. Matrículas e fila não são tratadas como capacidade.