"use server";

import { revalidatePath } from "next/cache";
import { auth } from "@/core/auth";
import { prisma } from "@/core/db/client";
import { criancaNoEscopoDoUsuario, adicionarContato, type AutorEdicao } from "@/modules/perfil-contatos";
import {
  geocodificarCep,
  criarCriancaDoResponsavel,
  criarInscricaoCompleta,
  type EnderecoGeocodificado,
  type DadosNovaInscricao,
} from "@/modules/inscricao";
import type { CanalContato, PapelContato } from "@/core/domain/constants";
import type { ContatoResumo } from "./tipos";

async function autorOuFalha(): Promise<AutorEdicao> {
  const session = await auth();
  const user = session?.user;
  if (!user) throw new Error("Não autenticado.");
  return { usuarioId: user.id, papel: user.papel, responsavelId: user.responsavelId };
}

export async function actionGeocodificarCep(cep: string): Promise<EnderecoGeocodificado> {
  await autorOuFalha();
  return geocodificarCep(cep);
}

export async function actionCriarCrianca(dados: {
  nomeExibicao: string;
  sexo: "M" | "F";
  nascimentoAnoMes: string;
}): Promise<{ criancaId: string }> {
  const autor = await autorOuFalha();
  if (autor.papel !== "RESPONSAVEL" || !autor.responsavelId) {
    throw new Error("Apenas responsáveis podem cadastrar uma criança.");
  }
  const resultado = await criarCriancaDoResponsavel(autor.responsavelId, dados);
  revalidatePath("/nova-inscricao");
  revalidatePath("/meus-filhos");
  return resultado;
}

export async function actionAdicionarContatoInscricao(dados: {
  criancaId: string;
  canal: string;
  valor: string;
  papel: "RESPONSAVEL" | "ALTERNATIVO";
  nomeContato?: string;
  parentesco?: string;
  consentimento?: boolean;
}): Promise<{ contatos: ContatoResumo[] }> {
  const autor = await autorOuFalha();
  const podeAcessar = await criancaNoEscopoDoUsuario(dados.criancaId, autor);
  if (!podeAcessar) throw new Error("Esta criança está fora do seu escopo.");

  const contatosAtivos = await prisma.contato.findMany({
    where: { criancaId: dados.criancaId, ativo: true },
    orderBy: { ordemTentativa: "asc" },
  });
  const proximaOrdem = contatosAtivos.length + 1;

  await adicionarContato(
    dados.criancaId,
    {
      papel: dados.papel as PapelContato,
      nomeContato: dados.nomeContato,
      parentesco: dados.parentesco,
      canal: dados.canal as CanalContato,
      valor: dados.valor,
      ordemTentativa: proximaOrdem,
      consentimentoDoResponsavel: dados.consentimento,
    },
    autor
  );

  const contatosAtualizados = await prisma.contato.findMany({
    where: { criancaId: dados.criancaId, ativo: true },
    orderBy: { ordemTentativa: "asc" },
  });

  return {
    contatos: contatosAtualizados.map((c) => ({ id: c.id, canal: c.canal, valor: c.valor, papel: c.papel })),
  };
}

export async function actionCriarInscricao(
  dados: DadosNovaInscricao
): Promise<{ ok: true } | { ok: false; erro: string }> {
  try {
    const autor = await autorOuFalha();
    await criarInscricaoCompleta(dados, autor);
    revalidatePath("/meus-filhos");
    return { ok: true };
  } catch (erro) {
    return { ok: false, erro: (erro as Error).message };
  }
}
