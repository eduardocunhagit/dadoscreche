import { prisma } from "@/core/db/client";
import { classificarResposta } from "./classificador";

export type StatusComunicacao = "NAO_ENVIADA" | "ENVIADA" | "RESPONDIDA" | "ERRO";

export interface DestinatarioEnvio {
  criancaId: string;
  contatoId: string;
}

export interface UsuarioMensagens {
  id: string;
  papel: string;
  poloId?: string | null;
  unidadeEscCodigo?: string | null;
}

function telefoneValido(valor: string) {
  const digitos = valor.replace(/\D/g, "");
  return digitos.length >= 10 && digitos.length <= 13;
}

async function criancaNoEscopo(criancaId: string, usuario: UsuarioMensagens) {
  if (usuario.papel === "GESTOR_SME") return true;

  if (usuario.papel === "SERVIDOR_UNIDADE" && usuario.unidadeEscCodigo) {
    return (
      (await prisma.inscricao.count({
        where: {
          criancaId,
          opcoes: { some: { unidadeEscCodigo: usuario.unidadeEscCodigo } },
        },
      })) > 0
    );
  }

  if (usuario.papel === "SERVIDOR_CRE" && usuario.poloId) {
    return (await prisma.inscricao.count({ where: { criancaId, poloId: usuario.poloId } })) > 0;
  }

  return false;
}

export async function statusPorCrianca(criancaIds: string[]) {
  const resultado: Record<string, StatusComunicacao> = Object.fromEntries(
    criancaIds.map((id) => [id, "NAO_ENVIADA" as const])
  );

  if (criancaIds.length === 0) return resultado;

  const conversas = await prisma.msgConversa.findMany({
    where: { criancaId: { in: criancaIds } },
    select: { criancaId: true, status: true },
  });

  for (const conversa of conversas) {
    const atual = resultado[conversa.criancaId];
    if (conversa.status === "RESPONDIDA") {
      resultado[conversa.criancaId] = "RESPONDIDA";
    } else if (conversa.status === "ERRO" && atual !== "RESPONDIDA") {
      resultado[conversa.criancaId] = "ERRO";
    } else if (atual === "NAO_ENVIADA") {
      resultado[conversa.criancaId] = "ENVIADA";
    }
  }

  return resultado;
}

export async function enviarMensagensDemo(
  destinatarios: DestinatarioEnvio[],
  mensagemModelo: string,
  usuario: UsuarioMensagens
) {
  if (destinatarios.length === 0 || destinatarios.length > 200) {
    throw new Error("Selecione entre 1 e 200 crianças por envio.");
  }

  const chaves = new Set(destinatarios.map((item) => `${item.criancaId}:${item.contatoId}`));
  if (chaves.size !== destinatarios.length) {
    throw new Error("Há destinatários repetidos na seleção.");
  }

  const contatos = await prisma.contato.findMany({
    where: {
      id: { in: destinatarios.map((item) => item.contatoId) },
      canal: "WHATSAPP",
      ativo: true,
    },
    include: {
      crianca: { include: { responsavelPrincipal: true } },
    },
  });
  const contatoPorId = new Map(contatos.map((contato) => [contato.id, contato]));

  for (const destinatario of destinatarios) {
    const contato = contatoPorId.get(destinatario.contatoId);
    if (!contato || contato.criancaId !== destinatario.criancaId) {
      throw new Error("Um dos WhatsApps selecionados não pertence à criança informada.");
    }
    if (contato.papel === "ALTERNATIVO" && !contato.consentimentoEm) {
      throw new Error("Um contato alternativo não possui autorização registrada.");
    }
    if (!telefoneValido(contato.valor)) {
      throw new Error("Um dos WhatsApps selecionados possui número inválido.");
    }
    if (!(await criancaNoEscopo(destinatario.criancaId, usuario))) {
      throw new Error("Uma das crianças selecionadas está fora do seu escopo.");
    }
  }

  await prisma.$transaction(async (tx) => {
    for (const destinatario of destinatarios) {
      const contato = contatoPorId.get(destinatario.contatoId)!;
      const nomeContato =
        contato.papel === "ALTERNATIVO"
          ? `${contato.parentesco ?? "Contato alternativo"} — ${contato.nomeContato ?? "sem nome"}`
          : contato.crianca.responsavelPrincipal.nomeExibicao;

      const conversa = await tx.msgConversa.upsert({
        where: {
          criancaId_contatoId: {
            criancaId: destinatario.criancaId,
            contatoId: destinatario.contatoId,
          },
        },
        update: {
          nomeContato,
          telefone: contato.valor,
          status: "ENVIADA",
        },
        create: {
          criancaId: destinatario.criancaId,
          contatoId: destinatario.contatoId,
          nomeContato,
          telefone: contato.valor,
          status: "ENVIADA",
        },
      });

      await tx.msgMensagem.create({
        data: {
          conversaId: conversa.id,
          direcao: "SAIDA",
          conteudo: mensagemModelo.replaceAll("{crianca}", contato.crianca.nomeExibicao),
          status: "ENVIADA",
          autorUsuarioId: usuario.id,
        },
      });
    }
  });
}

export async function listarConversasDaCrianca(criancaId: string) {
  return prisma.msgConversa.findMany({
    where: { criancaId },
    include: { mensagens: { orderBy: { criadaEm: "asc" } } },
    orderBy: { atualizadoEm: "desc" },
  });
}

export async function receberRespostaDemo(
  conversaId: string,
  conteudo: string,
  usuario: UsuarioMensagens
) {
  const conversa = await prisma.msgConversa.findUniqueOrThrow({ where: { id: conversaId } });
  if (!(await criancaNoEscopo(conversa.criancaId, usuario))) {
    throw new Error("Esta conversa está fora do seu escopo.");
  }

  const resultado = classificarResposta(conteudo);
  await prisma.$transaction([
    prisma.msgMensagem.create({
      data: {
        conversaId,
        direcao: "ENTRADA",
        conteudo,
        status: "RECEBIDA",
        classificacao: resultado.classificacao,
        sugestaoResposta: resultado.sugestaoResposta,
      },
    }),
    prisma.msgConversa.update({ where: { id: conversaId }, data: { status: "RESPONDIDA" } }),
  ]);
}

export async function responderMensagemDemo(
  conversaId: string,
  conteudo: string,
  usuario: UsuarioMensagens
) {
  const conversa = await prisma.msgConversa.findUniqueOrThrow({ where: { id: conversaId } });
  if (!(await criancaNoEscopo(conversa.criancaId, usuario))) {
    throw new Error("Esta conversa está fora do seu escopo.");
  }

  await prisma.msgMensagem.create({
    data: {
      conversaId,
      direcao: "SAIDA",
      conteudo,
      status: "ENVIADA",
      autorUsuarioId: usuario.id,
    },
  });
}
