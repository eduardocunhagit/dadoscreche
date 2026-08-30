import { prisma } from "@/core/db/client";
import { barramento } from "@/core/events/bus";
import {
  planejarCascata,
  transicionar,
  type EventoGatilho,
  type EventoOpcao,
  type OpcaoDaFila,
} from "@/core/domain/motor";
import type { EstadoOpcao } from "@/core/domain/constants";

// Fronteira do módulo: toda mudança de estado de uma Opcao passa por
// `aplicarEvento`. Ela nunca chama prisma.opcao.update diretamente fora
// daqui — é isso que garante que OfertaEvento nunca fica sem uma linha
// correspondente. Ver src/core/domain/motor.ts para as regras em si.

export interface AutorEvento {
  usuarioId?: string;
  papel: "SISTEMA" | "RESPONSAVEL" | "SERVIDOR_UNIDADE" | "SERVIDOR_CRE" | "GESTOR_SME";
  canal?: string;
  observacao?: string;
}

const PRAZO_DIAS_OFERTA = 6; // 3 dias de contato + 3 dias úteis de comparecimento, ver briefing

export interface EscopoUsuario {
  papel: string;
  poloId?: string | null;
  unidadeEscCodigo?: string | null;
}

/** true se `user` pode agir sobre esta opção — mesma lógica de escopo do módulo de contatos. */
export async function opcaoNoEscopoDoUsuario(opcaoId: string, user: EscopoUsuario) {
  if (user.papel === "GESTOR_SME") return true;

  if (user.papel === "SERVIDOR_UNIDADE" && user.unidadeEscCodigo) {
    const n = await prisma.opcao.count({ where: { id: opcaoId, unidadeEscCodigo: user.unidadeEscCodigo } });
    return n > 0;
  }

  if (user.papel === "SERVIDOR_CRE" && user.poloId) {
    const n = await prisma.opcao.count({ where: { id: opcaoId, inscricao: { poloId: user.poloId } } });
    return n > 0;
  }

  return false;
}

export async function aplicarEvento(opcaoId: string, evento: EventoGatilho, autor: AutorEvento) {
  const opcaoAlvo = await prisma.opcao.findUniqueOrThrow({ where: { id: opcaoId } });
  const irmas = await prisma.opcao.findMany({ where: { inscricaoId: opcaoAlvo.inscricaoId } });
  const processo = await prisma.processo.findFirstOrThrow({
    where: { inscricoes: { some: { id: opcaoAlvo.inscricaoId } } },
  });

  const opcoesParaCascata: OpcaoDaFila[] = irmas.map((o) => ({
    id: o.id,
    ordem: o.ordem,
    estado: o.estado as OpcaoDaFila["estado"],
  }));

  const acoes = planejarCascata(opcoesParaCascata, opcaoId, evento, {
    liberacaoEmCascata: processo.liberacaoEmCascata,
    aceiteCondicional: processo.aceiteCondicional,
  });

  const resultado = await prisma.$transaction(async (tx) => {
    const alterada = await aplicarUmaTransicao(
      tx,
      opcaoAlvo.id,
      opcaoAlvo.estado as EstadoOpcao,
      evento,
      autor
    );
    for (const acao of acoes) {
      const irma = irmas.find((o) => o.id === acao.opcaoId)!;
      await aplicarUmaTransicao(tx, irma.id, irma.estado as EstadoOpcao, acao.evento, {
        ...autor,
        observacao: `cascata a partir de ${opcaoAlvo.id}`,
      });
    }
    return alterada;
  });

  await emitirEventoDoBarramento(evento, opcaoAlvo.id, opcaoAlvo.inscricaoId);
  return resultado;
}

async function aplicarUmaTransicao(
  tx: Parameters<Parameters<typeof prisma.$transaction>[0]>[0],
  opcaoId: string,
  estadoAnterior: EstadoOpcao,
  evento: EventoOpcao,
  autor: AutorEvento
) {
  const estadoNovo = transicionar(estadoAnterior, evento);

  const dados: Record<string, unknown> = { estado: estadoNovo };
  if (evento === "OFERTAR") {
    dados.ofertaAbertaEm = new Date();
    dados.ofertaPrazo = new Date(Date.now() + PRAZO_DIAS_OFERTA * 24 * 60 * 60 * 1000);
  }

  const atualizada = await tx.opcao.update({ where: { id: opcaoId }, data: dados });

  await tx.ofertaEvento.create({
    data: {
      opcaoId,
      estadoAnterior,
      estadoNovo,
      autorUsuarioId: autor.usuarioId,
      autorPapel: autor.papel,
      canal: autor.canal,
      observacao: autor.observacao,
    },
  });

  return atualizada;
}

async function emitirEventoDoBarramento(evento: EventoGatilho, opcaoId: string, inscricaoId: string) {
  switch (evento) {
    case "OFERTAR": {
      const opcao = await prisma.opcao.findUniqueOrThrow({ where: { id: opcaoId } });
      await barramento.emit("oferta.criada", { opcaoId, inscricaoId, prazo: opcao.ofertaPrazo! });
      return;
    }
    case "ACEITAR_DEFINITIVO":
      return barramento.emit("oferta.aceita_definitiva", { opcaoId, inscricaoId });
    case "ACEITAR_CONDICIONAL":
      return barramento.emit("oferta.aceita_condicional", { opcaoId, inscricaoId });
    case "RECUSAR":
      return barramento.emit("oferta.recusada", { opcaoId, inscricaoId });
    case "EXPIRAR":
      return barramento.emit("oferta.expirada", { opcaoId, inscricaoId });
  }
}

