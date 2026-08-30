"use server";

import { revalidatePath } from "next/cache";
import { auth } from "@/core/auth";
import {
  adicionarContato,
  desativarContato,
  editarValorContato,
  declararSemContatoAlternativo,
  verificarContato,
  criancaNoEscopoDoUsuario,
  type AutorEdicao,
} from "@/modules/perfil-contatos";
import type { CanalContato, PapelContato } from "@/core/domain/constants";

async function autorOuFalha(criancaId: string): Promise<AutorEdicao> {
  const session = await auth();
  const user = session?.user;
  if (!user) throw new Error("Não autenticado.");

  const podeAcessar = await criancaNoEscopoDoUsuario(criancaId, user);
  if (!podeAcessar) throw new Error("Este cadastro está fora do seu escopo.");

  return { usuarioId: user.id, papel: user.papel, responsavelId: user.responsavelId };
}

export async function actionAdicionarContato(formData: FormData) {
  const criancaId = String(formData.get("criancaId"));
  const autor = await autorOuFalha(criancaId);

  const papel = String(formData.get("papel")) as PapelContato;
  await adicionarContato(
    criancaId,
    {
      papel,
      nomeContato: formData.get("nomeContato")?.toString() || undefined,
      parentesco: formData.get("parentesco")?.toString() || undefined,
      canal: String(formData.get("canal")) as CanalContato,
      valor: String(formData.get("valor")),
      ordemTentativa: Number(formData.get("ordemTentativa") ?? 1),
      consentimentoDoResponsavel: formData.get("consentimento") === "on",
    },
    autor
  );

  revalidatePath(`/meus-filhos/${criancaId}`);
}

export async function actionEditarValor(formData: FormData) {
  const criancaId = String(formData.get("criancaId"));
  const autor = await autorOuFalha(criancaId);
  await editarValorContato(String(formData.get("contatoId")), String(formData.get("valor")), autor);
  revalidatePath(`/meus-filhos/${criancaId}`);
}

export async function actionDesativar(formData: FormData) {
  const criancaId = String(formData.get("criancaId"));
  const autor = await autorOuFalha(criancaId);
  await desativarContato(String(formData.get("contatoId")), autor);
  revalidatePath(`/meus-filhos/${criancaId}`);
}

export async function actionVerificar(formData: FormData) {
  const criancaId = String(formData.get("criancaId"));
  const autor = await autorOuFalha(criancaId);
  await verificarContato(String(formData.get("contatoId")), autor);
  revalidatePath(`/meus-filhos/${criancaId}`);
}

export async function actionDeclararSemAlternativo(formData: FormData) {
  const criancaId = String(formData.get("criancaId"));
  await autorOuFalha(criancaId);
  const declarado = formData.get("declarado") === "true";
  await declararSemContatoAlternativo(criancaId, declarado);
  revalidatePath(`/meus-filhos/${criancaId}`);
}
