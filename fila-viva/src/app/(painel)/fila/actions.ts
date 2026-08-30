"use server";

import { revalidatePath } from "next/cache";
import { auth } from "@/core/auth";
import { prisma } from "@/core/db/client";
import { aplicarEvento, opcaoNoEscopoDoUsuario } from "@/modules/alocacao";
import type { EventoGatilho } from "@/core/domain/motor";

async function autorOuFalha() {
  const session = await auth();
  const user = session?.user;
  if (!user || user.papel === "RESPONSAVEL") throw new Error("Sem permissão.");
  return user;
}

export async function actionAplicarEvento(formData: FormData) {
  const user = await autorOuFalha();
  const opcaoId = String(formData.get("opcaoId"));

  const podeAgir = await opcaoNoEscopoDoUsuario(opcaoId, user);
  if (!podeAgir) throw new Error("Esta opção está fora do seu escopo.");

  const evento = String(formData.get("evento")) as EventoGatilho;
  await aplicarEvento(opcaoId, evento, { usuarioId: user.id, papel: user.papel });
  revalidatePath("/fila");
}

export async function actionAlternarFlag(formData: FormData) {
  const autor = await autorOuFalha();
  if (autor.papel !== "GESTOR_SME") throw new Error("Só o gestor SME pode mudar as regras do processo.");

  const processoId = String(formData.get("processoId"));
  const campo = String(formData.get("campo")) as "liberacaoEmCascata" | "aceiteCondicional";
  const processo = await prisma.processo.findUniqueOrThrow({ where: { id: processoId } });
  await prisma.processo.update({
    where: { id: processoId },
    data: { [campo]: !processo[campo] },
  });
  revalidatePath("/fila");
}
