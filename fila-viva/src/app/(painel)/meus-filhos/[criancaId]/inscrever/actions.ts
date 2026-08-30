"use server";

import { redirect } from "next/navigation";
import { auth } from "@/core/auth";
import { criancaNoEscopoDoUsuario } from "@/modules/perfil-contatos";
import { buscarUnidades, criarInscricao, type EscolhaOpcao } from "@/modules/alocacao";

export async function actionBuscarUnidades(termo: string) {
  const session = await auth();
  if (!session?.user) throw new Error("Não autenticado.");
  const unidades = await buscarUnidades(termo);
  return unidades.map((u) => ({ escCodigo: u.escCodigo, nome: u.nome, bairro: u.bairro }));
}

export async function actionCriarInscricao(params: {
  criancaId: string;
  processoId: string;
  poloId: string;
  opcoes: EscolhaOpcao[];
}) {
  const session = await auth();
  const user = session?.user;
  if (!user) throw new Error("Não autenticado.");

  const podeAcessar = await criancaNoEscopoDoUsuario(params.criancaId, user);
  if (!podeAcessar) throw new Error("Este cadastro está fora do seu escopo.");

  const { prisma } = await import("@/core/db/client");
  const crianca = await prisma.crianca.findUniqueOrThrow({ where: { id: params.criancaId } });

  await criarInscricao({
    processoId: params.processoId,
    poloId: params.poloId,
    criancaId: params.criancaId,
    responsavelId: crianca.responsavelPrincipalId,
    opcoes: params.opcoes,
  });

  redirect(`/meus-filhos/${params.criancaId}`);
}
