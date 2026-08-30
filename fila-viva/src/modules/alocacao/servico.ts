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
