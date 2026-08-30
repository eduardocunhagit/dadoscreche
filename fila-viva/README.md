# Fila Viva

Ferramenta de apoio à gestão de matrículas de creches e educação infantil.

A única fonte de previsão de demanda é `pipeline_demanda/`. O `fila-viva/` consome seus resultados; ele não mantém um modelo paralelo.

## Ordem correta de execução

Na raiz do repositório, gere e valide a pressão de demanda efetiva:

```powershell
python pipeline_demanda/05_integracao_com_frente1/prever_demanda_2026.py
python pipeline_demanda/calcular_gap_capacidade.py --demanda pipeline_demanda/06_resultados/previsao_integrada_unidade_2026.csv --coluna-demanda demanda_2026_ppml --ano-demanda 2026 --nivel unidade --saida-proxy pipeline_demanda/06_resultados/arquivos_gerados/capacidade_proxy_matriculas.csv --saida-gap pipeline_demanda/06_resultados/arquivos_gerados/gap_demanda_efetiva_2026.csv
python -m unittest discover -s pipeline_demanda/testes -v
```

Depois prepare o site:

```powershell
cd fila-viva
npm install
npm run setup
npm run db:geo
npm run db:demanda
npm run dev
```

Abra http://localhost:3000/login.

A sequência importa primeiro unidades e contas de demonstração, depois geografia e, por último, o gap efetivo de 2026. `db:demanda` deve vir depois de `db:geo`, pois a previsão efetiva substitui a classificação histórica quando as duas existem.

## Funcionalidades integradas

- mapa do gestor com pressão histórica, inscrições previstas e pressão efetiva prevista;
- nova inscrição do responsável, com busca e escolha de creches;
- fila, alocação e revalidação de contatos;
- mensagens de demonstração para a equipe gestora.

## Contas de demonstração

Senha `demo1234` para todas.

| E-mail | Papel | Escopo |
| --- | --- | --- |
| `gestor@filaviva.rio` | Gestor SME | Rede inteira |
| `cre1@filaviva.rio` | Servidor da CRE | Polo 1 (CRE 1) |
| `unidade@filaviva.rio` | Servidor da unidade | Uma unidade específica |
| `responsavel@filaviva.rio` | Responsável | As próprias crianças |

## Desenvolvimento

Antes de acrescentar funcionalidade, leia `EXTENDING.md`. Para validar uma mudança:

```powershell
npx tsc --noEmit
npm test
npm run lint
npm run build -- --webpack
```

O argumento `--webpack` é necessário apenas em ambientes Windows cuja política bloqueia o binário nativo do Turbopack.