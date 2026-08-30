import { type EstadoOpcao } from "./constants";

// Motor de alocação — a proposta do Eixo 2. Duas peças, cada uma testável
// isoladamente e cada uma atrás da sua própria flag por processo:
//
//   1. `transicionar`     — a máquina de estados de UMA opção.
//   2. `planejarCascata`  — dado um evento em uma opção, quais OUTRAS
//      opções da MESMA inscrição precisam reagir. É aqui que moram as duas
//      regras do plano: liberação em cascata e aceite condicional.
//
// Nenhuma das duas toca o banco. Quem grava o resultado (e o OfertaEvento
// de cada transição) é o serviço em src/modules/alocacao — ver EXTENDING.md
// sobre por que essa separação importa para quem for mexer aqui depois.

export type EventoOpcao =
  | "OFERTAR"
  | "ACEITAR_DEFINITIVO"
  | "ACEITAR_CONDICIONAL"
  | "RECUSAR"
  | "EXPIRAR"
  | "SUSPENDER"
  | "REATIVAR"
  | "ENCERRAR"
  | "PROMOVER"
  | "CONVERTER_DEFINITIVO";

const TRANSICOES: Record<EstadoOpcao, Partial<Record<EventoOpcao, EstadoOpcao>>> = {
  NA_FILA: {
    OFERTAR: "OFERTADA",
    SUSPENDER: "POSICAO_SUSPENSA",
    ENCERRAR: "ENCERRADA",
  },
  OFERTADA: {
    ACEITAR_DEFINITIVO: "ACEITA_DEFINITIVA",
    ACEITAR_CONDICIONAL: "ACEITA_CONDICIONAL",
    RECUSAR: "RECUSADA",
    EXPIRAR: "EXPIRADA",
    SUSPENDER: "POSICAO_SUSPENSA",
    ENCERRAR: "ENCERRADA",
  },
  ACEITA_CONDICIONAL: {
    PROMOVER: "ENCERRADA",
    CONVERTER_DEFINITIVO: "ACEITA_DEFINITIVA",
  },
  ACEITA_DEFINITIVA: {},
  POSICAO_SUSPENSA: {
    REATIVAR: "NA_FILA",
    ENCERRAR: "ENCERRADA",
  },
  RECUSADA: {},
  EXPIRADA: {},
  ENCERRADA: {},
};

export class TransicaoInvalidaError extends Error {
  constructor(estado: EstadoOpcao, evento: EventoOpcao) {
    super(`Transição inválida: ${estado} --${evento}--> ?`);
    this.name = "TransicaoInvalidaError";
  }
}

export function transicionar(estadoAtual: EstadoOpcao, evento: EventoOpcao): EstadoOpcao {
  const destino = TRANSICOES[estadoAtual]?.[evento];
  if (!destino) throw new TransicaoInvalidaError(estadoAtual, evento);
  return destino;
}

export function transicaoValida(estadoAtual: EstadoOpcao, evento: EventoOpcao): boolean {
  return Boolean(TRANSICOES[estadoAtual]?.[evento]);
}

// ---------------------------------------------------------------------------
// Cascata
// ---------------------------------------------------------------------------

export interface OpcaoDaFila {
  id: string;
  ordem: number;
  estado: EstadoOpcao;
}

export interface RegrasMotor {
  liberacaoEmCascata: boolean;
  aceiteCondicional: boolean;
}

export interface AcaoCascata {
  opcaoId: string;
  evento: EventoOpcao;
}

export type EventoGatilho =
  | "OFERTAR"
  | "ACEITAR_DEFINITIVO"
  | "ACEITAR_CONDICIONAL"
  | "RECUSAR"
  | "EXPIRAR";

