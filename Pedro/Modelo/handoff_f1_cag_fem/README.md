# Handoff da Frente 1 — CAGED feminino

Este diretório entrega o teste do emprego formal feminino do Novo CAGED na previsão da demanda bruta potencial por creche. A Frente 2 não foi executada nem alterada.

## Arquivo para consumir na Frente 2

Use `prev_creche_2025.csv` como tabela de entrada por unidade:

- `codigo_unidade`: chave da creche;
- `nome_unidade`: nome da creche;
- `prev_f1_cag_fem`: previsão da demanda bruta da Frente 1 com CAGED feminino;
- `prev_modelo`: previsão do PPML-FE base, sem CAGED;
- `prev_persistencia`: benchmark de persistência;
- `demanda_observada`: valor realizado de 2025, incluído apenas para validação fora da amostra.

A demanda bruta conta uma criança uma vez em cada creche selecionada. Portanto, uma mesma criança pode aparecer na demanda de várias unidades. Não interprete a soma entre creches como crianças únicas.

## Definição do CAGED feminino

Para prever o ano `t`, a covariável usa somente janeiro a setembro de `t-1`:

`cag_fem_taxa = (admissões femininas - desligamentos femininos) / estoque formal total no início de t-1`

Para o teste de 2025, isso significa janeiro a setembro de 2024, antes do processo de inscrição observado. No período, o município do Rio de Janeiro teve 287.457 admissões femininas, 257.320 desligamentos femininos e saldo de 30.137 vínculos.

O denominador é o estoque formal **total**, não o estoque feminino. O painel disponibiliza sexo para as movimentações, mas não fornece estoque municipal por sexo nessa tabela. Logo, a variável é uma medida de fluxo líquido feminino em relação ao tamanho do mercado formal municipal, e não um estoque de emprego feminino.

O CAGED é registrado pelo local do estabelecimento. Ele não mede diretamente o emprego das mães residentes em cada bairro e não possui variação entre creches dentro do mesmo ano.

## Modelo principal do teste

Para cada creche `i`, a taxa prevista é:

`log(taxa_i,2025) = intercepto + efeito_unidade_i + beta_tendencia * 4 + beta_caged * z_cag_fem_2025`

e a contagem é a taxa multiplicada pela exposição prevista pela Frente 1, igual a 65.114,2646 crianças únicas.

Coeficientes do teste principal:

- intercepto: -5,1862972;
- tendência: -0,2488673;
- CAGED feminino padronizado: 0,1023684;
- média de treino da taxa CAGED: 0,0050837232;
- desvio-padrão de treino: 0,0202795543;
- `z_cag_fem_2025`: 0,4894912;
- ridge `alpha`: 1e-8.

Os 834 efeitos por unidade estão em `coef_unidades.csv`. Os coeficientes comuns e as especificações de robustez estão em `coef_modelo.csv`.

## Validação fora da amostra — 2025

| Modelo | WAPE | Viés agregado | Total previsto |
|---|---:|---:|---:|
| PPML-FE + CAGED feminino pré-corte | 18,79% | -5,02% | 146.358 |
| PPML-FE base | 19,86% | +3,06% | 158.810 |
| Persistência | 20,15% | +14,63% | 176.639 |

O modelo com CAGED feminino reduz o WAPE em 1,08 ponto percentual frente ao PPML-FE base e em 1,37 ponto frente à persistência. Entretanto, o resultado não é estável: sem tendência o WAPE sobe para 47,91%, e excluindo 2021 sobe para 23,39%. Há somente quatro valores anuais independentes no treino e a covariável é comum a todas as creches.

Por isso, `prev_f1_cag_fem` deve ser tratado como cenário concorrente auditável, não como substituição automática do modelo base. O pacote mantém as três previsões lado a lado para a Frente 2 poder fazer análise de sensibilidade.

## Conteúdo

- `cag_fem_mensal.csv`: série oficial mensal de 2020 a 2024;
- `cag_fem_feat.csv`: construção da covariável pré-corte e padronização;
- `coef_modelo.csv`: coeficientes comuns e parâmetros das quatro especificações;
- `coef_unidades.csv`: efeitos fixos regularizados das 834 creches no modelo principal;
- `prev_creche_2025.csv`: previsões por creche para o handoff;
- `metricas_2025.csv`: métricas OOS do modelo, robustez, base e persistência;
- `manifesto.json`: definição do alvo, fonte, corte temporal e hashes dos arquivos;
- `../cag_fem_handoff.py`: código reprodutível de extração, estimação e exportação.

Fonte: Painel de Informações do Novo CAGED, Ministério do Trabalho e Emprego. Extração registrada no `manifesto.json`.
