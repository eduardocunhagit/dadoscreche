# Fila Viva

Base do site do time para o **Hackathon SME-Rio + Rio Impact Lab 2026** —
Inscrição Creche. Cobre o Eixo 2 (classificação) e a parte do Eixo 3
(convocação) que dá pra resolver sem integração externa: um cadastro de
contatos de verdade e um motor de alocação com liberação em cascata e
aceite condicional.

Leia primeiro:

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — as decisões de stack e por quê.
- [`EXTENDING.md`](./EXTENDING.md) — como adicionar um módulo sem editar o
  núcleo. **Leia isto antes de abrir um PR**, principalmente se você (ou
  seu agente) está entrando no projeto pela primeira vez.
- `AGENTS.md` (raiz) — aviso automático do Next.js: esta versão (16) pode
  divergir do que um agente de IA já sabe. Ele aponta pra documentação
  correta em `node_modules/next/dist/docs/`.

## Rodando local

Não precisa de Docker nem de Postgres — o banco de desenvolvimento é um
arquivo SQLite (`dev.db`), criado na hora.

```bash
npm install
npm run db:migrate     # cria dev.db e aplica o schema
npm run db:seed        # importa dados REAIS das CSVs do desafio + contas de demo — ~30s
npm run dev             # http://localhost:3000
```

Você vai precisar criar um `.env` na raiz de `fila-viva/` (não vem no git):

```
DATABASE_URL="file:./dev.db"
AUTH_SECRET="qualquer-string-aleatoria-de-32-caracteres-aqui"
```

Contas de demonstração (senha `demo1234` para todas):

| E-mail | Papel | Escopo |
| --- | --- | --- |
| `gestor@filaviva.rio` | Gestor SME | Rede inteira |
| `cre1@filaviva.rio` | Servidor da CRE | Polo 1 (CRE 1) |
| `unidade@filaviva.rio` | Servidor da unidade | Uma unidade específica |
| `responsavel@filaviva.rio` | Responsável | As próprias crianças |

Para recomeçar do zero: `npm run db:reset && npm run db:seed`.

### O que o seed importa

O seed lê os arquivos reais em `../Bases IC_ ClassificadoseFila/` (fora
deste repositório) e monta:

- As 872+ unidades escolares (Query D).
- As 11 CREs (deduzidas de `plm_id` na Query A).
- O questionário e a régua de pontuação dos 5 processos (Query C).
- Inscrições, opções e crianças **reais** — por padrão só do processo de
  2025, polos 1 e 2 (18.592 das 837 mil linhas da Query A), pra rodar
  rápido. Amplie `ANO_SEED`/`POLOS_SEED` em `scripts/seed.ts` pra importar
  mais.

O que o seed **não** importa: a Query B (respostas socioeconômicas) —
nada nas telas atuais depende dela. E nenhum contato é real: a extração
anonimizada não tem telefone, e-mail nem nome (ver `README.md` da raiz do
projeto de dados). Os contatos e o histórico de quem-mudou-o-quê são
sintéticos, claramente marcados como tal no código do seed.

## Comandos

| Comando | O que faz |
| --- | --- |
| `npm run dev` | Sobe o site em desenvolvimento |
| `npm run build` | Build de produção |
| `npm test` | Roda os testes (o motor de alocação é o mais importante) |
| `npm run db:migrate` | Aplica migrations do Prisma |
| `npm run db:seed` | Popula com dados reais + contas de demo |
| `npm run db:reset` | Apaga e recria o banco do zero |
| `npx tsx scripts/simulador.ts` | Reprocessa a Query A real e mede o tamanho do problema que o Eixo 2 resolve — roda sem precisar do banco |

## O simulador — a evidência para o pitch

```bash
npx tsx scripts/simulador.ts             # os 5 processos, 2021-2025
npx tsx scripts/simulador.ts --ano=2025  # só o processo mais recente
```

Lê a Query A direto do `.csv.gz` (não precisa do seed nem do banco) e
imprime, sobre a base real do desafio:

- Em que posição da lista de preferência as famílias efetivamente
  confirmam (31,7% não ficam com a 1ª opção).
- Quantas vagas ficaram presas em opções piores que uma já confirmada —
  o problema que a **liberação em cascata** resolve (20.697 vagas-ciclo
  em 2021-2025).
- Quantas famílias confirmaram tendo uma opção melhor ainda em jogo — o
  público do **aceite condicional** (4.396).
- Quantos cadastros têm um estado inconsistente sem sinalização hoje
  (668) — o gap nº2 do briefing.

## Fluxo de inscrição — onde a família escolhe a creche

`/meus-filhos/[criancaId]/inscrever`: a família busca unidades por nome ou
bairro, escolhe até 5 em ordem de preferência (reordena, troca grupamento e
turno por opção), e confirma. Cria a `Inscricao` e as `Opcao` reais, todas
`NA_FILA` — a partir daí é o motor de alocação (`/fila`) que processa. Um
botão "+ Nova inscrição" aparece no perfil de cada criança, e o mesmo
perfil já lista as inscrições existentes com o estado de cada opção.

O que essa tela **não** faz ainda: aplicar a pontuação da Query C no
momento da inscrição (o questionário socioeconômico) — a fila hoje ordena
só por `dataCriacao`, não pela régua de pontos do processo. Ver "O que
ainda falta" abaixo.

## O que ainda falta (por fase — ver o plano publicado)

- **Fase 3B** — questionário socioeconômico no momento da inscrição e
  aplicação da régua de pontuação (Query C) pra ordenar a fila por pontos,
  não só por data. Também não fizemos a UI de gestão do catálogo de
  perguntas. Precisaria importar a Query B se algum módulo quiser
  reconstituir o perfil de vulnerabilidade de uma inscrição já existente.
- Convocação de verdade (Eixo 3) — este projeto só abre a **oferta** e
  grava o relógio; disparar WhatsApp/SMS/e-mail de verdade é o módulo de
  outra pessoa do time (ver `EXTENDING.md`).
