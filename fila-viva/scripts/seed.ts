/**
 * Seed de desenvolvimento — importa dados REAIS das bases do desafio
 * (Query A, C, D) e complementa com contatos e contas de demonstração
 * SINTÉTICOS, já que a extração anonimizada não expõe nenhum campo de
 * contato (ver README.md da raiz, seção "O que dá para popular de
 * verdade").
 *
 * Para manter o seed rápido de rodar durante o desenvolvimento, a Query A
 * é importada só para o processo de 2025, polos 1 e 2 (18.592 linhas de
 * ~837 mil). Ampliar o filtro abaixo (`ANO_SEED` / `POLOS_SEED`) importa
 * mais dados reais sem mudar nenhuma outra parte do script.
 *
 * A Query B (respostas socioeconômicas) NÃO é importada nesta primeira
 * versão — nada nas Fases 0-2 e no motor de alocação depende dela. Fica
 * para quem construir a Fase 3 (fluxo de inscrição e pontuação).
 */
import { createReadStream } from "node:fs";
import { createGunzip } from "node:zlib";
import path from "node:path";
import { parse } from "csv-parse/sync";
import bcrypt from "bcryptjs";
import { prisma } from "../src/core/db/client";
import { SITUACAO_ORIGINAL_PARA_ESTADO, type EstadoOpcao } from "../src/core/domain/constants";

const RAIZ_DADOS = path.resolve(__dirname, "..", "..");
const PASTA_IC = path.join(RAIZ_DADOS, "Bases IC_ ClassificadoseFila");

const ANO_SEED = 2025;
const POLOS_SEED = [1, 2];

const PROCESSOS = [
  { ano: 2021, prmId: 179 },
  { ano: 2022, prmId: 181 },
  { ano: 2023, prmId: 184 },
  { ano: 2024, prmId: 194 },
  { ano: 2025, prmId: 195 },
];

async function main() {
  console.log("Limpando banco de dev...");
  await limparBanco();

  console.log("Importando unidades escolares (Query D)...");
  const totalUnidades = await importarUnidades();
  console.log(`  ${totalUnidades} unidades.`);

  console.log("Criando as 11 CREs (polos)...");
  const polos = await criarPolos();

  console.log("Criando os 5 processos seletivos...");
  const processos = await criarProcessos();

  console.log("Importando o questionário e a régua de pontuação (Query C)...");
  const totalPerguntas = await importarPerguntas(processos);
  console.log(`  ${totalPerguntas} perguntas.`);

  console.log(`Importando inscrições reais — ano ${ANO_SEED}, polos ${POLOS_SEED.join(", ")} (Query A)...`);
  const resumo = await importarInscricoes(processos, polos);
  console.log(
    `  ${resumo.inscricoes} inscrições, ${resumo.opcoes} opções, ${resumo.criancas} crianças, ${resumo.responsaveis} responsáveis.`
  );

  console.log("Semeando contatos de demonstração (sintéticos — ver aviso no topo deste arquivo)...");
  const totalContatos = await semearContatos();
  console.log(`  ${totalContatos} contatos.`);

  console.log("Criando contas de demonstração...");
  await criarContas(polos);

  console.log("\nPronto. Contas de demonstração (senha: demo1234):");
  console.log("  gestor@filaviva.rio        — Gestor SME, vê tudo");
  console.log("  cre1@filaviva.rio          — Servidor da CRE 1");
  console.log("  unidade@filaviva.rio       — Servidor de uma unidade específica");
  console.log("  responsavel@filaviva.rio   — Responsável com crianças reais vinculadas");
}

async function limparBanco() {
  await prisma.ofertaEvento.deleteMany();
  await prisma.opcao.deleteMany();
  await prisma.resposta.deleteMany();
  await prisma.inscricao.deleteMany();
  await prisma.contatoHistorico.deleteMany();
  await prisma.contato.deleteMany();
  await prisma.crianca.deleteMany();
  await prisma.usuario.deleteMany();
  await prisma.responsavel.deleteMany();
  await prisma.pergunta.deleteMany();
  await prisma.processo.deleteMany();
  await prisma.vaga.deleteMany();
  await prisma.unidade.deleteMany();
  await prisma.polo.deleteMany();
}

// Códigos de tipo de gestão inferidos por cardinalidade batendo com o
// briefing ("855 diretas, 10 conveniadas, 7 em parceria") — a Query D não
// traz um legenda textual para esta coluna.
const TIPO_GESTAO_POR_CODIGO: Record<string, string> = {
  "1": "DIRETA",
  "3": "CONVENIADA",
  "4": "PARCERIA",
};

