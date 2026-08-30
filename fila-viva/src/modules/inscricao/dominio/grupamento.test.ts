import { describe, it, expect } from "vitest";
import { grupamentoPorNascimento } from "./grupamento";

describe("grupamentoPorNascimento", () => {
  describe("fronteiras de faixa etária", () => {
    // Convenção de data: "yyyy-MM" interpreta como dia 01 do mês
    // Data de referência: 31/03 do anoProcesso
    // Idade completa = anos que a pessoa completou até 31/03

    it("deve retornar Berçário para < 2 anos", () => {
      // Nasce em 2023-06 (01/06/2023)
      // Em 31/03/2025, tem 1 ano e 9 meses
      const resultado = grupamentoPorNascimento("2023-06", 2025);
      expect(resultado).toBe("Berçário");
    });

    it("deve retornar Maternal I para >= 2 e < 3 anos", () => {
      // Nasce em 2022-01 (01/01/2022)
      // Em 31/03/2024, tem 2 anos e 2 meses (já fez 2 anos)
      const resultado = grupamentoPorNascimento("2022-01", 2024);
      expect(resultado).toBe("Maternal I");
    });

    it("deve retornar Maternal II para >= 3 e < 4 anos", () => {
      // Nasce em 2020-06 (01/06/2020)
      // Em 31/03/2024, tem 3 anos e 9 meses
      const resultado = grupamentoPorNascimento("2020-06", 2024);
      expect(resultado).toBe("Maternal II");
    });

    it("deve retornar null para >= 4 anos", () => {
      // Nasce em 2020-01 (01/01/2020)
      // Em 31/03/2024, tem 4 anos e 2 meses
      const resultado = grupamentoPorNascimento("2020-01", 2024);
      expect(resultado).toBeNull();
    });
  });

  describe("casos limite de aniversário", () => {
    it("deve considerar aniversário ANTES de 31/03 como completado", () => {
      // Nasce em 2023-03 (01/03/2023)
      // Em 31/03/2025, JÁ fez 2 anos (aniversário em 01/03)
      const resultado = grupamentoPorNascimento("2023-03", 2025);
      expect(resultado).toBe("Maternal I");
    });

    it("deve considerar aniversário EM 31/03 como completado", () => {
      // Nasce em 2023-03 (01/03/2023)
      // Mesmo teste: em 31/03/2025 já tem 2 anos
      const resultado = grupamentoPorNascimento("2023-03", 2025);
      expect(resultado).toBe("Maternal I");
    });

    it("deve considerar aniversário APÓS 31/03 como não completado", () => {
      // Nasce em 2023-04 (01/04/2023)
      // Em 31/03/2025, ainda NÃO fez 2 anos (aniversário em 01/04)
      const resultado = grupamentoPorNascimento("2023-04", 2025);
      expect(resultado).toBe("Berçário");
    });

    it("deve estar correto para limiar Berçário -> Maternal I", () => {
      // Exatamente 2 anos em 31/03
      // Nasce em 2022-03 (01/03/2022)
      // Em 31/03/2024, faz 2 anos
      const resultado = grupamentoPorNascimento("2022-03", 2024);
      expect(resultado).toBe("Maternal I");
    });

    it("deve estar correto para limiar Maternal I -> Maternal II", () => {
      // Exatamente 3 anos em 31/03
      // Nasce em 2021-03 (01/03/2021)
      // Em 31/03/2024, faz 3 anos
      const resultado = grupamentoPorNascimento("2021-03", 2024);
      expect(resultado).toBe("Maternal II");
    });

    it("deve estar correto para limiar Maternal II -> null", () => {
      // Exatamente 4 anos em 31/03
      // Nasce em 2020-03 (01/03/2020)
      // Em 31/03/2024, faz 4 anos -> null
      const resultado = grupamentoPorNascimento("2020-03", 2024);
      expect(resultado).toBeNull();
    });
  });

  describe("formato inválido", () => {
    it("deve retornar null para formato com barra", () => {
      expect(grupamentoPorNascimento("2023/06", 2025)).toBeNull();
    });

    it("deve retornar null para formato com um dígito no mês", () => {
      expect(grupamentoPorNascimento("2023-6", 2025)).toBeNull();
    });

    it("deve retornar null para ano com 2 dígitos", () => {
      expect(grupamentoPorNascimento("23-06", 2025)).toBeNull();
    });

    it("deve retornar null para sem hífen", () => {
      expect(grupamentoPorNascimento("202306", 2025)).toBeNull();
    });

    it("deve retornar null para string vazia", () => {
      expect(grupamentoPorNascimento("", 2025)).toBeNull();
    });

    it("deve retornar null para mês com 3 dígitos", () => {
      expect(grupamentoPorNascimento("2023-006", 2025)).toBeNull();
    });
  });

  describe("valores inválidos de mês", () => {
    it("deve retornar null para mês 0", () => {
      expect(grupamentoPorNascimento("2023-00", 2025)).toBeNull();
    });

    it("deve retornar null para mês 13", () => {
      expect(grupamentoPorNascimento("2023-13", 2025)).toBeNull();
    });

    it("deve retornar null para mês negativo", () => {
      expect(grupamentoPorNascimento("2023--1", 2025)).toBeNull();
    });

    it("deve retornar null para mês texto", () => {
      expect(grupamentoPorNascimento("2023-ab", 2025)).toBeNull();
    });
  });

  describe("valores inválidos de ano", () => {
    it("deve retornar null para ano texto", () => {
      expect(grupamentoPorNascimento("abcd-06", 2025)).toBeNull();
    });

    it("deve retornar null para ano vazio", () => {
      expect(grupamentoPorNascimento("-06", 2025)).toBeNull();
    });
  });

  describe("casos reais esperados", () => {
    it("bebê de 0 anos", () => {
      // Nasce em 2024-08 (01/08/2024)
      // Em 31/03/2025, tem 0 anos (ainda não fez 1)
      const resultado = grupamentoPorNascimento("2024-08", 2025);
      expect(resultado).toBe("Berçário");
    });

    it("criança com 2 anos completos", () => {
      // Nasce em 2022-02 (01/02/2022)
      // Em 31/03/2024, tem 2 anos e 1 mês
      const resultado = grupamentoPorNascimento("2022-02", 2024);
      expect(resultado).toBe("Maternal I");
    });

    it("criança com 3 anos e meio", () => {
      // Nasce em 2020-09 (01/09/2020)
      // Em 31/03/2024, tem 3 anos e 6 meses
      const resultado = grupamentoPorNascimento("2020-09", 2024);
      expect(resultado).toBe("Maternal II");
    });

    it("criança fora de faixa de creche", () => {
      // Nasce em 2019-05 (01/05/2019)
      // Em 31/03/2024, tem 4 anos e 10 meses
      const resultado = grupamentoPorNascimento("2019-05", 2024);
      expect(resultado).toBeNull();
    });
  });

  describe("processamento de string", () => {
    it("não deve aceitar espaços", () => {
      expect(grupamentoPorNascimento(" 2023-06", 2025)).toBeNull();
      expect(grupamentoPorNascimento("2023-06 ", 2025)).toBeNull();
    });

    it("não deve aceitar hífen extra", () => {
      expect(grupamentoPorNascimento("2023--06", 2025)).toBeNull();
      expect(grupamentoPorNascimento("2023-06-", 2025)).toBeNull();
    });
  });
});
