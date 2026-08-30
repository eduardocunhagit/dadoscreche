# Arquitetura

Decisões e o porquê. Se você (ou seu agente) está prestes a mudar algo
listado aqui, pare e pense se a mudança se justifica — a restrição real
deste projeto não é performance, é que **várias pessoas sem formação de
desenvolvedor vão pedir a agentes de IA diferentes pra mexer neste código
ao longo do hackathon**. Toda escolha abaixo existe pra que uma edição
errada quebre alto e cedo (erro de tipo, teste vermelho), em vez de
silenciosamente.

## Stack

| Camada | Escolha | Por quê |
| --- | --- | --- |
| App | Next.js 16 (App Router, Turbopack) | Front e back num processo só |
| Linguagem | TypeScript `strict` | Ver "O argumento do TypeScript" abaixo |
| Banco (dev) | SQLite via `@prisma/adapter-better-sqlite3` | Zero setup — sem Docker, sem serviço rodando. Ninguém no time é dev; `npm install && npm run dev` tem que bastar |
| ORM | Prisma 7 | Schema declarativo, migrations versionadas, tipos gerados |
| UI | Tailwind v4 (CSS-first, sem `tailwind.config.js`) | Tokens de design em `src/app/globals.css`, zero dependência de componente externo |
| Auth | Auth.js v5 (`next-auth@beta`), Credentials | Sessão JWT com papel + escopo (polo/unidade) embutidos |
| Testes | Vitest | O motor de alocação (`src/core/domain/motor.ts`) é o que mais precisa ficar travado por teste |

### Por que SQLite e não Postgres

O plano original (documento publicado antes da implementação) propunha
Postgres. Na hora de montar o projeto de verdade, a consideração que
ganhou foi: **ninguém no time é desenvolvedor** — exigir um Postgres
rodando (Docker ou serviço externo) é o tipo de fricção que impede a
pessoa de sequer abrir o projeto. SQLite como arquivo local resolve isso
sem abrir mão de nada que este projeto usa (não há full-text search,
window functions exóticas nem extensões específicas do Postgres no
código). Migrar para Postgres depois é trocar o provider no
`prisma/schema.prisma` e o adapter em `src/core/db/client.ts` — o resto
do código não muda, porque nada consulta SQL bruto.

### O argumento do TypeScript

Um agente de IA que edita este repositório não sabe o que quebrou três
arquivos adiante. O compilador sabe. `strict: true` (já configurado em
`tsconfig.json`) converte a maior parte das quebras de contrato de "bug
descoberto na demo" em "erro na hora de salvar o arquivo". Antes de
qualquer commit, rode:

```bash
npx tsc --noEmit
npm test
```

### Next.js 16 — isto não é o Next que seu treinamento conhece

A versão instalada aqui (16.3.3) mudou bastante desde o que a maioria dos
modelos de IA aprendeu: `params`/`searchParams` são assíncronos
(`await props.params`), `middleware.ts` virou `proxy.ts`, Turbopack é
padrão. O arquivo `AGENTS.md` na raiz é gerado automaticamente pelo
`next dev` e aponta para a documentação certa em
`node_modules/next/dist/docs/` — **leia antes de escrever qualquer
página nova**. Não edite esse bloco à mão; ele volta sozinho.

## Camadas

```
src/
  core/                 — congelado; PR que mexe aqui pede revisão do dono
    db/client.ts         Prisma singleton (adapter better-sqlite3)
    domain/               regras de negócio puras, sem tocar banco
      constants.ts         os "enums" (strings — SQLite não tem enum nativo)
      motor.ts              máquina de estados + cascata do Eixo 2
      motor.test.ts
    events/bus.ts          barramento de eventos entre módulos
    auth/                  Auth.js — sessão com papel + escopo
    ui/                    componentes compartilhados (Botao, Cartao, Selo...)
  modules/
    tipos.ts               o contrato Modulo{}
    registry.ts             a única linha compartilhada que um módulo toca
    perfil-contatos/        módulo — rede de contatos, LGPD, histórico
    alocacao/                módulo — motor ligado ao banco
  app/
    login/
    (painel)/               tudo autenticado — layout confere sessão 1x
      meus-filhos/
      revalidacao-contatos/
      fila/
```

`core/domain/motor.ts` não importa Prisma nem nada de `src/modules` —
é lógica pura, testada isoladamente. Quem liga isso ao banco é
`src/modules/alocacao/servico.ts`, que grava um `OfertaEvento` para
**toda** transição — é essa tabela append-only que resolve o gap nº1 do
briefing ("não há registro de quando uma opção mudou de status").

## Convenções de banco

- Migrations são **aditivas**. Precisa de uma coluna numa tabela do
  núcleo? Não altere — crie uma tabela satélite 1:1 com o prefixo do seu
  módulo. Ver `EXTENDING.md`.
- Toda escrita passa por uma função de serviço do módulo dono da tabela
  (`src/modules/*/servico.ts`). Uma rota ou Server Action nunca chama
  `prisma.<tabela>.update` direto.
- As colunas que replicam a extração real da SME (`prmId`, `plmId`,
  `iplId`, `escCodigo`, `pergId`, `ichPergId`) são de propósito — é o que
  sustenta importar/exportar no formato original sem tradução.

## Autenticação e escopo

Quatro papéis (`src/core/domain/constants.ts`):

- `RESPONSAVEL` — só as próprias crianças (`Usuario.responsavelId`).
- `SERVIDOR_UNIDADE` — só uma unidade (`Usuario.unidadeEscCodigo`).
- `SERVIDOR_CRE` — só um polo — uma das 11 CREs (`Usuario.poloId`).
- `GESTOR_SME` — rede inteira; único papel que pode ligar/desligar as
  flags do motor de alocação.

O escopo fica na sessão JWT (`src/core/auth/config.ts`) e cada página do
painel filtra as próprias queries por ele — não existe uma camada de
autorização central tipo middleware/proxy fazendo isso; cada
Server Component/Server Action é responsável por checar. Ver o padrão em
`src/app/(painel)/meus-filhos/[criancaId]/actions.ts` (`autorOuFalha`).
