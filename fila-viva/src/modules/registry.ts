import { barramento, type NomeEvento } from "@/core/events/bus";
import type { PapelUsuario } from "@/core/domain/constants";
import { moduloPerfilContatos } from "./perfil-contatos";
import { moduloAlocacao } from "./alocacao";
import { moduloExemplo } from "./exemplo";
import { moduloInscricao } from "./inscricao";
import type { Modulo, ItemDeMenu } from "./tipos";

// A única linha compartilhada que um módulo novo toca: acrescentar o import
// acima e o nome na lista abaixo. Nunca editar uma tela ou serviço de outro
// módulo para se plugar — é para isso que existem menu/widgets/assina.
export const MODULOS: Modulo[] = [moduloPerfilContatos, moduloAlocacao, moduloExemplo, moduloInscricao];

export function menuParaPapel(papel: PapelUsuario): ItemDeMenu[] {
  return MODULOS.flatMap((m) => m.menu ?? []).filter((item) => item.papeis.includes(papel));
}

export function widgetsDoSlot(slot: string) {
  return MODULOS.flatMap((m) => m.widgets ?? []).filter((w) => w.slot === slot);
}

let assinado = false;

// Chamado uma vez na subida do processo (ver src/instrumentation.ts) para
// ligar cada `assina` do manifesto ao barramento de verdade.
export function registrarAssinaturas() {
  if (assinado) return;
  assinado = true;
  for (const modulo of MODULOS) {
    if (!modulo.assina) continue;
    for (const [evento, handler] of Object.entries(modulo.assina)) {
      if (handler) barramento.onDynamic(evento as NomeEvento, handler);
    }
  }
}
