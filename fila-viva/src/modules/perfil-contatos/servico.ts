import { prisma } from "@/core/db/client";
import { barramento } from "@/core/events/bus";
import type { CanalContato, PapelContato } from "@/core/domain/constants";

// Regra do módulo: toda escrita em Contato passa por aqui — nunca direto
// via Prisma numa rota. É isso que garante que NENHUMA alteração escapa do
// ContatoHistorico, que é o que sustenta a auditoria (ver Briefing, seção
// "gaps do processo atual" e o plano, seção 05).

export interface AutorEdicao {
  usuarioId: string;
  papel: string;
  responsavelId?: string | null;
}

export interface UsuarioComEscopo {
  papel: string;
  responsavelId?: string | null;
  poloId?: string | null;
  unidadeEscCodigo?: string | null;
}

/**
 * true se `user` pode ver/editar esta criança. RESPONSAVEL só a própria;
 * SERVIDOR_UNIDADE/SERVIDOR_CRE só quem tem alguma inscrição na unidade ou
 * no polo dele; GESTOR_SME sempre. Usado tanto pela página de perfil
 * quanto pelas Server Actions de edição — nunca confie só numa das duas.
 */
export async function criancaNoEscopoDoUsuario(criancaId: string, user: UsuarioComEscopo) {
  if (user.papel === "GESTOR_SME") return true;

  if (user.papel === "RESPONSAVEL") {
    const crianca = await prisma.crianca.findUnique({ where: { id: criancaId } });
    return crianca?.responsavelPrincipalId === user.responsavelId;
  }

  if (user.papel === "SERVIDOR_UNIDADE" && user.unidadeEscCodigo) {
    const n = await prisma.inscricao.count({
      where: { criancaId, opcoes: { some: { unidadeEscCodigo: user.unidadeEscCodigo } } },
    });
    return n > 0;
  }

  if (user.papel === "SERVIDOR_CRE" && user.poloId) {
    const n = await prisma.inscricao.count({ where: { criancaId, poloId: user.poloId } });
    return n > 0;
  }

  return false;
}

export async function listarCriancasDoResponsavel(responsavelId: string) {
  return prisma.crianca.findMany({
    where: { responsavelPrincipalId: responsavelId },
    include: { contatos: { where: { ativo: true }, orderBy: { ordemTentativa: "asc" } } },
    orderBy: { nomeExibicao: "asc" },
  });
}

export async function obterCriancaComContatos(criancaId: string) {
  return prisma.crianca.findUnique({
    where: { id: criancaId },
    include: {
      contatos: {
        orderBy: [{ ativo: "desc" }, { ordemTentativa: "asc" }],
        include: { historico: { orderBy: { quando: "desc" }, take: 10 } },
      },
      responsavelPrincipal: true,
    },
  });
}

export interface DadosNovoContato {
  papel: PapelContato;
  nomeContato?: string;
  parentesco?: string;
  canal: CanalContato;
  valor: string;
  ordemTentativa: number;
  consentimentoDoResponsavel?: boolean;
}

export async function adicionarContato(criancaId: string, dados: DadosNovoContato, autor: AutorEdicao) {
  if (dados.papel === "ALTERNATIVO") {
    if (!dados.nomeContato || !dados.parentesco) {
      throw new Error("Contato alternativo exige nome e parentesco.");
    }
    if (!dados.consentimentoDoResponsavel) {
      throw new Error(
        "É preciso o responsável declarar que autoriza usar este contato de terceiro."
      );
    }
  }

  const contato = await prisma.contato.create({
    data: {
      criancaId,
      papel: dados.papel,
      nomeContato: dados.nomeContato,
      parentesco: dados.parentesco,
      canal: dados.canal,
      valor: dados.valor,
      ordemTentativa: dados.ordemTentativa,
      consentimentoEm: dados.papel === "ALTERNATIVO" ? new Date() : null,
    },
  });

  await registrarHistorico(contato.id, autor, "criado", null, resumoContato(contato));

  if (dados.papel === "ALTERNATIVO") {
    await prisma.crianca.update({
      where: { id: criancaId },
      data: { semContatoAlternativoDeclarado: false, semContatoAlternativoDeclaradoEm: null },
    });
  }

  await barramento.emit("contato.alterado", { contatoId: contato.id, criancaId, autorPapel: autor.papel });
  return contato;
}

