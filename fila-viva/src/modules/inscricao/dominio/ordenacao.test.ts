import { describe, it, expect } from "vitest";
import {
  LIMITE_OPCOES,
  alternarEscolha,
  moverPosicao,
} from "./ordenacao";

describe("ordenacao", () => {
  describe("LIMITE_OPCOES", () => {
    it("deve ser 5", () => {
      expect(LIMITE_OPCOES).toBe(5);
    });
  });

  describe("alternarEscolha", () => {
    const igual = (a: number, b: number) => a === b;

    it("deve adicionar item ausente ao fim", () => {
      const resultado = alternarEscolha([1, 2], 3, igual);
      expect(resultado).toEqual([1, 2, 3]);
    });

    it("deve adicionar ao fim de lista vazia", () => {
      const resultado = alternarEscolha([], 1, igual);
      expect(resultado).toEqual([1]);
    });

    it("deve respeitar limite de 5 items — 6º não entra", () => {
      const lista = [1, 2, 3, 4, 5];
      const resultado = alternarEscolha(lista, 6, igual);
      expect(resultado).toBe(lista);
    });

    it("deve remover item presente", () => {
      const resultado = alternarEscolha([1, 2, 3], 2, igual);
      expect(resultado).toEqual([1, 3]);
    });

    it("deve remover único item da lista", () => {
      const resultado = alternarEscolha([1], 1, igual);
      expect(resultado).toEqual([]);
    });

    it("deve preservar ordem ao remover", () => {
      const resultado = alternarEscolha([1, 2, 3, 4, 5], 3, igual);
      expect(resultado).toEqual([1, 2, 4, 5]);
    });

    it("deve preservar imutabilidade — não mutar entrada ao adicionar", () => {
      const lista = [1, 2, 3];
      const resultado = alternarEscolha(lista, 4, igual);
      expect(resultado).not.toBe(lista);
      expect(lista).toEqual([1, 2, 3]);
    });

    it("deve preservar imutabilidade — não mutar entrada ao remover", () => {
      const lista = [1, 2, 3];
      const resultado = alternarEscolha(lista, 2, igual);
      expect(resultado).not.toBe(lista);
      expect(lista).toEqual([1, 2, 3]);
    });

    it("deve preservar imutabilidade — não mutar entrada quando cheia", () => {
      const lista = [1, 2, 3, 4, 5];
      const resultado = alternarEscolha(lista, 6, igual);
      expect(resultado).toBe(lista);
      expect(lista).toEqual([1, 2, 3, 4, 5]);
    });

    it("deve usar função de igualdade customizada", () => {
      const igual = (a: { id: number }, b: { id: number }) => a.id === b.id;
      const lista = [{ id: 1 }, { id: 2 }];
      const resultado = alternarEscolha(lista, { id: 3 }, igual);
      expect(resultado).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }]);
    });

    it("deve remover com igualdade customizada mesmo com objetos diferentes", () => {
      const igual = (a: { id: number }, b: { id: number }) => a.id === b.id;
      const lista: { id: number; nome?: string }[] = [{ id: 1 }, { id: 2 }];
      const resultado = alternarEscolha(lista, { id: 2, nome: "x" }, igual);
      expect(resultado).toEqual([{ id: 1 }]);
    });
  });

  describe("moverPosicao", () => {
    it("deve mover item para frente", () => {
      const resultado = moverPosicao([1, 2, 3, 4, 5], 1, 3);
      expect(resultado).toEqual([1, 3, 4, 2, 5]);
    });

    it("deve mover item para trás", () => {
      const resultado = moverPosicao([1, 2, 3, 4, 5], 3, 1);
      expect(resultado).toEqual([1, 4, 2, 3, 5]);
    });

    it("deve não mudar quando tenta mover índice 0 para cima", () => {
      const lista = [1, 2, 3, 4, 5];
      const resultado = moverPosicao(lista, 0, -1);
      expect(resultado).toBe(lista);
    });

    it("deve não mudar quando tenta mover último índice para baixo", () => {
      const lista = [1, 2, 3, 4, 5];
      const resultado = moverPosicao(lista, 4, 10);
      expect(resultado).toBe(lista);
    });

    it("deve clampar índice de origem para cima", () => {
      const lista = [1, 2, 3, 4, 5];
      const resultado = moverPosicao(lista, -5, -3);
      expect(resultado).toBe(lista); // Ambos clampam a 0
    });

    it("deve clampar índice de destino para baixo", () => {
      const lista = [1, 2, 3, 4, 5];
      const resultado = moverPosicao(lista, 10, 20);
      expect(resultado).toBe(lista); // Ambos clampam a 4
    });

    it("deve clampar origem e usar destino válido", () => {
      const resultado = moverPosicao([1, 2, 3, 4, 5], -1, 2);
      // de clamps a 0, para = 2, então move 0 para 2
      expect(resultado).toEqual([2, 3, 1, 4, 5]);
    });

    it("deve clampar destino e usar origem válida", () => {
      const resultado = moverPosicao([1, 2, 3, 4, 5], 2, 10);
      // de = 2, para clamps a 4, então move 2 para 4
      expect(resultado).toEqual([1, 2, 4, 5, 3]);
    });

    it("deve preservar imutabilidade", () => {
      const lista = [1, 2, 3];
      const resultado = moverPosicao(lista, 0, 2);
      expect(resultado).not.toBe(lista);
      expect(lista).toEqual([1, 2, 3]);
    });

    it("deve lidar com lista de um elemento", () => {
      const resultado = moverPosicao([1], 0, 10);
      expect(resultado).toEqual([1]);
    });

    it("deve lidar com lista vazia", () => {
      const resultado = moverPosicao([], 0, 5);
      expect(resultado).toEqual([]);
    });

    it("deve ser estável — elementos não-movidos mantêm ordem relativa", () => {
      const resultado = moverPosicao([1, 2, 3, 4, 5], 1, 4);
      expect(resultado).toEqual([1, 3, 4, 5, 2]);
    });
  });
});
