/**
 * Importa a previsão de demanda da frente 2 (PR #9 — Eduardo) e grava a
 * métrica de DEMANDA EXCEDENTE por unidade em InscDemandaPrevista, fonte
 * "modelo_f2" — a fonte que listarUnidadesComGeoEDemanda prefere sobre o
 * placeholder "classe_pressao_2025". Rodar depois de db:seed e db:geo:
 *
 *   npm run db:demanda
 *
 * Fonte: frente2/06_resultados/arquivos_gerados/gap_demanda_efetiva_2026.csv
 * (uma linha por unidade; previsão do modelo para o ano letivo de 2026).
 * A métrica pedida pela SME na tela de escolha:
 *
 *   excedente = planning_gap / matriculas_2025_proxy_capacidade
 *             = (demanda efetiva prevista − oferta do ano anterior) / oferta
 *
 * Classificação (cortes sobre a distribuição real de 2026 — mediana −0,08,
 * 44,5% das unidades com gap positivo → 55% BAIXA / 22% MEDIA / 22% ALTA):
 *   excedente <= 0     -> BAIXA (a oferta do ano anterior cobre a demanda prevista)
 *   0 < excedente<=0,5 -> MEDIA (demanda até 50% acima da oferta)
 *   excedente > 0,5    -> ALTA  (demanda mais de 50% acima da oferta)
 *   oferta = 0 e demanda prevista > 0 -> ALTA com valor nulo (excedente indefinido)
 *
 * Idempotente (upsert por [unidade, ano, fonte]).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "csv-parse/sync";
import { prisma } from "../src/core/db/client";

const RAIZ_DADOS = path.resolve(__dirname, "..", "..");
// Pasta renomeada de "frente2" para "pipeline_demanda" no PR #11.
const ARQUIVO_GAP = path.join(
  RAIZ_DADOS,
  "pipeline_demanda",
  "06_resultados",
  "arquivos_gerados",
  "gap_demanda_efetiva_2026.csv"
);

const FONTE = "modelo_f2";
const CORTE_MEDIA = 0; // acima disso deixa de ser BAIXA
const CORTE_ALTA = 0.5; // acima disso vira ALTA

interface LinhaGap {
  ano: string;
  unidade: string;
  nome_unidade_norm: string;
  demanda_efetiva_prevista: string;
  matriculas_2025_proxy_capacidade: string;
  planning_gap: string;
}

function classificar(excedente: number): "ALTA" | "MEDIA" | "BAIXA" {
  if (excedente > CORTE_ALTA) return "ALTA";
  if (excedente > CORTE_MEDIA) return "MEDIA";
  return "BAIXA";
}

async function main() {
  const linhas = parse(readFileSync(ARQUIVO_GAP), {
    bom: true,
    columns: true,
    skip_empty_lines: true,
  }) as LinhaGap[];
  console.log(`${linhas.length} unidades no CSV de previsão.`);

  // Join com Unidade por código normalizado (mesma regra do importar-geo:
  // os escCodigo do banco podem ter zeros à esquerda).
  const unidades = await prisma.unidade.findMany({ select: { escCodigo: true } });
  const porCodigoNormalizado = new Map(unidades.map((u) => [u.escCodigo.replace(/^0+/, ""), u.escCodigo]));

  let gravadas = 0;
  let semUnidade = 0;
  let semDado = 0;
  const porClasse = { ALTA: 0, MEDIA: 0, BAIXA: 0 };

  for (const l of linhas) {
    const ano = Number(l.ano);
    const escCodigo = porCodigoNormalizado.get(l.unidade.trim().replace(/^0+/, ""));
    if (!escCodigo) {
      semUnidade++;
      continue;
    }

    const oferta = Number(l.matriculas_2025_proxy_capacidade) || 0;
    const demanda = Number(l.demanda_efetiva_prevista) || 0;
    const gap = Number(l.planning_gap) || demanda - oferta;

    let classe: "ALTA" | "MEDIA" | "BAIXA";
    let valor: number | null;
    if (oferta > 0) {
      valor = gap / oferta;
      classe = classificar(valor);
    } else if (demanda > 0) {
      // Demanda prevista sem matrícula-proxy no ano anterior: excedente
      // indefinido, mas certamente não coberto — ALTA sem valor numérico.
      valor = null;
      classe = "ALTA";
    } else {
      semDado++;
      continue;
    }

    await prisma.inscDemandaPrevista.upsert({
      where: { unidadeEscCodigo_ano_fonte: { unidadeEscCodigo: escCodigo, ano, fonte: FONTE } },
      create: { unidadeEscCodigo: escCodigo, ano, fonte: FONTE, classe, valor },
      update: { classe, valor },
    });
    porClasse[classe]++;
    gravadas++;
  }

  console.log(
    `${gravadas} unidades gravadas (fonte ${FONTE}, ano da previsão 2026): ` +
      `${porClasse.ALTA} ALTA, ${porClasse.MEDIA} MEDIA, ${porClasse.BAIXA} BAIXA.`
  );
  if (semUnidade > 0) console.log(`${semUnidade} códigos do CSV sem Unidade correspondente no banco (ignorados).`);
  if (semDado > 0) console.log(`${semDado} unidades sem demanda nem oferta (ignoradas).`);
}

main()
  .then(() => process.exit(0))
  .catch((erro) => {
    console.error(erro);
    process.exit(1);
  });