async function importarUnidades() {
  const linhas = await lerCsv(path.join(PASTA_IC, "04_UnidadesEscolaresComEndereco.csv"), false);
  const dados = linhas
    .filter((l) => l[1] && l[1] !== "NULL")
    .map((l) => ({
      escCodigo: l[1],
      nome: l[2],
      tipoGestao: TIPO_GESTAO_POR_CODIGO[l[3]] ?? "DIRETA",
      logradouro: nulo(l[4]),
      numero: nulo(l[5]),
      complemento: nulo(l[6]),
      bairro: nulo(l[7]),
      cep: nulo(l[8]),
    }));

  // esc_codigo pode se repetir na origem (duplicidade conhecida do cadastro
  // da rede) — mantém a primeira ocorrência.
  const vistos = new Set<string>();
  const unicos = dados.filter((d) => (vistos.has(d.escCodigo) ? false : (vistos.add(d.escCodigo), true)));

  await prisma.unidade.createMany({ data: unicos });
  return unicos.length;
}

async function criarPolos() {
  const polos = new Map<number, string>();
  for (let plmId = 1; plmId <= 11; plmId++) {
    const polo = await prisma.polo.create({ data: { plmId, nome: `CRE ${plmId}` } });
    polos.set(plmId, polo.id);
  }
  return polos;
}

async function criarProcessos() {
  const processos = new Map<number, { id: string; ativarMotor: boolean }>();
  for (const p of PROCESSOS) {
    const ativarMotor = p.ano === ANO_SEED;
    const processo = await prisma.processo.create({
      data: {
        ano: p.ano,
        prmId: p.prmId,
        nome: `Inscrição Creche ${p.ano}`,
        // Liga as duas regras do motor por padrão só no processo mais
        // recente, pra quem entrar no painel já ver a diferença — dá pra
        // desligar em /fila (só o Gestor SME muda essa flag).
        liberacaoEmCascata: ativarMotor,
        aceiteCondicional: ativarMotor,
      },
    });
    processos.set(p.ano, { id: processo.id, ativarMotor });
  }
  return processos;
}

async function importarPerguntas(processos: Map<number, { id: string }>) {
  const linhas = await lerCsv<Record<string, string>>(
    path.join(PASTA_IC, "03_QueryC_PerguntasComDescricao.csv"),
    true
  );
  let total = 0;
  for (const l of linhas) {
    const ano = Number(l.ano);
    const processo = processos.get(ano);
    if (!processo) continue;
    await prisma.pergunta.create({
      data: {
        processoId: processo.id,
        ichPergId: Number(l.ich_perg_id),
        pergId: Number(l.perg_id),
        texto: l.pergunta_texto,
        ordemVisualizacao: Number(l.perg_ordemVisualizacao),
        pontuacao: Number(l.perg_pontuacao),
        criterioDesempate: l.perg_criterio === "Sim",
      },
    });
    total++;
  }
  return total;
}

