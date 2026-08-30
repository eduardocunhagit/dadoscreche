# Visualiza\u00e7\u00f5es

Execute a partir da raiz:

```powershell
python pipeline_demanda\05_visualizacoes\gerar_mapa.py
```

O mapa combina:

1. demanda hist\u00f3rica: pares distintos crian\u00e7a-creche em qualquer op\u00e7\u00e3o de 2025;
2. demanda efetiva prevista por creche em 2026;
3. capacidade do ano anterior e press\u00e3o, somente quando houver capacidade f\u00edsica validada;
4. intervalos de 95%, somente quando existirem intervalos conjuntos v\u00e1lidos por unidade.

Entrada de previs\u00e3o: `pipeline_demanda/04_previsoes/previsao_2026_unidade.csv`.

Sa\u00eddas:

- `output/mapa_creches_2025.html`;
- `output/creches_2025.csv`;
- `output/creches_sem_coord_2025.csv`;
- `output/resumo_mapa_2025.json`;
- `output/performance_modelo_demanda.html`.

O script n\u00e3o altera bases originais. Capacidade ausente n\u00e3o \u00e9 substitu\u00edda por matr\u00edcula, meta ou vagas.
