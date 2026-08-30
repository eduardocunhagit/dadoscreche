/**
 * Simulador comparativo (Fase 6 do plano) — reprocessa a Query A real e
 * mede o tamanho do problema que a liberação em cascata e o aceite
 * condicional (Eixo 2) resolveriam.
 *
 * Não é um simulador de fila discreto (não reordena chamadas nem recalcula
 * quem seria convocado sob a regra nova) — a base não tem timestamp de
 * transição de estado (gap nº1 do briefing), então não dá pra saber QUANDO
 * cada ciclo aconteceu, só que aconteceu. O que este script faz é o que dá
 * pra provar com o dado que existe: medir, na base 2021-2025 real, quantas
 * vagas ficaram presas em ciclos de convocação que nunca tinham chance de
 * ser aceitas, e quantas famílias são o público exato do aceite
 * condicional. Ver Bases IC_ ClassificadoseFila/README_dicionario_dados.md
 * e a seção 01 do plano publicado para os números equivalentes já
 * validados em Python sobre a base inteira.
 *
 * Uso:
 *   npx tsx scripts/simulador.ts             # todos os anos (2021-2025)
 *   npx tsx scripts/simulador.ts --ano=2025   # só um processo
 */
import { createReadStream } from "node:fs";
import { createGunzip } from "node:zlib";
import path from "node:path";
import { parse } from "csv-parse";

const RAIZ_DADOS = path.resolve(__dirname, "..", "..");
const ARQUIVO_QUERY_A = path.join(RAIZ_DADOS, "Bases IC_ ClassificadoseFila", "01_QueryA_InscricoesPorAno.csv.gz");

const CANCELADO_NA_CONFIRMACAO = "Cancelado na confirmacao";
const CONFIRMADO = "Confirmado";
const LISTA_DE_ESPERA = "Lista de espera";
const SELECIONADO = "Selecionado";
const SELECIONADO_DA_LISTA = "Selecionado da lista";

interface OpcaoLinha {
  ordem: number;
  situacao: string;
}

async function main() {
  const anoFiltro = process.argv.find((a) => a.startsWith("--ano="))?.split("=")[1];
  const anoAlvo = anoFiltro ? Number(anoFiltro) : null;

  console.log(anoAlvo ? `Processando o processo de ${anoAlvo}...` : "Processando os 5 processos (2021-2025)...");

  const inscricoes = new Map<string, { ano: number; opcoes: OpcaoLinha[] }>();
  let linhasLidas = 0;
  let linhasConsideradas = 0;

  const parser = createReadStream(ARQUIVO_QUERY_A)
    .pipe(createGunzip())
    .pipe(parse({ delimiter: ";", bom: true, columns: true, skip_empty_lines: true }));

  for await (const linha of parser as AsyncIterable<Record<string, string>>) {
    linhasLidas++;
    const ano = Number(linha.ano);
    if (anoAlvo && ano !== anoAlvo) continue;
    linhasConsideradas++;

    const chave = `${linha.prm_id}-${linha.plm_id}-${linha.ipl_id}`;
    let inscricao = inscricoes.get(chave);
    if (!inscricao) {
      inscricao = { ano, opcoes: [] };
      inscricoes.set(chave, inscricao);
    }
    inscricao.opcoes.push({ ordem: Number(linha.opcao), situacao: linha.situacao });
  }

  console.log(`  ${linhasLidas} linhas lidas, ${linhasConsideradas} no escopo, ${inscricoes.size} inscrições.\n`);

  relatorio(inscricoes);
}

