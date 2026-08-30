import { describe, expect, it } from "vitest";
import { classificarResposta } from "./classificador";

describe("classificarResposta", () => {
  it.each([
    ["Sim, este número continua correto", "CONFIRMOU_CONTATO"],
    ["Número errado, não conheço essa pessoa", "NUMERO_INCORRETO"],
    ["Quando a creche vai entrar em contato?", "DUVIDA"],
    ["Quero falar com uma pessoa", "ATENDIMENTO_HUMANO"],
    ["Ok, recebido", "INCERTA"],
  ])("classifica %s", (texto, classificacao) => {
    expect(classificarResposta(texto).classificacao).toBe(classificacao);
  });

  it("sempre oferece uma resposta editável", () => {
    expect(classificarResposta("mensagem livre").sugestaoResposta.length).toBeGreaterThan(20);
  });
});
