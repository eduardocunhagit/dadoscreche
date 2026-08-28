# Dicionário de dados — Extração anonimizada Inscrição Creche (Hackathon)

## Escopo

- **Processos incluídos**: 179 (2021), 181 (2022), 184 (2023), 194 (2024), 195 (2025).

## Formato dos arquivos

As duas bases maiores estão neste repositório **compactadas em `.gz`**. O GitHub recusa
qualquer arquivo acima de 100 MB, e o CSV cru passa desse limite.

| Arquivo | Compactado | Descompactado |
|---|---|---|
| `01_QueryA_InscricoesPorAno.csv.gz` | 20 MB | 154 MB (837.180 linhas) |
| `02_QueryB_RespostasSocioEconomicas.csv.gz` | 14 MB | 436 MB (4.357.120 linhas) |

O conteúdo é idêntico ao CSV original, byte a byte. Não é preciso descompactar antes de
usar — a maioria das ferramentas lê `.csv.gz` direto:

```python
import pandas as pd
df = pd.read_csv("01_QueryA_InscricoesPorAno.csv.gz", sep=";", encoding="utf-8-sig")
```

```r
df <- read.csv2(gzfile("01_QueryA_InscricoesPorAno.csv.gz"), fileEncoding = "UTF-8-BOM")
```

```sql
-- DuckDB
SELECT * FROM read_csv_auto('02_QueryB_RespostasSocioEconomicas.csv.gz', delim=';');
```

Para gerar o CSV no disco: `gunzip -k 01_QueryA_InscricoesPorAno.csv.gz`.

Os arquivos usam separador `;`, codificação UTF-8 com BOM.

## Antes de começar

Duas armadilhas comuns com a `02_QueryB`:

**O Excel não dá conta desta base.** Ele não abre `.csv.gz` (é preciso descompactar antes),
e mesmo descompactada a QueryB tem 4.357.119 linhas — acima do teto do Excel, que é
1.048.576 linhas. O arquivo abriria truncado, sem aviso claro. Use Python, R, DuckDB ou
um banco de dados. A `01_QueryA` tem 837.179 linhas e cabe no Excel, mas ainda assim
precisa ser descompactada primeiro.

**Carregar a QueryB inteira na memória exige vários GB de RAM.** Isso vale igual para o
CSV cru: não é efeito da compactação. Em máquinas comuns, leia em blocos e vá agregando:

```python
import pandas as pd

total = 0
for bloco in pd.read_csv("02_QueryB_RespostasSocioEconomicas.csv.gz",
                         sep=";", encoding="utf-8-sig", chunksize=500_000):
    total += len(bloco)   # troque pelo seu filtro/agregação
```

Alternativa mais simples: o DuckDB lê o `.gz` direto do disco e só carrega o resultado da
consulta, sem precisar da base inteira na memória.

## Anonimização

- **Criança → `aluno_NNNNNNN`**: chave natural = CPF → (se vazio) DNV → (se vazio) NIS → (se vazio) nome normalizado + data de nascimento. O mesmo código é usado em todas as opções de creche e em todos os 5 processos em que a criança aparecer.
- **Responsável → `responsavel_NNNNNNN`**: chave natural = NIS → (se vazio) nome normalizado + data de nascimento.
- O mapeamento é recalculado a cada execução via CTE (`ROW_NUMBER()` sobre a chave ordenada) — não há tabela de mapeamento persistida no banco (o acesso usado é somente leitura). Isso é determinístico e estável desde que os dados de entrada não mudem entre execuções, o que é seguro aqui porque 2021–2025 são processos fechados/históricos.
- Dados generalizados por privacidade: nascimento da criança sai só como ano-mês (`yyyy-MM`); do responsável não é exposto nascimento nem nome; do endereço só saem bairro e CEP (sem logradouro, número ou telefones).

## Query A — Extração principal

**Grão**: uma linha por *opção de creche escolhida* dentro de uma inscrição (`ich_id`). Uma criança pode ter várias linhas (uma por opção) e reaparecer em processos/anos diferentes.

**Chave de junção com a Query B**: `(prm_id, plm_id, ipl_id)`.

