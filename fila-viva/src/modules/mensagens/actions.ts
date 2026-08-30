"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { auth } from "@/core/auth";
import {
  enviarMensagensDemo,
  receberRespostaDemo,
  responderMensagemDemo,
  type UsuarioMensagens,
} from "./servico";
import type { EstadoAcaoMensagens } from "./tipos";

const schemaDestinatarios = z
  .array(
    z.object({
      criancaId: z.string().min(1),
      contatoId: z.string().min(1),
    })
  )
  .min(1)
  .max(200);

const schemaMensagem = z.string().trim().min(10).max(1000);
const schemaResposta = z.string().trim().min(1).max(1000);

async function usuarioEquipeOuFalha(): Promise<UsuarioMensagens> {
  const session = await auth();
  const user = session?.user;
  if (!user || user.papel === "RESPONSAVEL") {
    throw new Error("Sem permissão para enviar mensagens.");
  }
  return {
    id: user.id,
    papel: user.papel,
    poloId: user.poloId,
    unidadeEscCodigo: user.unidadeEscCodigo,
  };
}

export async function actionEnviarMensagens(
  _estadoAnterior: EstadoAcaoMensagens,
  formData: FormData
): Promise<EstadoAcaoMensagens> {
  try {
    const usuario = await usuarioEquipeOuFalha();
    const bruto = JSON.parse(String(formData.get("destinatarios") ?? "[]"));
    const destinatarios = schemaDestinatarios.parse(bruto);
    const mensagem = schemaMensagem.parse(formData.get("mensagem"));

    await enviarMensagensDemo(destinatarios, mensagem, usuario);
    revalidatePath("/revalidacao-contatos");
    return {
      ok: true,
      mensagem: `${destinatarios.length} mensagem(ns) enviada(s) no modo de demonstração.`,
    };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof Error ? erro.message : "Não foi possível enviar as mensagens.",
    };
  }
}

export async function actionReceberRespostaDemo(formData: FormData) {
  const usuario = await usuarioEquipeOuFalha();
  const conversaId = z.string().min(1).parse(formData.get("conversaId"));
  const criancaId = z.string().min(1).parse(formData.get("criancaId"));
  const resposta = schemaResposta.parse(formData.get("resposta"));

  await receberRespostaDemo(conversaId, resposta, usuario);
  revalidatePath(`/meus-filhos/${criancaId}`);
  revalidatePath("/revalidacao-contatos");
}

export async function actionResponderMensagem(formData: FormData) {
  const usuario = await usuarioEquipeOuFalha();
  const conversaId = z.string().min(1).parse(formData.get("conversaId"));
  const criancaId = z.string().min(1).parse(formData.get("criancaId"));
  const resposta = schemaResposta.parse(formData.get("resposta"));

  await responderMensagemDemo(conversaId, resposta, usuario);
  revalidatePath(`/meus-filhos/${criancaId}`);
}
