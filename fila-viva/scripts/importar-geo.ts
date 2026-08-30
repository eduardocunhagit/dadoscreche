/**
 * Importa geocodificação e demanda prevista das unidades a partir de
 * prisma/dados/creches_2025.csv (geocodificação do Pedro, branch pedro).
 *
 * Idempotente — pode ser rodado quantas vezes for preciso (upserts em
 * chaves únicas). Ver EXTENDING.md e os models InscUnidadeGeo /
 * InscDemandaPrevista em prisma/schema.prisma.
 *
 * Passos:
 *   1. Lê o CSV e casa cada linha com uma Unidade do banco por escCodigo,
 *      normalizando zeros à esquerda dos dois lados (o banco pode ter
 *      escCodigo com zero à esquerda, o CSV não necessariamente).
 *   2. Para linhas com latitude/longitude preenchidas: upsert
 *      InscUnidadeGeo (origem CSV_PEDRO).
 *   3. Para linhas com classe_pressao_fila reconhecida: upsert
 *      InscDemandaPrevista (ano 2025, fonte classe_pressao_2025).
 *   4. Para unidades que ainda ficaram sem geo: tenta um centroide por
 *      bairro (média das unidades já geocodificadas no mesmo bairro
 *      normalizado) — upsert InscUnidadeGeo (origem CENTROIDE_BAIRRO).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "csv-parse/sync";
import { prisma } from "../src/core/db/client";

const CAMINHO_CSV = path.resolve(__dirname, "..", "prisma", "dados", "creches_2025.csv");

const ANO_DEMANDA = 2025;
const FONTE_DEMANDA = "classe_pressao_2025";

const CLASSE_POR_ROTULO: Record<string, string> = {
  "Até 25 por 100 matriculados": "BAIXA",
  "Sem fila observada": "BAIXA",
  "25 a 75 por 100 matriculados": "MEDIA",
  "Mais de 75 por 100 matriculados": "ALTA",
};

type LinhaCsv = {
  codigo: string;
  cre: string;
  bairro: string;
  latitude: string;
  longitude: string;
  classe_pressao_fila: string;
};

async function main() {
  console.log(`Lendo ${CAMINHO_CSV}...`);
  const linhas = lerCsv();
  console.log(`  ${linhas.length} linhas no CSV.`);

  const unidades = await prisma.unidade.findMany({ select: { escCodigo: true, bairro: true } });
  const escCodigoPorNormalizado = new Map<string, string>();
  for (const u of unidades) {
    escCodigoPorNormalizado.set(normalizarCodigo(u.escCodigo), u.escCodigo);
  }
  console.log(`  ${unidades.length} unidades no banco.`);

  let totalGeoCsv = 0;
  let totalDemanda = 0;
  let codigosNaoCasados = 0;

  for (const linha of linhas) {
    const codigoNormalizado = normalizarCodigo(String(linha.codigo ?? "").trim());
    const escCodigo = escCodigoPorNormalizado.get(codigoNormalizado);
    if (!escCodigo) {
      codigosNaoCasados++;
      continue;
    }

    if (naoVazio(linha.latitude) && naoVazio(linha.longitude)) {
      const cre = naoVazio(linha.cre) ? Math.trunc(Number(linha.cre)) : null;
      await prisma.inscUnidadeGeo.upsert({
        where: { unidadeEscCodigo: escCodigo },
        create: {
          unidadeEscCodigo: escCodigo,
          latitude: Number(linha.latitude),
          longitude: Number(linha.longitude),
          plmId: cre,
          origem: "CSV_PEDRO",
        },
        update: {
          latitude: Number(linha.latitude),
          longitude: Number(linha.longitude),
          plmId: cre,
          origem: "CSV_PEDRO",
        },
      });
      totalGeoCsv++;
    }

    const classe = CLASSE_POR_ROTULO[String(linha.classe_pressao_fila ?? "").trim()];
    if (classe) {
      await prisma.inscDemandaPrevista.upsert({
        where: {
          unidadeEscCodigo_ano_fonte: {
            unidadeEscCodigo: escCodigo,
            ano: ANO_DEMANDA,
            fonte: FONTE_DEMANDA,
          },
        },
        create: {
          unidadeEscCodigo: escCodigo,
          ano: ANO_DEMANDA,
          fonte: FONTE_DEMANDA,
          classe,
        },
        update: {
          classe,
        },
      });
      totalDemanda++;
    }
  }

  console.log(`  ${totalGeoCsv} geo (CSV_PEDRO), ${totalDemanda} demanda prevista, ${codigosNaoCasados} códigos não casados.`);

  console.log("Preenchendo centroides por bairro para unidades sem geo...");
  const totalCentroides = await preencherCentroidesPorBairro();
  console.log(`  ${totalCentroides} geo (CENTROIDE_BAIRRO).`);

  const contagens = await prisma.inscUnidadeGeo.groupBy({
    by: ["origem"],
    _count: { origem: true },
  });

  console.log("\nResumo final:");
  for (const c of contagens) {
    console.log(`  ${c.origem}: ${c._count.origem}`);
  }
  console.log(`  códigos do CSV não casados com nenhuma Unidade: ${codigosNaoCasados}`);
}

async function preencherCentroidesPorBairro(): Promise<number> {
  const geosCsvPedro = await prisma.inscUnidadeGeo.findMany({
    where: { origem: "CSV_PEDRO" },
    select: { latitude: true, longitude: true, unidade: { select: { bairro: true } } },
  });

  const somaPorBairro = new Map<string, { somaLat: number; somaLon: number; total: number }>();
  for (const g of geosCsvPedro) {
    const bairroNormalizado = normalizarBairro(g.unidade.bairro);
    if (!bairroNormalizado) continue;
    const acumulado = somaPorBairro.get(bairroNormalizado) ?? { somaLat: 0, somaLon: 0, total: 0 };
    acumulado.somaLat += g.latitude;
    acumulado.somaLon += g.longitude;
    acumulado.total += 1;
    somaPorBairro.set(bairroNormalizado, acumulado);
  }

  const centroidePorBairro = new Map<string, { latitude: number; longitude: number }>();
  for (const [bairro, acumulado] of somaPorBairro) {
    centroidePorBairro.set(bairro, {
      latitude: acumulado.somaLat / acumulado.total,
      longitude: acumulado.somaLon / acumulado.total,
    });
  }

  const unidadesComGeo = new Set(
    (await prisma.inscUnidadeGeo.findMany({ select: { unidadeEscCodigo: true } })).map((g) => g.unidadeEscCodigo)
  );

  const todasUnidades = await prisma.unidade.findMany({ select: { escCodigo: true, bairro: true } });

  let total = 0;
  for (const u of todasUnidades) {
    if (unidadesComGeo.has(u.escCodigo)) continue;
    const bairroNormalizado = normalizarBairro(u.bairro);
    if (!bairroNormalizado) continue;
    const centroide = centroidePorBairro.get(bairroNormalizado);
    if (!centroide) continue;

    await prisma.inscUnidadeGeo.upsert({
      where: { unidadeEscCodigo: u.escCodigo },
      create: {
        unidadeEscCodigo: u.escCodigo,
        latitude: centroide.latitude,
        longitude: centroide.longitude,
        plmId: null,
        origem: "CENTROIDE_BAIRRO",
      },
      update: {
        latitude: centroide.latitude,
        longitude: centroide.longitude,
        plmId: null,
        origem: "CENTROIDE_BAIRRO",
      },
    });
    unidadesComGeo.add(u.escCodigo);
    total++;
  }

  return total;
}

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

function normalizarCodigo(codigo: string): string {
  return codigo.replace(/^0+/, "");
}

function normalizarBairro(bairro: string | null): string {
  if (!bairro) return "";
  return bairro
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .trim()
    .replace(/\s+/g, " ");
}

function naoVazio(v: string | undefined | null): boolean {
  return v !== undefined && v !== null && v.trim() !== "";
}

function lerCsv(): LinhaCsv[] {
  const texto = readFileSync(CAMINHO_CSV);
  return parse(texto, {
    bom: true,
    columns: true,
    skip_empty_lines: true,
  }) as LinhaCsv[];
}

main()
  .then(() => process.exit(0))
  .catch((erro) => {
    console.error(erro);
    process.exit(1);
  });
