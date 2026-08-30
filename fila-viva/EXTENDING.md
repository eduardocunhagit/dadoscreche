# Como estender este projeto sem quebrar o que já existe

Este projeto foi montado assumindo que **outras pessoas do time vão pedir
para os próprios agentes de IA delas mexerem aqui**, sem terem lido todo o
histórico de decisões. Este documento é o que substitui esse contexto.

## A regra de uma linha

**Você adiciona coisas. Você não edita o que já existe**, salvo bug
concreto. Se a sua feature parece exigir editar um arquivo em `src/core`
ou em `src/modules/<outro-módulo>`, é sinal de que falta um ponto de
extensão — peça pra adicionar (ou abra uma issue), não contorne editando
direto.

## Passo a passo — criando um módulo novo

Use `src/modules/exemplo/` como referência viva; é um módulo mínimo real,
registrado, e o cartão azul-claro que aparece no topo do painel quando
você roda o projeto vem dele.

1. **Crie a pasta.** `src/modules/<seu-modulo>/index.ts` exportando um
   objeto que satisfaz `Modulo` (`src/modules/tipos.ts`):

   ```ts
   import type { Modulo } from "../tipos";

   export const meuModulo: Modulo = {
     id: "meu-modulo",
     nome: "Nome legível",
     menu: [{ href: "/minha-rota", label: "Minha Rota", papeis: ["GESTOR_SME"] }],
     widgets: [{ slot: "dashboard-topo", component: MeuWidget }],
     assina: { "oferta.criada": async (payload) => { /* ... */ } },
   };
   ```

   Todos os campos são opcionais — um módulo pode só ter uma rota, só um
   widget, ou só uma assinatura de evento.

2. **Registre.** Abra `src/modules/registry.ts`, importe seu módulo e
   acrescente na lista `MODULOS`. É a única linha que um arquivo do núcleo
   ganha por causa do seu módulo.

3. **Crie a rota de verdade, se precisar de uma.** O Next.js resolve
   páginas por arquivo, não em runtime — o `href` do seu item de menu
   precisa de um `src/app/(painel)/<sua-rota>/page.tsx` correspondente.
   `menu` só decide o que aparece na barra lateral e pra quem.

4. **Se precisar guardar dado**, crie uma tabela satélite 1:1 com o
   prefixo do seu módulo (ex.: `conv_TentativaContato`), nunca uma coluna
   nova numa tabela do núcleo. Ver "Banco de dados" abaixo.

5. **Se precisar reagir a algo que outro módulo faz**, assine um evento do
   barramento (`src/core/events/bus.ts`) em vez de importar a lógica do
   outro módulo. Os eventos disponíveis hoje estão no tipo
   `EventoDoBarramento` nesse arquivo — precisa de um evento novo? Peça
   pra acrescentar lá (é uma linha), não simule chamando o serviço do
   outro módulo direto.

## O que roda sozinho se você tentar cruzar a fronteira

Não é só documentação — antes de abrir um PR, rode:

```bash
npx tsc --noEmit   # quebra de contrato com o núcleo não compila
npm test           # os testes de src/core/domain/motor.ts não podem mudar,
                    # só ganhar testes novos — um teste alterado é o sinal
                    # mais confiável de que alguém contornou a fronteira
npm run lint
npm run build
```

Os quatro têm que passar. Se `npm test` só passa depois de você editar um
`.test.ts` existente (não criar um novo), pare — isso quase sempre
significa que a mudança devia ter sido um módulo novo, não uma edição do
núcleo.

## Banco de dados

- **Migrations são aditivas.** `npx prisma migrate dev --name <algo>`
  depois de mexer no schema. Nunca edite uma migration já aplicada.
- **Tabela satélite, não coluna nova.** Precisa guardar "tentativas de
  contato via WhatsApp" pro seu módulo de convocação? Crie
  `model ConvTentativaContato` com uma FK pra `Contato` ou `Opcao` — não
  adicione `tentativasWhatsapp` em `Contato`.
- **Toda escrita passa por um serviço.** Se a tabela é do núcleo
  (`Contato`, `Opcao`, ...), a função que escreve nela já existe em
  `src/modules/perfil-contatos/servico.ts` ou
  `src/modules/alocacao/servico.ts` — use-a. Não chame
  `prisma.opcao.update(...)` de dentro de uma rota ou Server Action.

## Design / UI

Os tokens de cor e tipografia estão em `src/app/globals.css` (bloco
`@theme`) — use as classes Tailwind que eles geram (`bg-accent`,
`text-ink-2`, `border-line`, etc.), não hexadecimais soltos. Componentes
prontos em `src/core/ui/`: `Botao`, `Cartao`/`CartaoTitulo`/`CartaoCorpo`,
`Selo`/`SeloEstadoOpcao`, `Campo`/`CampoSelect`/`Rotulo`. Um módulo novo
usa esses componentes; se precisar de um componente que ainda não existe
e for genérico o bastante pra outros módulos usarem, ele vai em
`src/core/ui`, não duplicado dentro do seu módulo.

## Convenções de nomenclatura

O código é em português (identificadores, textos de UI, nomes de tabela) —
é o idioma do domínio (SME, CRE, "Selecionado", "Lista de espera") e o
idioma de quem vai usar o sistema. Mantenha consistência: `Cartao`, não
`Card`; `Botao`, não `Button`. As únicas exceções são nomes de bibliotecas
e convenções do próprio Next.js/Prisma (`page.tsx`, `schema.prisma`).
