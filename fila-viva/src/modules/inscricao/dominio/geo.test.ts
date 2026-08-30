import { describe, it, expect } from 'vitest'
import {
  distanciaKm,
  centroide,
  normalizarBairro,
  ordenarPorDistancia,
} from './geo'

describe('geo', () => {
  describe('distanciaKm', () => {
    it('calcula distância entre Centro do Rio e Barra da Tijuca', () => {
      const centro = { latitude: -22.9068, longitude: -43.1729 }
      const barraDaTijuca = { latitude: -23.0004, longitude: -43.3659 }

      const distancia = distanciaKm(centro, barraDaTijuca)

      expect(distancia).toBeGreaterThanOrEqual(20)
      expect(distancia).toBeLessThanOrEqual(25)
    })

    it('retorna zero para o mesmo ponto', () => {
      const ponto = { latitude: 0, longitude: 0 }

      const distancia = distanciaKm(ponto, ponto)

      expect(distancia).toBe(0)
    })

    it('calcula distância simétrica', () => {
      const p1 = { latitude: 10, longitude: 20 }
      const p2 = { latitude: 30, longitude: 40 }

      const d1 = distanciaKm(p1, p2)
      const d2 = distanciaKm(p2, p1)

      expect(d1).toBeCloseTo(d2)
    })
  })

  describe('centroide', () => {
    it('calcula o centroide de uma lista simples com dois pontos', () => {
      const pontos = [
        { latitude: 0, longitude: 0 },
        { latitude: 2, longitude: 2 },
      ]

      const centro = centroide(pontos)

      expect(centro).toEqual({ latitude: 1, longitude: 1 })
    })

    it('calcula o centroide de uma lista com múltiplos pontos', () => {
      const pontos = [
        { latitude: 0, longitude: 0 },
        { latitude: 2, longitude: 0 },
        { latitude: 0, longitude: 2 },
        { latitude: 2, longitude: 2 },
      ]

      const centro = centroide(pontos)

      expect(centro).toEqual({ latitude: 1, longitude: 1 })
    })

    it('retorna null para lista vazia', () => {
      const centro = centroide([])

      expect(centro).toBeNull()
    })
  })

  describe('normalizarBairro', () => {
    it('trata "  Jacarepaguá " corretamente', () => {
      const resultado = normalizarBairro('  Jacarepaguá ')

      expect(resultado).toBe('JACAREPAGUA')
    })

    it('trata "São Cristóvão" corretamente', () => {
      const resultado = normalizarBairro('São Cristóvão')

      expect(resultado).toBe('SAO CRISTOVAO')
    })

    it('converte para maiúsculas', () => {
      const resultado = normalizarBairro('Centro')

      expect(resultado).toBe('CENTRO')
    })

    it('remove múltiplos espaços', () => {
      const resultado = normalizarBairro('Bairro   Com    Espaços')

      expect(resultado).toBe('BAIRRO COM ESPACOS')
    })

    it('trata string vazia', () => {
      const resultado = normalizarBairro('')

      expect(resultado).toBe('')
    })
  })

  describe('ordenarPorDistancia', () => {
    it('ordena pontos em ordem ascendente de distância', () => {
      const origem = { latitude: -22.9068, longitude: -43.1729 }
      const itens = [
        { latitude: -22.95, longitude: -43.18, id: 'a' }, // mais longe
        { latitude: -22.905, longitude: -43.172, id: 'b' }, // mais perto
        { latitude: -22.92, longitude: -43.175, id: 'c' }, // meio
      ]

      const resultado = ordenarPorDistancia(origem, itens)

      expect(resultado).toHaveLength(3)
      expect(resultado[0].id).toBe('b')
      expect(resultado[1].id).toBe('c')
      expect(resultado[2].id).toBe('a')
    })

    it('anexa distanciaKm aos itens', () => {
      const origem = { latitude: 0, longitude: 0 }
      const itens = [
        { latitude: 0.01, longitude: 0, id: 'a' },
        { latitude: 0.05, longitude: 0, id: 'b' },
      ]

      const resultado = ordenarPorDistancia(origem, itens)

      expect(resultado[0]).toHaveProperty('distanciaKm')
      expect(resultado[1]).toHaveProperty('distanciaKm')
      expect(resultado[0].distanciaKm).toBeLessThan(resultado[1].distanciaKm)
      expect(resultado[0].distanciaKm).toBeGreaterThan(0)
      expect(resultado[1].distanciaKm).toBeGreaterThan(resultado[0].distanciaKm)
    })

    it('preserva a ordem (estável) para itens com mesma distância', () => {
      const origem = { latitude: 0, longitude: 0 }
      const itens = [
        { latitude: 0.01, longitude: 0, id: 'a' },
        { latitude: 0.01, longitude: 0, id: 'b' },
        { latitude: 0.01, longitude: 0, id: 'c' },
      ]

      const resultado = ordenarPorDistancia(origem, itens)

      expect(resultado[0].id).toBe('a')
      expect(resultado[1].id).toBe('b')
      expect(resultado[2].id).toBe('c')
    })

    it('funciona com lista vazia', () => {
      const origem = { latitude: 0, longitude: 0 }
      const itens: Array<{ latitude: number; longitude: number; id: string }> =
        []

      const resultado = ordenarPorDistancia(origem, itens)

      expect(resultado).toHaveLength(0)
    })

    it('funciona com um único item', () => {
      const origem = { latitude: 0, longitude: 0 }
      const itens = [{ latitude: 0.05, longitude: 0, id: 'a' }]

      const resultado = ordenarPorDistancia(origem, itens)

      expect(resultado).toHaveLength(1)
      expect(resultado[0].id).toBe('a')
      expect(resultado[0].distanciaKm).toBeGreaterThan(0)
    })
  })
})
