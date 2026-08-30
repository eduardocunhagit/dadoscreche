/**
 * Módulo de domínio para validação e formatação de CPF.
 * Funções puras sem dependências externas.
 */

/**
 * Remove todos os caracteres não-dígitos de uma string.
 * @param bruto String com possivelmente pontuação (ex: "123.456.789-01")
 * @returns String contendo apenas dígitos
 */
export function normalizarCpf(bruto: string): string {
  return bruto.replace(/\D/g, '');
}

/**
 * Valida se um CPF é válido segundo as regras da Receita Federal.
 *
 * Regras:
 * - Deve ter exatamente 11 dígitos (após normalização)
 * - Dígitos verificadores (DVs) devem estar corretos
 * - Rejeita CPFs com todos os dígitos iguais (000.000.000-00, 111.111.111-11, etc.)
 *
 * @param cpf CPF com ou sem máscara (ex: "111.444.777-35" ou "11144477735")
 * @returns true se CPF é válido, false caso contrário
 */
export function cpfValido(cpf: string): boolean {
  const normalizado = normalizarCpf(cpf);

  // Rejeitar se não tiver exatamente 11 dígitos
  if (normalizado.length !== 11) {
    return false;
  }

  // Rejeitar se todos os dígitos são iguais (000...0, 111...1, etc.)
  if (/^(\d)\1{10}$/.test(normalizado)) {
    return false;
  }

  // Validar primeiro dígito verificador (posição 9)
  let soma = 0;
  for (let i = 0; i < 9; i++) {
    soma += parseInt(normalizado[i], 10) * (10 - i);
  }
  let resto = soma % 11;
  const dv1 = resto < 2 ? 0 : 11 - resto;

  if (parseInt(normalizado[9], 10) !== dv1) {
    return false;
  }

  // Validar segundo dígito verificador (posição 10)
  soma = 0;
  for (let i = 0; i < 10; i++) {
    soma += parseInt(normalizado[i], 10) * (11 - i);
  }
  resto = soma % 11;
  const dv2 = resto < 2 ? 0 : 11 - resto;

  if (parseInt(normalizado[10], 10) !== dv2) {
    return false;
  }

  return true;
}

/**
 * Formata um CPF com máscara, exibindo apenas os 2 últimos dígitos.
 *
 * Formato: ***.***.***-NN (onde NN são os 2 últimos dígitos)
 *
 * @param cpf CPF com ou sem máscara
 * @returns CPF formatado com máscara (***.***.***-XX) ou original se inválido
 */
export function mascararCpf(cpf: string): string {
  const normalizado = normalizarCpf(cpf);

  if (normalizado.length !== 11) {
    return cpf;
  }

  // Retorna "***.***.***-NN" onde NN são os últimos 2 dígitos
  return `***.***.***.${normalizado.slice(-2)}`;
}
