# modelo de escolha — escolha da unidade e concorrência

## 1. Pergunta e estimando

A modelo de escolha estima como a demanda **já inscrita** se distribui entre alternativas de creche. Seu estimando principal é a probabilidade de uma alternativa ser a primeira opção registrada, condicional à inscrição, ao grupamento, ao ano, ao território de origem e ao conjunto de alternativas elegíveis.

Esse objeto não é demanda potencial, matrícula nem alocação:

- **entrada na rede:** quantidade de crianças que se inscrevem; estimada pela modelo de demanda potencial;
- **preferência submetida:** ordem de unidades e turnos registrada pela família; objeto da modelo de escolha;
- **demanda prevista por alternativa:** entrada prevista multiplicada pela participação prevista pela modelo de escolha;
- **alocação:** aplicação posterior de pontuação, desempates, capacidade e elegibilidade;
- **matrícula:** resultado posterior da demanda, da oferta, da alocação e da confirmação.

A modelo de escolha não altera a prioridade socioeconômica e não produz ranking de crianças. Seu produto é uma previsão explicável para planejamento de oferta.

> **Decisão empírica.** Expandir a demanda histórica com atributos, distância e concorrência não garante melhora por construção. O modelo completo só é preferível se superar os benchmarks simples em 2024 e 2025. Caso contrário, o benchmark mais simples deve ser mantido.

## 2. Unidade de análise e notação

Todas as variáveis usadas nas equações são definidas nesta seção.

### 2.1 Índices, conjuntos e chaves

| Símbolo | Definição |
| --- | --- |
| `k` | Episódio de escolha: uma inscrição em um processo anual. |
| `c(k)` | Código anonimizado da criança associada ao episódio `k`. |
| `t(k)` | Ano do episódio `k`, entre 2021 e 2025. |
| `m(k)` | Território de residência associado ao episódio `k`. |
| `g(k)` | Grupamento etário associado ao episódio `k`. |
| `i` | Código canônico de uma unidade escolar. |
| `h` | Turno da opção, por exemplo integral ou parcial. |
| `a=(i,h)` | Alternativa formada pelo par unidade–turno. |
| `\mathcal C_k` | Conjunto de alternativas elegíveis e disponíveis para o episódio `k`. |
| `j` | Alternativa genérica usada no denominador de uma escolha. |
| `f` | Fold temporal de avaliação. |
| `\mathcal T_f` | Conjunto de anos de treinamento do fold `f`. |
| `T_f` | Ano-alvo do fold `f`. |

O grão canônico da estimação é `episódio de escolha × alternativa disponível`. A chave do episódio preserva `prm_id + plm_id + ipl_id`; `aluno_anon` identifica a criança, mas não substitui automaticamente a chave da inscrição. Casos com mais de uma inscrição da mesma criança no mesmo ano devem ser auditados e sinalizados. Não serão deduplicados por uma regra arbitrária.

O turno faz parte da alternativa porque pode variar entre as opções de uma mesma inscrição. A agregação para unidade será feita somente depois de preservar `unidade × grupamento × turno`.

### 2.2 Desfechos, atributos e parâmetros

| Símbolo | Definição |
| --- | --- |
| `y_{ka}` | Indicador igual a 1 quando a alternativa `a` é a primeira opção do episódio `k`, e 0 caso contrário. |
| `r_{ka}` | Posição observada da alternativa `a` na lista do episódio `k`; vale 1 para a primeira opção. |
| `L_k` | Número de opções submetidas no episódio `k`. |
| `d_{ka}` | Distância entre a origem do episódio `k` e a unidade da alternativa `a`. |
| `q_{agt}^{pre}` | Medida de capacidade ou tamanho da alternativa `a`, no grupamento `g` e ano `t`, conhecida antes da escolha. |
| `x_{agt}` | Vetor de atributos observáveis da alternativa `a`, do grupamento `g` e do ano `t`, disponíveis antes da escolha. |
| `z_k` | Vetor de características observáveis do episódio `k`, disponíveis antes da escolha. |
| `w_{kagt}` | Vetor de interações explicáveis entre elementos de `z_k` e atributos da alternativa. |
| `G_{agt}` | Índice de concorrência geográfica da alternativa `a`, no grupamento `g` e ano `t`. |
| `R_{agt}` | Índice de concorrência revelada por co-listagem da alternativa `a`, no grupamento `g` e ano `t`. |
| `H_{agt}` | Índice híbrido que combina proximidade geográfica e co-listagem. |
| `V_{ka}` | Utilidade sistemática prevista da alternativa `a` para o episódio `k`. |
| `P_{ka}` | Probabilidade prevista de o episódio `k` escolher a alternativa `a` como primeira opção. |
| `\beta_d` | Coeficiente associado à distância. |
| `\beta_q` | Coeficiente associado à capacidade ou ao tamanho ex ante. |
| `\boldsymbol\beta_x` | Vetor de coeficientes dos atributos da alternativa. |
| `\boldsymbol\beta_w` | Vetor de coeficientes das interações. |
| `\beta_G`, `\beta_R`, `\beta_H` | Coeficientes dos índices de concorrência geográfica, revelada e híbrida. |
| `\alpha_i` | Efeito específico da unidade `i`, usado apenas em diagnóstico para unidades incumbentes. |