function relatorio(inscricoes: Map<string, { ano: number; opcoes: OpcaoLinha[] }>) {
  const total = inscricoes.size;

  // --- distribuição de opção em que a família confirma -------------------
  const opcaoDaConfirmacao = new Map<number, number>();
  let comConfirmado = 0;
  for (const { opcoes } of inscricoes.values()) {
    const confirmada = opcoes.find((o) => o.situacao === CONFIRMADO);
    if (confirmada) {
      comConfirmado++;
      opcaoDaConfirmacao.set(confirmada.ordem, (opcaoDaConfirmacao.get(confirmada.ordem) ?? 0) + 1);
    }
  }

  console.log("== Em que posição da lista de preferência a família confirma ==");
  for (const ordem of [...opcaoDaConfirmacao.keys()].sort()) {
    const n = opcaoDaConfirmacao.get(ordem)!;
    console.log(`  ${ordem}ª opção: ${n} (${pct(n, comConfirmado)})`);
  }
  const naoPrimeira = comConfirmado - (opcaoDaConfirmacao.get(1) ?? 0);
  console.log(`  → ${pct(naoPrimeira, comConfirmado)} das famílias atendidas ficam com uma opção que não é a 1ª.\n`);

  // --- regra 1: vagas presas em opções piores que a confirmada -----------
  let inscricoesComVagaPresa = 0;
  let vagasPresasTotal = 0;
  const distribuicaoVagasPresasPorInscricao = new Map<number, number>();

  for (const { opcoes } of inscricoes.values()) {
    const confirmadas = opcoes.filter((o) => o.situacao === CONFIRMADO);
    if (confirmadas.length !== 1) continue;
    const k = confirmadas[0].ordem;
    const presas = opcoes.filter((o) => o.ordem > k && o.situacao === CANCELADO_NA_CONFIRMACAO);
    if (presas.length > 0) {
      inscricoesComVagaPresa++;
      vagasPresasTotal += presas.length;
      distribuicaoVagasPresasPorInscricao.set(
        presas.length,
        (distribuicaoVagasPresasPorInscricao.get(presas.length) ?? 0) + 1
      );
    }
  }

  console.log("== Regra 1 — liberação em cascata: vagas presas sem chance de aceite ==");
  console.log(
    `  ${inscricoesComVagaPresa} inscrições confirmaram numa opção enquanto tinham opção(ões) PIOR(ES)`
  );
  console.log(`  ainda em ciclo de convocação — ${vagasPresasTotal} vagas-ciclo perdidas ao todo.`);
  for (const n of [...distribuicaoVagasPresasPorInscricao.keys()].sort()) {
    console.log(`    ${n} vaga(s) presa(s): ${distribuicaoVagasPresasPorInscricao.get(n)} inscrições`);
  }
  const diasBloqueioPorCiclo = 6; // 3 dias de contato + 3 dias úteis de comparecimento, ver briefing
  console.log(
    `  → limite superior de ${vagasPresasTotal * diasBloqueioPorCiclo} vaga-dias de rede bloqueados` +
      ` sem necessidade (${vagasPresasTotal} vagas × até ${diasBloqueioPorCiclo} dias cada).\n`
  );

  // --- regra 2: aceite condicional — público-alvo -------------------------
  let alvoCondicional = 0;
  for (const { opcoes } of inscricoes.values()) {
    const confirmadas = opcoes.filter((o) => o.situacao === CONFIRMADO);
    if (confirmadas.length !== 1) continue;
    const k = confirmadas[0].ordem;
    const melhorEmCiclo = opcoes.some((o) => o.ordem < k && o.situacao === CANCELADO_NA_CONFIRMACAO);
    if (melhorEmCiclo) alvoCondicional++;
  }

  console.log("== Regra 2 — aceite condicional: público-alvo ==");
  console.log(
    `  ${alvoCondicional} inscrições confirmaram uma opção enquanto ainda tinham uma opção MELHOR`
  );
  console.log(`  em ciclo de convocação — é quem hoje escolhe entre aceitar o pior e apostar no melhor`);
  console.log(`  sem rede de segurança.\n`);

  // --- gap: estados transitórios inconsistentes ----------------------------
  let comOfertaEEspera = 0;
  let comOferta = 0;
  for (const { opcoes } of inscricoes.values()) {
    const temOferta = opcoes.some((o) => o.situacao === SELECIONADO || o.situacao === SELECIONADO_DA_LISTA);
    if (!temOferta) continue;
    comOferta++;
    if (opcoes.some((o) => o.situacao === LISTA_DE_ESPERA)) comOfertaEEspera++;
  }
  console.log("== Gap nº2 do briefing — estados transitórios não sinalizados ==");
  console.log(`  ${comOferta} inscrições com opção Selecionada/Selecionada da lista;`);
  console.log(
    `  ${comOfertaEEspera} delas (${pct(comOfertaEEspera, comOferta)}) têm outra opção ainda em Lista de` +
      ` espera no mesmo cadastro — o painel /fila deste projeto já calcula essa lista.\n`
  );

  console.log(`Total de inscrições no escopo: ${total}`);
}

function pct(n: number, total: number) {
  return total === 0 ? "0,0%" : `${((100 * n) / total).toFixed(1)}%`;
}

main().catch((erro) => {
  console.error(erro);
  process.exit(1);
});
