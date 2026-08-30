# Frente 2 — distribuição da demanda entre creches

A Frente 1 estima quantas famílias entrarão na rede em cada `ano × território de origem × grupamento`. A Frente 2 estima como esse total se distribui entre alternativas `unidade × turno`.

A previsão integrada é:

`demanda prevista da alternativa = inscrições previstas pela Frente 1 × participação prevista pela Frente 2`.

A alocação legal vem depois. O modelo de demanda não altera prioridade, desempate ou elegibilidade.

## Organização

~~~text
frente2/
├── 01_problema_e_estimando/          pergunta econômica, estimando e contrato das saídas
├── 02_universo_de_escolha/           mercados, alternativas e geografia
├── 03_preferencias_e_concorrencia/   modelos de escolha e medidas de concorrência
├── 04_validacao_in_sample_oos/       comparação histórica, in-sample e OOS
├── 05_integracao_com_frente1/        contrato, exemplos e chave de integração
├── 06_resultados/                     síntese e arquivos gerados
├── 07_painel/                         painel de resultados
├── rotinas/                           funções usadas pela estimação
├── testes/                            invariantes e testes sintéticos
├── executar_frente2.py                execução completa da Frente 2
└── integrar_frentes.py                multiplicação Frente 1 × Frente 2
~~~

## O que cada frente entrega

A Frente 1 deve entregar `ano`, `origin_area`, `grupamento_norm` e `inscricoes_previstas`. A Frente 2 entrega, nas mesmas células, `alternativa_id`, `unidade`, `horario_norm` e `choice_share`. As participações devem somar um dentro de cada célula.

O contrato completo e arquivos de exemplo estão em `05_integracao_com_frente1/CONTRATO_DE_INTEGRACAO.md`.

## Modelos estimados

1. participação histórica;
2. unidade mais próxima;
3. conditional logit com distância;
4. conditional logit com distância, atributos e demanda defasada;
5. conditional logit completo, com concorrência geográfica e co-listagem.

Os logits são lineares e seus coeficientes são exportados com erro-padrão robusto agrupado por mercado e intervalo de confiança de 95%. Esses coeficientes descrevem associação preditiva, não efeito causal.

## Execução

~~~powershell
python frente2/executar_frente2.py
python -m unittest discover -s frente2/testes -v
~~~

Integração com a Frente 1:

~~~powershell
python frente2/integrar_frentes.py --frente1 caminho/previsao_frente1.csv --frente2 caminho/participacoes_frente2.csv --saida frente2/06_resultados/arquivos_gerados/demanda_integrada.csv
~~~

Painel:

~~~powershell
cd frente2/07_painel
npm install
npm run dev
~~~

## Validação

- OOS-2024: treino em 2021–2023. Unidades incumbentes e creches parceiras são avaliadas separadamente porque as parceiras só aparecem na extração em 2024.
- OOS-2025: treino em 2021–2024 e teste no universo completo.
- Métricas: log loss, acerto da primeira opção, MAE e WAPE da demanda por alternativa.
- Referência obrigatória: participação histórica. Um modelo mais rico só é escolhido quando melhora o objetivo de previsão relevante.

## Git

A raiz contém alterações que não pertencem necessariamente à Frente 2. Para preparar apenas esta entrega:

~~~powershell
git status --short -- frente2
git diff --check -- frente2
git add frente2
git commit -m "feat: estima demanda entre creches e integra frentes"
git push
~~~

Não use `git add .` para esta entrega.