async function importarInscricoes(processos: Map<number, { id: string; ativarMotor: boolean }>, polos: Map<number, string>) {
  const processo2025 = processos.get(ANO_SEED)!;

  const criancaPorAnon = new Map<string, string>();
  const responsavelPorAnon = new Map<string, string>();
  const inscricaoPorChave = new Map<string, string>();

  let opcoesImportadas = 0;
  const unidadesConhecidas = new Set((await prisma.unidade.findMany({ select: { escCodigo: true } })).map((u) => u.escCodigo));

  await paraCadaLinhaCsvGz(
    path.join(PASTA_IC, "01_QueryA_InscricoesPorAno.csv.gz"),
    async (l) => {
      const ano = Number(l.ano);
      const plmId = Number(l.plm_id);
      if (ano !== ANO_SEED || !POLOS_SEED.includes(plmId)) return;
      if (!unidadesConhecidas.has(l.unidade)) return; // proteção — todas deveriam casar

      let criancaId = criancaPorAnon.get(l.aluno_anon);
      if (!criancaId) {
        const c = await prisma.crianca.create({
          data: {
            alunoAnon: l.aluno_anon,
            nomeExibicao: `Criança ${l.aluno_anon.replace("aluno_", "")}`,
            sexo: l.sexo_crianca,
            nascimentoAnoMes: l.nascimento_aluno_anomes,
            responsavelPrincipalId: await obterOuCriarResponsavel(l.responsavel_anon, responsavelPorAnon),
          },
        });
        criancaId = c.id;
        criancaPorAnon.set(l.aluno_anon, criancaId);
      }

      const chaveInscricao = `${l.prm_id}-${l.plm_id}-${l.ipl_id}`;
      let inscricaoId = inscricaoPorChave.get(chaveInscricao);
      if (!inscricaoId) {
        // Não confia que o responsável já foi criado junto com a criança:
        // a base real tem casos de reinscrição em que o mesmo aluno_anon
        // aparece sob um ipl_id novo, às vezes com responsavel_anon
        // diferente — obterOuCriarResponsavel é idempotente, então chamar
        // de novo aqui é seguro e barato (cache em memória).
        const responsavelId = await obterOuCriarResponsavel(l.responsavel_anon, responsavelPorAnon);
        const inscricao = await prisma.inscricao.create({
          data: {
            processoId: processo2025.id,
            poloId: polos.get(plmId)!,
            iplId: Number(l.ipl_id),
            criancaId,
            responsavelId,
            dataCriacao: new Date(l.data_criacao),
            cepResponsavel: nulo(l.CEP),
            bairroResponsavel: nulo(l.bairro),
          },
        });
        inscricaoId = inscricao.id;
        inscricaoPorChave.set(chaveInscricao, inscricaoId);
      }

      const estado = (SITUACAO_ORIGINAL_PARA_ESTADO[l.situacao] ?? "NA_FILA") as EstadoOpcao;
      const emCiclo = estado === "OFERTADA";
      // A extração histórica não guarda QUANDO uma opção mudou de estado
      // (é o gap nº1 do briefing). Pra opções que já chegaram ofertadas na
      // importação, sintetiza um instante recente só pra o painel /fila
      // ter algo pra mostrar — deixa isso claro no evento abaixo.
      const ofertaAbertaEm = emCiclo ? diasAtras(Math.floor(Math.random() * 6)) : null;

      const opcao = await prisma.opcao.create({
        data: {
          inscricaoId,
          ordem: Number(l.opcao),
          unidadeEscCodigo: l.unidade,
          grupamento: l.grupamento.trim(),
          turno: l.horario,
          estado,
          situacaoOriginal: l.situacao,
          ofertaAbertaEm,
          ofertaPrazo: ofertaAbertaEm ? new Date(ofertaAbertaEm.getTime() + 6 * 24 * 60 * 60 * 1000) : null,
        },
      });

      await prisma.ofertaEvento.create({
        data: {
          opcaoId: opcao.id,
          estadoAnterior: "NA_FILA",
          estadoNovo: estado,
          autorPapel: "SISTEMA",
          observacao: "Estado inicial importado da extração 2021-2025 (sem histórico real de transição).",
          quando: ofertaAbertaEm ?? new Date(l.data_criacao),
        },
      });

      opcoesImportadas++;
    }
  );

  return {
    inscricoes: inscricaoPorChave.size,
    opcoes: opcoesImportadas,
    criancas: criancaPorAnon.size,
    responsaveis: responsavelPorAnon.size,
  };
}

async function obterOuCriarResponsavel(anon: string, cache: Map<string, string>): Promise<string> {
  const existente = cache.get(anon);
  if (existente) return existente;
  const r = await prisma.responsavel.create({
    data: { responsavelAnon: anon, nomeExibicao: `Responsável ${anon.replace("responsavel_", "")}` },
  });
  cache.set(anon, r.id);
  return r.id;
}

// ---------------------------------------------------------------------------
// Contatos sintéticos — a base real não tem NENHUM campo de contato.
// ---------------------------------------------------------------------------

function telefoneFalsoDeterministico(semente: string, sufixo = 0) {
  const digitos = semente.replace(/\D/g, "").padStart(4, "0").slice(-4);
  const n = (Number(digitos) + sufixo) % 10000;
  return `(21) 9${String(7000 + n).padStart(4, "0")}-${String(n).padStart(4, "0")}`;
}

