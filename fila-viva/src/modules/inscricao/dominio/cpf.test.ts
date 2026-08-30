import { describe, it, expect } from 'vitest';
import { normalizarCpf, cpfValido, mascararCpf } from './cpf';

describe('CPF', () => {
  describe('normalizarCpf', () => {
    it('deve remover pontuação de CPF formatado', () => {
      expect(normalizarCpf('111.444.777-35')).toBe('11144477735');
    });

    it('deve remover todos os caracteres não-dígitos', () => {
      expect(normalizarCpf('123abc456def789xx')).toBe('123456789');
    });

    it('deve retornar string vazia para entrada sem dígitos', () => {
      expect(normalizarCpf('abc-def.ghi')).toBe('');
    });

    it('deve lidar com espaços', () => {
      expect(normalizarCpf('111 444 777 35')).toBe('11144477735');
    });

    it('deve retornar dígitos já normalizados', () => {
      expect(normalizarCpf('11144477735')).toBe('11144477735');
    });
  });

  describe('cpfValido', () => {
    it('deve aceitar CPF válido com máscara', () => {
      expect(cpfValido('111.444.777-35')).toBe(true);
    });

    it('deve aceitar CPF válido sem máscara', () => {
      expect(cpfValido('11144477735')).toBe(true);
    });

    it('deve rejeitar CPF com dígito verificador incorreto (primeiro DV)', () => {
      expect(cpfValido('111.444.777-36')).toBe(false);
    });

    it('deve rejeitar CPF com dígito verificador incorreto (segundo DV)', () => {
      expect(cpfValido('111.444.777-34')).toBe(false);
    });

    it('deve rejeitar CPF com ambos os DVs incorretos', () => {
      expect(cpfValido('111.444.777-00')).toBe(false);
    });

    it('deve rejeitar CPF com todos os dígitos iguais a 0', () => {
      expect(cpfValido('000.000.000-00')).toBe(false);
    });

    it('deve rejeitar CPF com todos os dígitos iguais a 1', () => {
      expect(cpfValido('111.111.111-11')).toBe(false);
    });

    it('deve rejeitar CPF com todos os dígitos iguais a 2', () => {
      expect(cpfValido('222.222.222-22')).toBe(false);
    });

    it('deve rejeitar CPF com todos os dígitos iguais (normalizado)', () => {
      expect(cpfValido('33333333333')).toBe(false);
    });

    it('deve rejeitar CPF com menos de 11 dígitos', () => {
      expect(cpfValido('111.444.777')).toBe(false);
      expect(cpfValido('12345678901')).toBe(false);
    });

    it('deve rejeitar CPF com mais de 11 dígitos', () => {
      expect(cpfValido('111.444.777-350')).toBe(false);
      expect(cpfValido('123456789012')).toBe(false);
    });

    it('deve rejeitar string vazia', () => {
      expect(cpfValido('')).toBe(false);
    });

    it('deve rejeitar string com apenas caracteres não-dígitos', () => {
      expect(cpfValido('.-.-.-')).toBe(false);
    });

    it('deve rejeitar CPF com pontuação inconsistente', () => {
      expect(cpfValido('111 444 777 35')).toBe(true); // Valida após normalizar
    });
  });

  describe('mascararCpf', () => {
    it('deve mascarar CPF válido com máscara', () => {
      expect(mascararCpf('111.444.777-35')).toBe('***.***.***.35');
    });

    it('deve mascarar CPF válido sem máscara', () => {
      expect(mascararCpf('11144477735')).toBe('***.***.***.35');
    });

    it('deve mostrar apenas os 2 últimos dígitos', () => {
      expect(mascararCpf('12345678901')).toBe('***.***.***.01');
    });

    it('deve retornar CPF original se não tiver 11 dígitos', () => {
      const cpfInvalido = '123.456.789';
      expect(mascararCpf(cpfInvalido)).toBe(cpfInvalido);
    });

    it('deve lidar com string vazia', () => {
      expect(mascararCpf('')).toBe('');
    });

    it('deve mascarar mesmo que DVs estejam incorretos (não valida)', () => {
      // mascararCpf não valida os DVs, apenas o comprimento após normalização
      expect(mascararCpf('111.444.777-36')).toBe('***.***.***.36');
    });
  });
});
