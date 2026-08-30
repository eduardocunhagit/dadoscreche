/**
 * Determina o grupamento (etapa) de uma criança baseado em sua data de nascimento.
 *
 * Regra: calcula a idade completa em 31/03 do anoProcesso:
 * - < 2 anos → "Berçário"
 * - >= 2 e < 3 anos → "Maternal I"
 * - >= 3 e < 4 anos → "Maternal II"
 * - >= 4 anos → null
 *
 * Convenção de data: nascimentoAnoMes em formato "yyyy-MM", interpreta como dia 01 do mês.
 * Entrada malformada retorna null.
 *
 * @param nascimentoAnoMes Data de nascimento no formato "yyyy-MM"
 * @param anoProcesso Ano de referência para cálculo (será usado 31/03 deste ano)
 * @returns Grupamento correspondente ou null se não elegível ou entrada inválida
 */
export function grupamentoPorNascimento(
  nascimentoAnoMes: string,
  anoProcesso: number
): "Berçário" | "Maternal I" | "Maternal II" | null {
  // Validar formato "yyyy-MM"
  const regex = /^\d{4}-\d{2}$/;
  if (!regex.test(nascimentoAnoMes)) {
    return null;
  }

  const [anoStr, mesStr] = nascimentoAnoMes.split("-");
  const ano = Number(anoStr);
  const mes = Number(mesStr);

  // Validar ano e mês
  if (isNaN(ano) || isNaN(mes) || mes < 1 || mes > 12) {
    return null;
  }

  // Data de nascimento: dia 01 do mês especificado
  // new Date(year, monthIndex, day) - mês é zero-indexado
  const dataNascimento = new Date(ano, mes - 1, 1);

  // Data de referência: 31/03 do anoProcesso
  const dataReferencia = new Date(anoProcesso, 2, 31); // Março é mês 2 (zero-indexed)

  // Calcular idade completa em anos
  let idade = dataReferencia.getFullYear() - dataNascimento.getFullYear();

  // Ajustar se ainda não fez aniversário até a data de referência
  if (
    dataReferencia.getMonth() < dataNascimento.getMonth() ||
    (dataReferencia.getMonth() === dataNascimento.getMonth() &&
      dataReferencia.getDate() < dataNascimento.getDate())
  ) {
    idade--;
  }

  // Aplicar regras de grupamento
  if (idade < 2) {
    return "Berçário";
  }
  if (idade < 3) {
    return "Maternal I";
  }
  if (idade < 4) {
    return "Maternal II";
  }

  return null;
}
