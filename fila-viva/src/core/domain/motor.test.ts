import { describe, expect, it } from "vitest";
import {
  janelaCondicionalVencida,
  planejarCascata,
  transicaoValida,
  transicionar,
  type OpcaoDaFila,
  type RegrasMotor,
} from "./motor";

const REGRAS_LIGADAS: RegrasMotor = { liberacaoEmCascata: true, aceiteCondicional: true };
const REGRAS_DESLIGADAS: RegrasMotor = { liberacaoEmCascata: false, aceiteCondicional: false };

function fila(...estados: OpcaoDaFila["estado"][]): OpcaoDaFila[] {
  return estados.map((estado, i) => ({ id: `o${i + 1}`, ordem: i + 1, estado }));
}

describe("transicionar", () => {
  it("aplica uma transição válida", () => {
    expect(transicionar("NA_FILA", "OFERTAR")).toBe("OFERTADA");
    expect(transicionar("OFERTADA", "ACEITAR_DEFINITIVO")).toBe("ACEITA_DEFINITIVA");
  });

  it("rejeita uma transição fora da máquina de estados", () => {
    expect(() => transicionar("ACEITA_DEFINITIVA", "OFERTAR")).toThrow(/Transição inválida/);
    expect(() => transicionar("RECUSADA", "ACEITAR_DEFINITIVO")).toThrow();
  });

  it("transicaoValida não lança e responde booleano", () => {
    expect(transicaoValida("NA_FILA", "OFERTAR")).toBe(true);
    expect(transicaoValida("ENCERRADA", "OFERTAR")).toBe(false);
  });
});

describe("planejarCascata — OFERTAR (regra 1: liberação em cascata)", () => {
  it("suspende as opções piores que estão NA_FILA ou OFERTADA", () => {
    const opcoes = fila("ACEITA_DEFINITIVA", "NA_FILA", "OFERTADA", "NA_FILA", "OFERTADA");
    // opção 3 acabou de ser ofertada
    const plano = planejarCascata(opcoes, "o3", "OFERTAR", REGRAS_LIGADAS);
    expect(plano).toEqual(
      expect.arrayContaining([
        { opcaoId: "o4", evento: "SUSPENDER" },
        { opcaoId: "o5", evento: "SUSPENDER" },
      ])
    );
    expect(plano).toHaveLength(2);
    // não mexe nas opções melhores (o1, o2)
    expect(plano.some((a) => a.opcaoId === "o1" || a.opcaoId === "o2")).toBe(false);
  });

  it("não faz nada com a flag desligada — é o comportamento de hoje", () => {
    const opcoes = fila("NA_FILA", "NA_FILA", "OFERTADA", "NA_FILA", "OFERTADA");
    const plano = planejarCascata(opcoes, "o3", "OFERTAR", REGRAS_DESLIGADAS);
    expect(plano).toEqual([]);
  });

  it("não suspende opções piores que já estão em estado terminal", () => {
    const opcoes = fila("NA_FILA", "NA_FILA", "OFERTADA", "RECUSADA", "ENCERRADA");
    const plano = planejarCascata(opcoes, "o3", "OFERTAR", REGRAS_LIGADAS);
    expect(plano).toEqual([]);
  });
});

describe("planejarCascata — RECUSAR/EXPIRAR devolve o lugar suspenso", () => {
  it("reativa só as piores que estavam suspensas por causa desta opção", () => {
    const opcoes = fila("NA_FILA", "NA_FILA", "OFERTADA", "POSICAO_SUSPENSA", "POSICAO_SUSPENSA");
    const plano = planejarCascata(opcoes, "o3", "RECUSAR", REGRAS_LIGADAS);
    expect(plano).toEqual(
      expect.arrayContaining([
        { opcaoId: "o4", evento: "REATIVAR" },
        { opcaoId: "o5", evento: "REATIVAR" },
      ])
    );
    expect(plano).toHaveLength(2);
  });

  it("EXPIRAR se comporta como RECUSAR para efeito de cascata", () => {
    const opcoes = fila("NA_FILA", "OFERTADA", "POSICAO_SUSPENSA");
    const plano = planejarCascata(opcoes, "o2", "EXPIRAR", REGRAS_LIGADAS);
    expect(plano).toEqual([{ opcaoId: "o3", evento: "REATIVAR" }]);
  });
});