Características do episódio que não variam entre alternativas não são identificadas isoladamente pelo conditional logit. Elas entram somente por interações com distância, turno ou atributos da unidade. Pontuação socioeconômica não entra como atratividade nem como substituto da regra legal.

## 3. Construção da amostra

### 3.1 Episódios e primeira opção

Para cada inscrição anual:

1. preservar todas as opções registradas e sua ordem;
2. identificar uma única primeira opção;
3. preservar grupamento e turno de cada opção;
4. verificar duplicidade de posição, opção fora do intervalo usual e inconsistência de grupamento;
5. sinalizar múltiplas inscrições de `c(k)` no mesmo ano;
6. não usar a situação final da opção como preditor.

O modelo principal usa a primeira opção porque ela fornece um desfecho simples e comparável. As demais posições alimentam os índices de co-listagem e, posteriormente, o rank-ordered logit. Uma criança continua valendo uma unidade de demanda, mesmo quando lista várias alternativas.

### 3.2 Conjunto de alternativas

Para cada episódio `k`, `\mathcal C_k` deve conter somente alternativas que:

- existiam no ano `t(k)`;
- ofereciam o grupamento `g(k)`;
- ofereciam o turno correspondente;
- eram elegíveis segundo regras reconstruíveis com os dados;
- pertenciam à área de acessibilidade definida antes de estimar o modelo.

A alternativa escolhida deve pertencer a `\mathcal C_k`. Caso contrário, o episódio é uma falha de construção do conjunto, não uma observação a ser silenciosamente descartada.

Não há, nas extrações, um catálogo histórico perfeitamente uniforme de todas as alternativas disponíveis a cada família. Portanto, o conjunto de escolha será uma reconstrução. A versão inicial usa unidades ativas em `ano × grupamento × turno`, com regra espacial declarada. Devem ser reportadas sensibilidade à regra espacial, taxa de cobertura da alternativa escolhida e tamanho do conjunto.

### 3.3 Geografia e oferta

A origem será construída sem reidentificação:

1. território associado ao CEP, quando a correspondência estiver disponível;
2. território associado ao bairro como fallback;
3. categoria de origem sem geografia quando nenhum vínculo for possível.

Distância em linha reta é a medida inicial. Tempo de deslocamento só entra como extensão se puder ser reproduzido. Unidade deve ser ligada pelo código normalizado; nome e endereço servem apenas como checagem.

Matrícula não será chamada de capacidade. Até a harmonização das planilhas de oferta, a especificação pode usar tamanho ou número de turmas defasados, com nome de variável que preserve o conceito observado. Uma capacidade contemporânea só entra se for informação ou cenário disponível antes das inscrições.

## 4. Benchmarks

Cada benchmark produz probabilidades no mesmo conjunto `\mathcal C_k` do modelo principal.

### 4.1 Definições adicionais

| Símbolo | Definição |
| --- | --- |
| `N_{mgt}^{obs}` | Número observado de episódios com origem `m`, grupamento `g` e ano `t`. |
| `D_{agt}^{obs}` | Número observado de primeiras opções da alternativa `a`, no grupamento `g` e ano `t`. |
| `S_{amg,\mathcal T_f}^{hist}` | Participação histórica da alternativa `a` entre as primeiras opções de origem `m` e grupamento `g`, calculada somente nos anos `\mathcal T_f`. |
| `P_{ka}^{hist}` | Probabilidade do benchmark de participação histórica. |
| `P_{ka}^{near}` | Probabilidade do benchmark da alternativa mais próxima. |

O benchmark de participação histórica atribui a cada alternativa elegível sua participação anterior e renormaliza as participações dentro de `\mathcal C_k`:

