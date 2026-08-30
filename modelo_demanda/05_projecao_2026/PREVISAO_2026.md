# Previsão integrada de demanda para 2026

A modelo de demanda potencial fornece o envelope de crianças previstas por `bairro × grupamento`. A modelo de escolha estima a participação de cada alternativa `creche × turno`. O produto dos dois objetos gera demanda prevista de primeira opção por alternativa.

## Entradas

- `Pedro/Modelo/insumos_modelo_demanda/contexto_bairro_grupo_2026.csv`: envelope territorial;
- `Pedro/Modelo/insumos_modelo_demanda/demanda_bruta_2025.csv`: interesse bruto histórico por unidade;
- `Pedro/Modelo/insumos_modelo_demanda/pares_crianca_creche_2025.csv`: referência de co-seleção;
- Query A de 2021–2025: preferências, primeira opção e rede histórica;
- cadastro geográfico das unidades.

## Cenários

- principal: envelope PPML-FE da modelo de demanda potencial distribuído pelo logit completo da modelo de escolha;
- demanda agregada: persistência da modelo de demanda potencial distribuída pelo mesmo logit;
- distribuição: envelope PPML distribuído por participações históricas;
- CAGED feminino: permanece sensibilidade OOS de 2025 e não é extrapolado para 2026.

## Execução

```powershell
python modelo_demanda/05_projecao_2026/prever_demanda_2026.py
```

## Saídas

- `modelo_demanda/06_resultados/previsao_integrada_unidade_2026.csv`: previsão principal por creche e cenários;
- `modelo_demanda/06_resultados/previsao_integrada_grupamento_2026.csv`: conservação do envelope por grupamento;
- `modelo_demanda/06_resultados/coeficientes_modelo_integrado_2026.csv`: estimativas e IC95;
- `modelo_demanda/06_resultados/manifesto_integracao_2026.json`: estimando, insumos e checks;
- `modelo_demanda/06_resultados/arquivos_gerados/`: detalhe por território, grupamento, creche e turno.

A projeção é de demanda de primeira opção. `interesse_bruto_2025` conta todas as creches selecionadas pela criança e entra apenas como contexto histórico. Matrículas e fila não são tratadas como capacidade.