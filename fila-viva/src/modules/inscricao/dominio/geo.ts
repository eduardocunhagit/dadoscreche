export interface Ponto {
  latitude: number
  longitude: number
}

/**
 * Calcula a distância entre dois pontos usando a fórmula de Haversine.
 * Raio da Terra: 6371 km
 */
export function distanciaKm(a: Ponto, b: Ponto): number {
  const R = 6371

  const lat1Rad = (a.latitude * Math.PI) / 180
  const lat2Rad = (b.latitude * Math.PI) / 180
  const dLat = ((b.latitude - a.latitude) * Math.PI) / 180
  const dLon = ((b.longitude - a.longitude) * Math.PI) / 180

  const a_var =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1Rad) *
      Math.cos(lat2Rad) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)

  const c = 2 * Math.atan2(Math.sqrt(a_var), Math.sqrt(1 - a_var))

  return R * c
}

/**
 * Calcula o centroide (ponto médio) de uma lista de pontos.
 * Retorna null se a lista estiver vazia.
 */
export function centroide(pontos: Ponto[]): Ponto | null {
  if (pontos.length === 0) {
    return null
  }

  const somaLatitude = pontos.reduce((sum, p) => sum + p.latitude, 0)
  const somaLongitude = pontos.reduce((sum, p) => sum + p.longitude, 0)

  return {
    latitude: somaLatitude / pontos.length,
    longitude: somaLongitude / pontos.length,
  }
}

/**
 * Normaliza nome de bairro:
 * - Remove espaços nas extremidades
 * - Converte para maiúsculas
 * - Remove acentos (usando NFD)
 * - Colapsa múltiplos espaços em um
 */
export function normalizarBairro(nome: string): string {
  return (
    nome
      .trim()
      .toUpperCase()
      .normalize('NFD')
      // Remove combining diacritical marks (U+0300 a U+036F)
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
  )
}

/**
 * Ordena itens pela distância até a origem (em ordem ascendente).
 * Anexa a propriedade distanciaKm a cada item.
 * O sort é estável.
 */
export function ordenarPorDistancia<T extends Ponto>(
  origem: Ponto,
  itens: T[]
): (T & { distanciaKm: number })[] {
  return itens
    .map((item) => ({
      ...item,
      distanciaKm: distanciaKm(origem, item),
    }))
    .sort((a, b) => a.distanciaKm - b.distanciaKm)
}