$$
P_{ka}^{hist}
=
\frac{S_{am(k)g(k),\mathcal T_f}^{hist}}
{\sum_{j\in\mathcal C_k}S_{jm(k)g(k),\mathcal T_f}^{hist}}.
$$

O cálculo usa suavização e fallback previamente definidos: `território × grupamento`, depois `grupamento`, sem consultar o ano-alvo. Alternativas novas recebem o fallback, não probabilidade zero automática.

O benchmark geográfico escolhe a alternativa de menor distância. Se houver empate, divide a probabilidade igualmente entre as alternativas empatadas. Sua probabilidade é denotada por `P_{ka}^{near}`.

Serão comparados:

1. participação histórica da alternativa;
2. alternativa mais próxima;
3. conditional logit apenas com distância;
4. conditional logit com distância, atributos e oferta ex ante;
5. modelo completo com concorrência e interações;
6. rank-ordered logit, somente como extensão.

A contagem de todas as opções por unidade será exibida apenas como **pressão de lista**. Ela duplica crianças e não é demanda comparável à primeira opção.

## 5. Conditional logit explicável

### 5.1 Especificações

A utilidade sistemática do modelo completo é definida por:

$$
V_{ka}
=
\beta_d\log(1+d_{ka})
+\beta_q\log(1+q_{ag(k)t(k)}^{pre})
+\boldsymbol\beta_x'x_{ag(k)t(k)}
+\boldsymbol\beta_w'w_{kag(k)t(k)}
+\beta_G G_{ag(k)t(k)}
+\beta_R R_{ag(k)t(k)}
+\beta_H H_{ag(k)t(k)}.
$$

A probabilidade de primeira escolha é definida por:

$$
P_{ka}
=
\frac{\exp(V_{ka})}
{\sum_{j\in\mathcal C_k}\exp(V_{kj})}.
$$

A sequência de especificações deve ser cumulativa. Isso permite mostrar quanto cada bloco acrescenta:

- **M1:** distância;
- **M2:** M1 + atributos da unidade, turno e medida de oferta ex ante;
- **M3:** M2 + concorrência geográfica e co-listagem;
- **M4:** M3 + poucas interações pré-especificadas, como `distância × grupamento` e `distância × vulnerabilidade territorial`.

Uma especificação com `\alpha_i` pode ser estimada como diagnóstico in-sample e para incumbentes. Ela não será o modelo principal porque não consegue atribuir efeito próprio a unidades novas. O modelo transportável, baseado em atributos observáveis, é obrigatório na avaliação completa.

### 5.2 Explicação

O dashboard deve traduzir coeficientes em objetos compreensíveis:

- sinal e intervalo do coeficiente;
- razão de chances para uma variação declarada do atributo;
- mudança média na probabilidade prevista;
- decomposição da utilidade prevista em distância, oferta, atributos e concorrência;
- comparação da unidade com alternativas do mesmo conjunto.

Essas decomposições explicam a previsão, não uma relação causal. Aberturas e capacidade podem responder à demanda preexistente.

### 5.3 Hipóteses e limitações

O conditional logit impõe independência de alternativas irrelevantes. Unidades semelhantes podem violar essa hipótese. O teste prático é estabilidade dos coeficientes e das previsões ao retirar grupos de alternativas ou alterar o raio do conjunto de escolha. Modelos mais flexíveis só entram se trouxerem ganho OOS e continuarem auditáveis.

A primeira opção é uma **preferência submetida sob as regras existentes**, não necessariamente preferência verdadeira. Famílias podem ordenar estrategicamente conforme expectativa de vaga, prioridade e conhecimento do sistema. Por isso:

- coeficientes não serão interpretados como disposição causal a viajar ou valor de bem-estar;
- o modelo não simulará aceitação de unidade não listada como se fosse observada;
- mudanças de regra podem alterar o comportamento de submissão;
- o rank-ordered logit será apresentado como extensão sujeita a hipótese mais forte sobre a lista.

## 6. Concorrência

### 6.1 Definições adicionais

| Símbolo | Definição |
| --- | --- |
| `d_{ab}` | Distância entre as unidades das alternativas `a` e `b`. |
| `\tau` | Parâmetro positivo de decaimento geográfico, escolhido somente no treino. |
| `n_{a,\mathcal T_f}` | Número de episódios do treino que listaram a alternativa `a`. |
| `n_{ab,\mathcal T_f}` | Número de episódios do treino que listaram simultaneamente `a` e `b`. |
| `\omega_{ab,\mathcal T_f}` | Peso normalizado de co-listagem entre `a` e `b`, calculado no treino. |
| `b` | Alternativa concorrente distinta de `a`. |