| Coluna | Tipo / origem | Tabela.Coluna de origem | Descrição | Observações |
|---|---|---|---|---|
| `ano` | int (literal) | CTE `Processos` | Ano do processo seletivo (2021–2025) | Fixo por processo, não vem do banco |
| `prm_id` | int | `ICH_ProcessoMatricula.prm_id` | Identificador do processo de matrícula | Chave "raiz" da hierarquia |
| `plm_id` | int | `ICH_PoloProcessoMatricula.plm_id` | Identificador do polo/lote dentro do processo | Composto com `prm_id` |
| `ipl_id` | int | `ICH_InscricaoPolo.ipl_id` | Identificador da inscrição dentro do polo | "ID da inscrição" propriamente dito |
| `opcao` | int | `ICH_InscricaoCreche.ich_id` | Número da opção de creche escolhida (1ª, 2ª...) | Uma inscrição pode ter várias opções → várias linhas |
| `unidade` | ? (`esc_codigo`) | `Synonym_ESC_Escola.esc_codigo` | Código da unidade escolar (creche) | Objeto *synonym* (aponta para outro banco); tipo/tamanho não confirmados |
| `nome_unidade` | ? (`esc_nome`) | `Synonym_ESC_Escola.esc_nome` | Nome da unidade escolar | idem acima |
| `grupamento` | ? (`crp_descricao`) | `Synonym_ACA_CurriculoPeriodo.crp_descricao` | Faixa/grupamento etário-curricular (ex.: Berçário, Maternal) | idem acima |
| `horario` | varchar (derivado) | `ICH_InscricaoCreche.ich_horarioIntegral` | `'Integral'` ou `'Parcial'` | CASE calculado, não é coluna física |
| `ficha` | nvarchar(100), nulo | `ICH_InscricaoPolo.ipl_codigoFicha` | Código da ficha de inscrição impressa | Pode ser NULL |
| `data_criacao` | datetime | `ICH_InscricaoPolo.ipl_dataCriacao` | Data/hora de criação da inscrição | Não nulo na origem |
| `aluno_anon` | varchar(30), gerado | CTE `MapCrianca` | Código anonimizado da criança | Estável entre opções e entre os 5 processos |
| `sexo_crianca` | nchar(2) | `ICH_InscricaoCrianca.icr_sexo` | Sexo da criança | Valores prováveis `M`/`F`, não confirmados nos dados reais |
| `nascimento_aluno_anomes` | varchar (derivado) | `ICH_InscricaoCrianca.icr_dataNascimento` | Ano-mês de nascimento (`yyyy-MM`) | Generalizado por privacidade (sem o dia) |
| `responsavel_anon` | varchar(30), gerado, **nulo possível** | CTE `MapResponsavel` | Código anonimizado do responsável 1 (`ire_id = 1`) | `LEFT JOIN` — NULL se não houver responsável cadastrado |
| `CEP` | ?, nulo possível | `[CoreSSO]...[END_Endereco].end_cep` (via `ICH_ResponsavelEndereco`) | CEP do endereço do responsável | Tabela em banco externo, tipo não documentado; NULL se não houver endereço ativo |
| `bairro` | ?, nulo possível | `END_Endereco.end_bairro` | Bairro do endereço do responsável | mesma ressalva do CEP |
| `situacao` | varchar (derivado) | `ich_situacaoIntegral` / `ich_situacaoParcial` (tinyint) | Status da inscrição/opção: Ativo, Bloqueado, Excluído, Selecionado, Lista de espera, Selecionado da lista, Cancelado, Confirmado, Cancelado pelo sistema, Cancelado na confirmação | Enum reconstruído a partir de comentários no SQL de origem da aplicação, não de uma tabela de domínio |

**Filtros aplicados** (não viram coluna, mas afetam quais linhas saem):
- `ich_situacaoIntegral NOT IN (3,10)` e `ich_situacaoParcial NOT IN (3,10)`.
- Apenas os 5 processos listados acima (2026 fora).

## Query B — Respostas às perguntas de classificação (formato longo)

**Grão**: uma linha por *pergunta respondida* dentro de uma inscrição.

| Coluna | Tipo / origem | Tabela.Coluna de origem | Descrição |
|---|---|---|---|
| `ano` | int (literal) | CTE `Processos` | Ano do processo |
| `prm_id`, `plm_id`, `ipl_id` | int | `ICH_PerguntaResposta` | Chave da inscrição (liga com a Query A) |
| `ich_perg_id` | int | `ICH_PerguntaResposta.ich_perg_id` | Identificador da pergunta *nesse processo específico* (muda de ano para ano) |
| `pergunta_texto` | varchar(max), nulo possível | `[CoreSSO]...[SYS_Pergunta].pergunta` | Texto completo da pergunta (catálogo central, estável entre processos via `perg_id`) |
| `pergunta_legenda` | varchar, nulo possível | `ICH_Pergunta.perg_tituloLegenda` | Rótulo curto usado em legendas/gráficos pela aplicação |
| `pergunta_ordem` | int | `ICH_Pergunta.perg_ordemVisualizacao` | Ordem de exibição da pergunta no formulário |
| `resposta` | `'Sim'` / `'Nao'` / NULL | `ICH_PerguntaResposta.resp_perg` (1/2) | Resposta dada pela família |
| `confirmado` | `'Sim'` / `'Nao'` / NULL | `ICH_PerguntaResposta.resp_confirmado` (bit) | Se a resposta foi confirmada/validada |

**Filtro aplicado**: `resp_situacao = 1` (só respostas ativas).

## Query C (bônus) — Catálogo de perguntas por processo/ano

Uma linha por pergunta distinta usada em cada processo — útil como changelog: mostra `perg_id` (chave estável no catálogo), `pergunta_texto`, `pergunta_legenda` e `ich_perg_id` (a instância daquele ano), para comparar se a redação mudou de um ano para o outro.