async function semearContatos() {
  const criancas = await prisma.crianca.findMany({ select: { id: true, alunoAnon: true } });
  let total = 0;

  for (let i = 0; i < criancas.length; i++) {
    const c = criancas[i];

    await prisma.contato.create({
      data: {
        criancaId: c.id,
        papel: "RESPONSAVEL",
        canal: "WHATSAPP",
        valor: telefoneFalsoDeterministico(c.alunoAnon),
        ordemTentativa: 1,
        verificadoEm: i % 3 === 0 ? diasAtras(10) : null,
      },
    });
    total++;

    // Cerca de 60% ganham contato alternativo — o resto fica em estados
    // variados (declarado "sem contato" ou simplesmente pendente) para a
    // tela de perfil mostrar todos os casos reais de uso.
    if (i % 5 < 3) {
      await prisma.contato.create({
        data: {
          criancaId: c.id,
          papel: "ALTERNATIVO",
          nomeContato: ["Avó", "Tio", "Vizinha", "Madrinha"][i % 4],
          parentesco: ["Avó", "Tio", "Vizinha", "Madrinha"][i % 4],
          canal: "TELEFONE",
          valor: telefoneFalsoDeterministico(c.alunoAnon, 17),
          ordemTentativa: 2,
          consentimentoEm: diasAtras(30),
          verificadoEm: i % 4 === 0 ? diasAtras(200) : null, // alguns vencidos, pra fila de revalidação
        },
      });
      total++;
    } else if (i % 5 === 4) {
      await prisma.crianca.update({
        where: { id: c.id },
        data: { semContatoAlternativoDeclarado: true, semContatoAlternativoDeclaradoEm: diasAtras(5) },
      });
    }
  }

  return total;
}

async function criarContas(polos: Map<number, string>) {
  const senhaHash = await bcrypt.hash("demo1234", 10);

  await prisma.usuario.create({
    data: {
      email: "gestor@filaviva.rio",
      senhaHash,
      papel: "GESTOR_SME",
      nomeExibicao: "Gestora SME (demo)",
    },
  });

  await prisma.usuario.create({
    data: {
      email: "cre1@filaviva.rio",
      senhaHash,
      papel: "SERVIDOR_CRE",
      nomeExibicao: "Servidor CRE 1 (demo)",
      poloId: polos.get(1)!,
    },
  });

  const primeiraOpcao = await prisma.opcao.findFirst({ select: { unidadeEscCodigo: true } });
  if (primeiraOpcao) {
    await prisma.usuario.create({
      data: {
        email: "unidade@filaviva.rio",
        senhaHash,
        papel: "SERVIDOR_UNIDADE",
        nomeExibicao: "Servidor de unidade (demo)",
        unidadeEscCodigo: primeiraOpcao.unidadeEscCodigo,
      },
    });
  }

  // Escolhe um responsável com mais de uma criança pra "Meus filhos" mostrar
  // uma lista de verdade, não um caso degenerado de filho único.
  const responsaveisComVarios = await prisma.responsavel.findMany({
    where: { criancas: { some: {} } },
    include: { _count: { select: { criancas: true } } },
    orderBy: { criancas: { _count: "desc" } },
    take: 1,
  });
  const responsavelDemo = responsaveisComVarios[0];
  if (responsavelDemo) {
    await prisma.usuario.create({
      data: {
        email: "responsavel@filaviva.rio",
        senhaHash,
        papel: "RESPONSAVEL",
        nomeExibicao: responsavelDemo.nomeExibicao,
        responsavelId: responsavelDemo.id,
      },
    });
  }
}

// ---------------------------------------------------------------------------
// Utilidades de leitura de CSV
// ---------------------------------------------------------------------------

function nulo(v: string | undefined) {
  return !v || v === "NULL" ? null : v;
}

function diasAtras(dias: number) {
  return new Date(Date.now() - dias * 24 * 60 * 60 * 1000);
}

async function lerCsv<T = string[]>(caminho: string, comCabecalho: boolean): Promise<T[]> {
  const fs = await import("node:fs/promises");
  const texto = await fs.readFile(caminho, "utf-8");
  return parse(texto, {
    delimiter: ";",
    bom: true,
    columns: comCabecalho,
    skip_empty_lines: true,
  }) as T[];
}

async function paraCadaLinhaCsvGz(caminho: string, callback: (linha: Record<string, string>) => Promise<void>) {
  // Um único parser em modo stream (não um parse() novo por linha) — é a
  // diferença entre isto rodar em ~1 minuto ou em dezenas de minutos nas
  // 837 mil linhas da Query A.
  const { parse: parseStream } = await import("csv-parse");
  const parser = createReadStream(caminho)
    .pipe(createGunzip())
    .pipe(parseStream({ delimiter: ";", bom: true, columns: true, skip_empty_lines: true }));

  let lidas = 0;
  for await (const linha of parser as AsyncIterable<Record<string, string>>) {
    lidas++;
    if (lidas % 100_000 === 0) console.log(`  ...${lidas} linhas lidas`);
    await callback(linha);
  }
}

main()
  .then(() => process.exit(0))
  .catch((erro) => {
    console.error(erro);
    process.exit(1);
  });
