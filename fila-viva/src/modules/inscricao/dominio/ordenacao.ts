export const LIMITE_OPCOES = 5;

/**
 * Alterna a presença de um item em uma lista de escolhidas.
 * - Se o item está presente: remove
 * - Se está ausente e há espaço: adiciona ao fim
 * - Se está ausente e lista está cheia: retorna a lista inalterada
 *
 * @param escolhidas Lista de itens escolhidos
 * @param item Item a alternar
 * @param igual Função de comparação para determinar igualdade
 * @returns Nova lista (imutável), respeitando LIMITE_OPCOES
 */
export function alternarEscolha<T>(
  escolhidas: T[],
  item: T,
  igual: (a: T, b: T) => boolean
): T[] {
  const indice = escolhidas.findIndex((e) => igual(e, item));

  if (indice !== -1) {
    // Remove se presente
    return escolhidas.filter((_, i) => i !== indice);
  }

  // Adiciona se ausente e ainda há espaço
  if (escolhidas.length < LIMITE_OPCOES) {
    return [...escolhidas, item];
  }

  // Se cheio, retorna a mesma lista
  return escolhidas;
}

/**
 * Move um item de uma posição para outra em uma lista.
 * Índices são clampeados aos limites da lista.
 * Se de e para apontam para a mesma posição (após clamp), retorna lista inalterada.
 *
 * @param lista Lista de itens
 * @param de Índice de origem (será clampado)
 * @param para Índice de destino (será clampado)
 * @returns Nova lista (imutável) com item movido
 */
export function moverPosicao<T>(
  lista: T[],
  de: number,
  para: number
): T[] {
  if (lista.length === 0) return lista;

  // Clamp nos limites da lista
  const deClampado = Math.max(0, Math.min(de, lista.length - 1));
  const paraClampado = Math.max(0, Math.min(para, lista.length - 1));

  // Se resultam na mesma posição após clamp, sem mudança
  if (deClampado === paraClampado) {
    return lista;
  }

  const novaLista = [...lista];
  const item = novaLista[deClampado];
  novaLista.splice(deClampado, 1);
  novaLista.splice(paraClampado, 0, item);

  return novaLista;
}