describe("planejarCascata — ACEITAR_CONDICIONAL (regra 2: aceite condicional)", () => {
  it("encerra as opções piores e NÃO TOCA nas melhores", () => {
    const opcoes = fila("NA_FILA", "OFERTADA", "OFERTADA", "NA_FILA", "POSICAO_SUSPENSA");
    // aceita condicionalmente na opção 3
    const plano = planejarCascata(opcoes, "o3", "ACEITAR_CONDICIONAL", REGRAS_LIGADAS);
    expect(plano).toEqual(
      expect.arrayContaining([
        { opcaoId: "o4", evento: "ENCERRAR" },
        { opcaoId: "o5", evento: "ENCERRAR" },
      ])
    );
    expect(plano).toHaveLength(2);
    expect(plano.some((a) => a.opcaoId === "o1" || a.opcaoId === "o2")).toBe(false);
  });

  it("recusa aceite condicional se a flag do processo está desligada", () => {
    const opcoes = fila("NA_FILA", "OFERTADA");
    expect(() =>
      planejarCascata(opcoes, "o2", "ACEITAR_CONDICIONAL", REGRAS_DESLIGADAS)
    ).toThrow(/desligado/);
  });

  it("bloqueia uma segunda condicional na mesma inscrição — uma migração por criança", () => {
    const opcoes = fila("ACEITA_CONDICIONAL", "OFERTADA", "NA_FILA");
    // já existe uma condicional em o1; tentar aceitar condicional em o2 é inválido
    expect(() =>
      planejarCascata(opcoes, "o2", "ACEITAR_CONDICIONAL", REGRAS_LIGADAS)
    ).toThrow(/uma migração por criança/);
  });
});

describe("planejarCascata — ACEITAR_DEFINITIVO fecha tudo, promove a condicional", () => {
  it("encerra todas as irmãs não-terminais, melhores e piores", () => {
    const opcoes = fila("NA_FILA", "OFERTADA", "NA_FILA", "POSICAO_SUSPENSA");
    const plano = planejarCascata(opcoes, "o3", "ACEITAR_DEFINITIVO", REGRAS_LIGADAS);
    expect(plano).toEqual(
      expect.arrayContaining([
        { opcaoId: "o1", evento: "ENCERRAR" },
        { opcaoId: "o2", evento: "ENCERRAR" },
        { opcaoId: "o4", evento: "ENCERRAR" },
      ])
    );
    expect(plano).toHaveLength(3);
  });

  it("promove a opção que estava aceita condicionalmente numa opção pior", () => {
    // a família tinha aceitado condicionalmente a opção 3 e agora a 1 (melhor) confirma de vez
    const opcoes = fila("OFERTADA", "NA_FILA", "ACEITA_CONDICIONAL");
    const plano = planejarCascata(opcoes, "o1", "ACEITAR_DEFINITIVO", REGRAS_LIGADAS);
    expect(plano).toEqual(
      expect.arrayContaining([
        { opcaoId: "o2", evento: "ENCERRAR" },
        { opcaoId: "o3", evento: "PROMOVER" },
      ])
    );
    expect(plano).toHaveLength(2);
  });

  it("não gera ação para irmãs que já estão em estado terminal", () => {
    const opcoes = fila("NA_FILA", "RECUSADA", "ENCERRADA", "EXPIRADA");
    const plano = planejarCascata(opcoes, "o1", "ACEITAR_DEFINITIVO", REGRAS_LIGADAS);
    expect(plano).toEqual([]);
  });
});

describe("janelaCondicionalVencida", () => {
  const aceitoEm = new Date("2026-02-01T00:00:00Z");

  it("não venceu antes do prazo", () => {
    const agora = new Date("2026-02-20T00:00:00Z");
    expect(janelaCondicionalVencida(aceitoEm, agora, 30)).toBe(false);
  });

  it("vence exatamente no dia do prazo", () => {
    const agora = new Date("2026-03-03T00:00:00Z");
    expect(janelaCondicionalVencida(aceitoEm, agora, 30)).toBe(true);
  });

  it("vence bem depois do prazo", () => {
    const agora = new Date("2026-06-01T00:00:00Z");
    expect(janelaCondicionalVencida(aceitoEm, agora, 30)).toBe(true);
  });
});