/** Opções cuja oferta está aberta há mais tempo primeiro — a fila de trabalho do painel da CRE. */
export async function ofertasEmAberto(opts: { poloId?: string; unidadeEscCodigo?: string }) {
  return prisma.opcao.findMany({
    where: {
      estado: "OFERTADA",
      unidadeEscCodigo: opts.unidadeEscCodigo,
      inscricao: opts.poloId ? { poloId: opts.poloId } : undefined,
    },
    include: {
      unidade: true,
      inscricao: { include: { crianca: true, responsavel: true } },
    },
    orderBy: { ofertaAbertaEm: "asc" },
  });
}

/** Cadastros com uma opção "Selecionada" e outra ainda "Na fila" — o gap nº2 do briefing. */
export async function inconsistenciasDeEstado() {
  const inscricoesComOferta = await prisma.inscricao.findMany({
    where: { opcoes: { some: { estado: "OFERTADA" } } },
    include: { opcoes: true, crianca: true },
  });
  return inscricoesComOferta.filter((i) => i.opcoes.some((o) => o.estado === "NA_FILA"));
}

// ---------------------------------------------------------------------------
// Inscrição — onde a família escolhe as creches (Fase 3 do plano)
// ---------------------------------------------------------------------------

/** As 11 CREs, pra popular o seletor de polo do formulário de inscrição. */
export async function listarPolos() {
  return prisma.polo.findMany({ orderBy: { plmId: "asc" } });
}

/** O processo mais recente — o que está "com inscrição aberta" nesta demo. */
export async function processoVigente() {
  return prisma.processo.findFirstOrThrow({ orderBy: { ano: "desc" } });
}

/** Busca por nome ou bairro pro seletor de unidades — sem isso ninguém acha uma escola entre 2 mil. */
export async function buscarUnidades(termo: string) {
  const q = termo.trim();
  if (q.length < 2) return [];
  return prisma.unidade.findMany({
    where: {
      OR: [
        { nome: { contains: q } },
        { bairro: { contains: q } },
        { escCodigo: { contains: q } },
      ],
    },
    orderBy: { nome: "asc" },
    take: 20,
  });
}

export interface EscolhaOpcao {
  unidadeEscCodigo: string;
  grupamento: string;
  turno: string;
}

export interface DadosNovaInscricao {
  processoId: string;
  poloId: string;
  criancaId: string;
  responsavelId: string;
  cepResponsavel?: string | null;
  bairroResponsavel?: string | null;
  opcoes: EscolhaOpcao[]; // já na ordem de preferência da família — 1 a 5
}

/**
 * Cria a inscrição e suas opções, todas em NA_FILA. Não pontua nem ordena
 * fila aqui — isso é a Query C aplicada em cima da Query B (Fase 3B, ver
 * README) e roda separado do motor de alocação.
 */
export async function criarInscricao(dados: DadosNovaInscricao) {
  if (dados.opcoes.length < 1 || dados.opcoes.length > 5) {
    throw new Error("A inscrição precisa de 1 a 5 opções, na ordem de preferência.");
  }
  const codigosUnicos = new Set(dados.opcoes.map((o) => `${o.unidadeEscCodigo}|${o.grupamento}|${o.turno}`));
  if (codigosUnicos.size !== dados.opcoes.length) {
    throw new Error("Duas opções não podem repetir a mesma unidade, grupamento e turno.");
  }

  const jaTemInscricaoNoProcesso = await prisma.inscricao.findFirst({
    where: { processoId: dados.processoId, criancaId: dados.criancaId },
  });
  if (jaTemInscricaoNoProcesso) {
    throw new Error("Esta criança já tem uma inscrição neste processo seletivo.");
  }

  const ultima = await prisma.inscricao.findFirst({
    where: { processoId: dados.processoId, poloId: dados.poloId },
    orderBy: { iplId: "desc" },
    select: { iplId: true },
  });

  return prisma.$transaction(async (tx) => {
    const inscricao = await tx.inscricao.create({
      data: {
        processoId: dados.processoId,
        poloId: dados.poloId,
        iplId: (ultima?.iplId ?? 0) + 1,
        criancaId: dados.criancaId,
        responsavelId: dados.responsavelId,
        dataCriacao: new Date(),
        cepResponsavel: dados.cepResponsavel,
        bairroResponsavel: dados.bairroResponsavel,
      },
    });

    for (const [i, opcao] of dados.opcoes.entries()) {
      await tx.opcao.create({
        data: {
          inscricaoId: inscricao.id,
          ordem: i + 1,
          unidadeEscCodigo: opcao.unidadeEscCodigo,
          grupamento: opcao.grupamento,
          turno: opcao.turno,
          estado: "NA_FILA",
        },
      });
    }

    return inscricao;
  });
}

export async function listarInscricoesDaCrianca(criancaId: string) {
  return prisma.inscricao.findMany({
    where: { criancaId },
    include: {
      processo: true,
      opcoes: { include: { unidade: true }, orderBy: { ordem: "asc" } },
    },
    orderBy: { dataCriacao: "desc" },
  });
}