O índice geográfico é:

$$
G_{agt}
=
\sum_{b\neq a}
q_{bgt}^{pre}\exp(-d_{ab}/\tau).
$$

O peso de co-listagem é:

$$
\omega_{ab,\mathcal T_f}
=
\frac{n_{ab,\mathcal T_f}}
{\sqrt{n_{a,\mathcal T_f}n_{b,\mathcal T_f}}}.
$$

O índice revelado é:

$$
R_{agt}
=
\sum_{b\neq a}
\omega_{ab,\mathcal T_f}q_{bgt}^{pre}.
$$

O índice híbrido é:

$$
H_{agt}
=
\sum_{b\neq a}
\omega_{ab,\mathcal T_f}
q_{bgt}^{pre}\exp(-d_{ab}/\tau).
$$

Somente alternativas que atendem ao grupamento relevante entram nas somas. As redes de co-listagem são reconstruídas em cada fold usando apenas `\mathcal T_f`. Para unidades novas ou pares sem histórico, geografia e atributos observáveis fornecem o fallback.

O denominador do conditional logit continua sendo a representação principal da substituição entre alternativas. Os índices resumem o ambiente competitivo para diagnóstico e comunicação; não medem efeito causal da concorrência.

## 7. Rank-ordered logit como extensão

### 7.1 Definições adicionais

| Símbolo | Definição |
| --- | --- |
| `a_{k\ell}` | Alternativa colocada na posição `\ell` da lista do episódio `k`. |
| `\ell` | Posição da alternativa na lista, de 1 até `L_k`. |
| `\mathcal L_k` | Contribuição do episódio `k` para a verossimilhança da lista ordenada. |

A contribuição sequencial é:

$$
\mathcal L_k
=
\prod_{\ell=1}^{L_k}
\frac{\exp(V_{k a_{k\ell}})}
{\sum_{j\in\mathcal C_k\setminus\{a_{k1},\ldots,a_{k,\ell-1}\}}
\exp(V_{kj})}.
$$

Essa extensão usa as posições adicionais sem contar a criança várias vezes na demanda. Ela será estimada somente após o modelo de primeira opção e não substitui o resultado principal. Listas curtas, truncadas ou estratégicas tornam sua interpretação mais forte e menos segura.

## 8. Avaliação

### 8.1 In-sample

O teste in-sample verifica ajuste e implementação, não seleciona sozinho o modelo. Serão reportados:

- log loss e acurácia da primeira escolha;
- calibração das probabilidades;
- participação prevista e observada por alternativa;
- erro de contagem por unidade, grupamento e turno, condicionado ao total observado de inscritos;
- resíduos por distância, território, grupamento, tipo de gestão e tamanho da unidade;
- estabilidade de sinais e intervalos dos coeficientes.

Invariantes devem ser testados antes das métricas: uma primeira opção por episódio, alternativa escolhida no conjunto, probabilidades somando um e ausência de atributos posteriores à escolha.

### 8.2 Folds fora da amostra

| Fold | Treino `\mathcal T_f` | Ano-alvo `T_f` |
| --- | --- | --- |
| OOS-2024 | 2021–2023 | 2024 |
| OOS-2025 | 2021–2024 | 2025 |

Todas as transformações são refeitas dentro do fold: imputação, padronização, conjunto histórico de unidades, suavização de shares, rede de co-listagem, escolha de `\tau` e estimação. Situação final, matrículas realizadas e listas do ano-alvo não entram como preditores.

O resultado de 2024 será separado em:

- unidades presentes no treino;
- unidades novas, ausentes em 2021–2023;
- amostra completa.

Não será presumida uma quantidade de unidades novas. Ela será calculada pelo pipeline e registrada no relatório. O mesmo diagnóstico será repetido em 2025.

### 8.3 Métricas definidas

| Símbolo | Definição |
| --- | --- |
| `K_f` | Conjunto de episódios do ano-alvo do fold `f`. |
| `A_f` | Número de episódios em `K_f`. |
| `\widehat P_{ka}^{(f)}` | Probabilidade OOS da alternativa `a` para o episódio `k` no fold `f`. |
| `a_k^*` | Primeira alternativa efetivamente escolhida no episódio `k`. |
| `\widehat D_{agt}^{cond}` | Demanda prevista para `a,g,t`, condicionada ao total observado de inscritos. |
| `\varepsilon_{agt}` | Erro da demanda condicional da alternativa `a,g,t`. |