/**
 * Dado que `opcaoAlvoId` acabou de sofrer `evento`, decide o que acontece
 * com as OUTRAS opções da mesma inscrição. Regras (ver plano):
 *
 * - OFERTAR opção k, com liberacaoEmCascata ligada → opções piores que k
 *   (ordem > k) que estejam NA_FILA ou OFERTADA vão para POSICAO_SUSPENSA:
 *   a vaga delas devolve à rede na hora, mas a família não perde o lugar.
 * - RECUSAR/EXPIRAR em k → as piores suspensas por causa de k reativam,
 *   voltando a NA_FILA na posição original.
 * - ACEITAR_CONDICIONAL em k, com aceiteCondicional ligada → piores que k
 *   encerram (ela nunca vai preferir algo pior que k); melhores continuam
 *   intocadas, é esse o ponto da regra. Só permite uma condicional por
 *   criança por processo — a promoção seguinte tem que ser definitiva.
 * - ACEITAR_DEFINITIVO em k → toda opção-irmã encerra; se alguma estava
 *   ACEITA_CONDICIONAL, essa vira PROMOVER (ela estava seguindo uma opção
 *   pior enquanto esperava esta, e agora migrou).
 */
export function planejarCascata(
  opcoes: OpcaoDaFila[],
  opcaoAlvoId: string,
  evento: EventoGatilho,
  regras: RegrasMotor
): AcaoCascata[] {
  const alvo = opcoes.find((o) => o.id === opcaoAlvoId);
  if (!alvo) {
    throw new Error(`Opção ${opcaoAlvoId} não está na lista de opções informada.`);
  }

  const irmas = opcoes.filter((o) => o.id !== alvo.id);
  const piores = irmas.filter((o) => o.ordem > alvo.ordem);
  const acoes: AcaoCascata[] = [];

  switch (evento) {
    case "OFERTAR": {
      if (!regras.liberacaoEmCascata) return [];
      for (const o of piores) {
        if (o.estado === "NA_FILA" || o.estado === "OFERTADA") {
          acoes.push({ opcaoId: o.id, evento: "SUSPENDER" });
        }
      }
      return acoes;
    }

    case "RECUSAR":
    case "EXPIRAR": {
      for (const o of piores) {
        if (o.estado === "POSICAO_SUSPENSA") {
          acoes.push({ opcaoId: o.id, evento: "REATIVAR" });
        }
      }
      return acoes;
    }

    case "ACEITAR_CONDICIONAL": {
      if (!regras.aceiteCondicional) {
        throw new Error(
          "Aceite condicional está desligado para este processo (flag aceiteCondicional)."
        );
      }
      const jaTemCondicional = irmas.some((o) => o.estado === "ACEITA_CONDICIONAL");
      if (jaTemCondicional) {
        throw new Error(
          "Esta criança já usou o aceite condicional neste processo — a próxima " +
            "promoção precisa ser definitiva (regra: uma migração por criança)."
        );
      }
      for (const o of piores) {
        if (o.estado === "NA_FILA" || o.estado === "OFERTADA" || o.estado === "POSICAO_SUSPENSA") {
          acoes.push({ opcaoId: o.id, evento: "ENCERRAR" });
        }
      }
      // As opções melhores (ordem < alvo) não entram nesta lista de
      // propósito: é isso que faz o aceite condicional valer a pena.
      return acoes;
    }

    case "ACEITAR_DEFINITIVO": {
      for (const o of irmas) {
        if (o.estado === "ACEITA_CONDICIONAL") {
          acoes.push({ opcaoId: o.id, evento: "PROMOVER" });
        } else if (o.estado !== "ENCERRADA" && o.estado !== "RECUSADA" && o.estado !== "EXPIRADA") {
          acoes.push({ opcaoId: o.id, evento: "ENCERRAR" });
        }
      }
      return acoes;
    }
  }
}

// ---------------------------------------------------------------------------
// Janela de condicionalidade — guarda-corpo nº1 do plano
// ---------------------------------------------------------------------------

export function janelaCondicionalVencida(aceitoEm: Date, agora: Date, janelaDias: number): boolean {
  const limiteMs = aceitoEm.getTime() + janelaDias * 24 * 60 * 60 * 1000;
  return agora.getTime() >= limiteMs;
}