export async function editarValorContato(
  contatoId: string,
  novoValor: string,
  autor: AutorEdicao
) {
  const atual = await prisma.contato.findUniqueOrThrow({ where: { id: contatoId } });
  if (atual.valor === novoValor) return atual;

  const atualizado = await prisma.contato.update({
    where: { id: contatoId },
    data: { valor: novoValor, verificadoEm: null },
  });

  await registrarHistorico(contatoId, autor, "valor", atual.valor, novoValor);
  await barramento.emit("contato.alterado", {
    contatoId,
    criancaId: atualizado.criancaId,
    autorPapel: autor.papel,
  });
  return atualizado;
}

export async function desativarContato(contatoId: string, autor: AutorEdicao) {
  const atual = await prisma.contato.findUniqueOrThrow({ where: { id: contatoId } });
  const atualizado = await prisma.contato.update({ where: { id: contatoId }, data: { ativo: false } });
  await registrarHistorico(contatoId, autor, "ativo", String(atual.ativo), "false");
  await barramento.emit("contato.alterado", {
    contatoId,
    criancaId: atualizado.criancaId,
    autorPapel: autor.papel,
  });
  return atualizado;
}

export async function verificarContato(contatoId: string, autor: AutorEdicao) {
  const atual = await prisma.contato.findUniqueOrThrow({ where: { id: contatoId } });
  const agora = new Date();
  const atualizado = await prisma.contato.update({
    where: { id: contatoId },
    data: { verificadoEm: agora },
  });
  await registrarHistorico(contatoId, autor, "verificadoEm", atual.verificadoEm?.toISOString() ?? null, agora.toISOString());
  return atualizado;
}

export async function declararSemContatoAlternativo(criancaId: string, declarado: boolean) {
  return prisma.crianca.update({
    where: { id: criancaId },
    data: {
      semContatoAlternativoDeclarado: declarado,
      semContatoAlternativoDeclaradoEm: declarado ? new Date() : null,
    },
  });
}

/** Fila de trabalho da CRE: contatos nunca verificados ou vencidos há mais de `meses`. */
export async function filaDeRevalidacao(opts: { poloId?: string; unidadeEscCodigo?: string; meses?: number }) {
  const limite = new Date();
  limite.setMonth(limite.getMonth() - (opts.meses ?? 6));

  const criancas = await prisma.crianca.findMany({
    where: {
      inscricoes: opts.poloId
        ? { some: { poloId: opts.poloId } }
        : opts.unidadeEscCodigo
          ? { some: { opcoes: { some: { unidadeEscCodigo: opts.unidadeEscCodigo } } } }
          : undefined,
      contatos: { some: { ativo: true, OR: [{ verificadoEm: null }, { verificadoEm: { lt: limite } }] } },
    },
    include: {
      responsavelPrincipal: true,
      contatos: { where: { ativo: true }, orderBy: { ordemTentativa: "asc" } },
      inscricoes: { orderBy: { dataCriacao: "desc" }, take: 1 },
    },
    orderBy: { nomeExibicao: "asc" },
  });

  return criancas;
}

function resumoContato(c: { canal: string; valor: string }) {
  return `${c.canal}:${c.valor}`;
}

async function registrarHistorico(
  contatoId: string,
  autor: AutorEdicao,
  campo: string,
  antes: string | null,
  depois: string | null
) {
  await prisma.contatoHistorico.create({
    data: {
      contatoId,
      autorUsuarioId: autor.usuarioId,
      autorResponsavelId: autor.responsavelId ?? undefined,
      autorPapel: autor.papel,
      campo,
      valorAntes: antes,
      valorDepois: depois,
    },
  });
}