A log loss OOS é:

$$
\operatorname{LogLoss}_f
=
-\frac{1}{A_f}
\sum_{k\in K_f}\log\widehat P_{k a_k^*}^{(f)}.
$$

A demanda condicional prevista é:

$$
\widehat D_{agt}^{cond}
=
\sum_{k\in K_f:\,g(k)=g,\,t(k)=t}
\widehat P_{ka}^{(f)}.
$$

O erro condicional é:

$$
\varepsilon_{agt}
=
\widehat D_{agt}^{cond}-D_{agt}^{obs}.
$$

Também serão reportados MAE, WAPE e erro de participação por unidade. A avaliação condicional isola a distribuição entre alternativas, sem atribuir à modelo de escolha o erro no total de inscritos.

### 8.4 Critério de seleção

O modelo principal deve:

1. superar participação histórica e distância na média dos folds OOS;
2. não depender de efeito fixo para prever unidade nova;
3. manter calibração aceitável nos principais subgrupos;
4. conservar o total de inscritos ao agregar probabilidades;
5. ter coeficientes e decomposições compreensíveis;
6. evitar ganho concentrado apenas no ajuste in-sample.

Se as métricas divergirem, log loss é a métrica principal de escolha individual e WAPE/MAE orientam planejamento por unidade. A decisão e a diferença para cada benchmark serão registradas, sem declarar vitória por construção.

## 9. Integração com a modelo de demanda potencial

### 9.1 Definições adicionais

| Símbolo | Definição |
| --- | --- |
| `\widehat A_{mgt}` | Número de inscrições previsto pela modelo de demanda potencial para território `m`, grupamento `g` e ano `t`. |
| `\widehat s_{amgt}` | Participação prevista pela modelo de escolha para alternativa `a`, território `m`, grupamento `g` e ano `t`. |
| `\widehat D_{agt}` | Demanda integrada prevista para alternativa `a`, grupamento `g` e ano `t`. |

A integração é:

$$
\widehat D_{agt}
=
\sum_m \widehat A_{mgt}\widehat s_{amgt}.
$$

As participações devem somar um dentro de cada `m × g × t` com cobertura. Assim, a integração conserva o total territorial. Células sem alternativa elegível são marcadas como ausência de cobertura; não são renormalizadas para uma unidade incompatível.

A comparação da demanda integrada com a histórica só ocorre quando a previsão OOS da modelo de demanda potencial estiver disponível. Antes disso, `\widehat D_{agt}^{cond}` é o produto correto para avaliar isoladamente a modelo de escolha.

## 10. Sequência de desenvolvimento

1. **Contrato de dados:** congelar chaves, grãos, grupamento, turno e regra de disponibilidade.
2. **Auditoria:** testar primeira opção, identidade, duplicidades, vínculos de unidade e geografia.
3. **Conjuntos de escolha:** reconstruir elegibilidade e cobertura, com teste de inclusão da escolhida.
4. **Benchmarks:** participação histórica e distância.
5. **M1–M2:** conditional logit com distância, atributos e oferta ex ante.
6. **Concorrência:** construir geografia e co-listagem dentro de cada fold.
7. **M3–M4:** adicionar concorrência e interações pré-especificadas.
8. **Avaliação:** rodar in-sample, OOS-2024 e OOS-2025, com segmento de unidades novas.
9. **Seleção:** escolher a menor especificação que entregue ganho OOS material e estável.
10. **Extensão:** estimar rank-ordered logit somente se o MVP estiver validado.
11. **Integração:** aplicar as participações congeladas à saída da modelo de demanda potencial.
12. **Dashboard:** publicar resultados agregados, explicações, comparação de modelos e limitações.

## 11. Limitações que acompanham todo resultado

- As extrações de 2021–2025 são históricas, anonimizadas e perturbadas; seus níveis não representam 2026.
- A regra jurídica de 2026 não reconstrói preferências nem pontuações históricas.
- O conjunto de alternativas é reconstruído e pode não representar toda informação disponível à família.
- Lista submetida pode ser estratégica e não identifica preferência latente de bem-estar.
- Ausência de uma unidade na lista não prova rejeição dessa unidade.
- Oferta e capacidade têm fontes e datas de referência heterogêneas.
- O modelo é preditivo; coeficientes de distância, capacidade e concorrência não são causais.
- A modelo de escolha não determina classificação, alocação ou convocação.
