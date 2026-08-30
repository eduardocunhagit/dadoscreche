"use client";

import { useMemo, useState } from "react";
import { Botao } from "@/core/ui/Button";
import { Campo, CampoSelect, Rotulo } from "@/core/ui/Input";
import type { UnidadeParaEscolha, EnderecoGeocodificado } from "@/modules/inscricao";
import { normalizarBairro, ordenarPorDistancia, type Ponto } from "@/modules/inscricao/dominio/geo";
import { alternarEscolha, moverPosicao, LIMITE_OPCOES } from "@/modules/inscricao/dominio/ordenacao";
import { SeloDemanda } from "./SeloDemanda";

export interface OpcaoEscolhida {
  unidadeEscCodigo: string;
  turno: "Integral" | "Parcial";
}

const MAX_LISTADAS = 20;

function pontoDoEndereco(endereco: EnderecoGeocodificado | null): Ponto | null {
  if (!endereco || endereco.latitude === undefined || endereco.longitude === undefined) return null;
  return { latitude: endereco.latitude, longitude: endereco.longitude };
}

/**
 * Demanda excedente prevista pelo modelo da frente 2 (gap / oferta do ano
 * anterior). Só destacamos quando a demanda supera a oferta — o selo de
 * classe já resume o resto.
 */
function ExcedenteDemanda({ valor }: { valor: number | null }) {
  // < 0,5% arredondaria para "+0%" — abaixo disso o selo de classe basta.
  if (valor === null || valor < 0.005) return null;
  return (
    <span className="text-xs text-muted">+{Math.round(valor * 100)}% acima da oferta</span>
  );
}

interface PassoEscolhaCrechesProps {
  unidades: UnidadeParaEscolha[];
  enderecoResidencia: EnderecoGeocodificado | null;
  enderecoTrabalho: EnderecoGeocodificado | null;
  opcoes: OpcaoEscolhida[];
  onOpcoesChange: (opcoes: OpcaoEscolhida[]) => void;
  onEnviar: () => void;
  enviando: boolean;
}

export function PassoEscolhaCreches({
  unidades,
  enderecoResidencia,
  enderecoTrabalho,
  opcoes,
  onOpcoesChange,
  onEnviar,
  enviando,
}: PassoEscolhaCrechesProps) {
  const [origem, setOrigem] = useState<"residencia" | "trabalho" | "livre">("residencia");
  const [buscaSemGeo, setBuscaSemGeo] = useState("");
  const [buscaLivre, setBuscaLivre] = useState("");
  const [arrastandoIndice, setArrastandoIndice] = useState<number | null>(null);

  const pontoResidencia = pontoDoEndereco(enderecoResidencia);
  const pontoTrabalho = pontoDoEndereco(enderecoTrabalho);
  const pontoOrigem =
    origem === "residencia" ? pontoResidencia : origem === "trabalho" ? pontoTrabalho : null;

  const porCodigo = useMemo(() => new Map(unidades.map((u) => [u.escCodigo, u])), [unidades]);

  const unidadesComGeo = useMemo(
    () =>
      unidades.filter(
        (u): u is UnidadeParaEscolha & { latitude: number; longitude: number } =>
          u.latitude !== null && u.longitude !== null
      ),
    [unidades]
  );

  const unidadesSemGeo = useMemo(
    () =>
      unidades
        .filter((u) => u.latitude === null || u.longitude === null)
        .filter((u) => u.nome.toLowerCase().includes(buscaSemGeo.trim().toLowerCase()))
        .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")),
    [unidades, buscaSemGeo]
  );

  const unidadesOrdenadas = useMemo(() => {
    if (!pontoOrigem) return [];
    return ordenarPorDistancia(pontoOrigem, unidadesComGeo).slice(0, MAX_LISTADAS);
  }, [pontoOrigem, unidadesComGeo]);

  // Busca livre: filtra TODAS as unidades (com e sem geo) por nome ou bairro,
  // sem acento e sem caixa; quando a residência tem ponto, anexa a distância
  // até ela só como referência.
  const unidadesLivre = useMemo(() => {
    if (origem !== "livre") return [];
    const termo = normalizarBairro(buscaLivre);
    if (termo.length < 2) return [];
    const filtradas = unidades
      .filter(
        (u) => normalizarBairro(u.nome).includes(termo) || normalizarBairro(u.bairro ?? "").includes(termo)
      )
      .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
      .slice(0, MAX_LISTADAS);
    return filtradas.map((u) => ({
      ...u,
      distanciaKm:
        pontoResidencia && u.latitude !== null && u.longitude !== null
          ? ordenarPorDistancia(pontoResidencia, [{ latitude: u.latitude, longitude: u.longitude }])[0]
              .distanciaKm
          : null,
    }));
  }, [origem, buscaLivre, unidades, pontoResidencia]);

  function estaEscolhida(escCodigo: string) {
    return opcoes.some((o) => o.unidadeEscCodigo === escCodigo);
  }

  function alternar(escCodigo: string) {
    const nova = alternarEscolha<OpcaoEscolhida>(
      opcoes,
      { unidadeEscCodigo: escCodigo, turno: "Integral" },
      (a, b) => a.unidadeEscCodigo === b.unidadeEscCodigo
    );
    onOpcoesChange(nova);
  }

  function atualizarTurno(indice: number, turno: "Integral" | "Parcial") {
    onOpcoesChange(opcoes.map((o, i) => (i === indice ? { ...o, turno } : o)));
  }

  function remover(indice: number) {
    onOpcoesChange(opcoes.filter((_, i) => i !== indice));
  }

  function mover(indice: number, delta: number) {
    onOpcoesChange(moverPosicao(opcoes, indice, indice + delta));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-[260px]">
          <Rotulo htmlFor="origem-proximidade">Como encontrar as creches:</Rotulo>
          <CampoSelect
            id="origem-proximidade"
            value={origem}
            onChange={(e) => setOrigem(e.target.value as "residencia" | "trabalho" | "livre")}
          >
            <option value="residencia">Perto da residência</option>
            <option value="trabalho" disabled={!pontoTrabalho}>
              Perto do trabalho
            </option>
            <option value="livre">Busca livre (nome ou bairro)</option>
          </CampoSelect>
        </div>
        <p className="text-sm font-medium text-ink-2">
          {opcoes.length} de {LIMITE_OPCOES} escolhidas
        </p>
      </div>

      {origem === "livre" && (
        <div className="space-y-2">
          <Campo
            value={buscaLivre}
            onChange={(e) => setBuscaLivre(e.target.value)}
            placeholder="Digite o nome da creche ou o bairro (ex.: Copacabana)"
            autoFocus
          />
          {buscaLivre.trim().length < 2 && (
            <p className="text-sm text-muted">Digite pelo menos 2 letras para ver as opções.</p>
          )}
          {buscaLivre.trim().length >= 2 && unidadesLivre.length === 0 && (
            <p className="text-sm text-muted">Nenhuma unidade encontrada com esse nome ou bairro.</p>
          )}
          {unidadesLivre.map((u) => {
            const escolhida = estaEscolhida(u.escCodigo);
            const cheio = opcoes.length >= LIMITE_OPCOES;
            return (
              <div
                key={u.escCodigo}
                className="flex flex-wrap items-center gap-3 rounded-md border border-line p-3 text-sm"
              >
                <div className="min-w-[200px] flex-1">
                  <p className="font-medium text-ink">{u.nome}</p>
                  <p className="text-xs text-muted">{u.bairro ?? "Bairro não informado"}</p>
                </div>
                {u.distanciaKm !== null && (
                  <span className="text-xs text-ink-2">
                    {u.distanciaKm.toFixed(1).replace(".", ",")} km de casa
                  </span>
                )}
                <SeloDemanda classe={u.demanda} />
                <ExcedenteDemanda valor={u.demandaExcedente} />
                <Botao
                  type="button"
                  variante={escolhida ? "perigo" : "secundaria"}
                  disabled={!escolhida && cheio}
                  onClick={() => alternar(u.escCodigo)}
                >
                  {escolhida ? "Remover" : "Adicionar"}
                </Botao>
              </div>
            );
          })}
        </div>
      )}

      {origem !== "livre" && (
        <div className="space-y-2">
          {unidadesOrdenadas.length === 0 && (
            <p className="text-sm text-muted">Nenhuma unidade com localização conhecida para ordenar.</p>
          )}
          {unidadesOrdenadas.map((u) => {
            const escolhida = estaEscolhida(u.escCodigo);
            const cheio = opcoes.length >= LIMITE_OPCOES;
            return (
              <div
                key={u.escCodigo}
                className="flex flex-wrap items-center gap-3 rounded-md border border-line p-3 text-sm"
              >
                <div className="min-w-[200px] flex-1">
                  <p className="font-medium text-ink">{u.nome}</p>
                  <p className="text-xs text-muted">{u.bairro ?? "Bairro não informado"}</p>
                </div>
                <span className="text-xs text-ink-2">{u.distanciaKm.toFixed(1).replace(".", ",")} km</span>
                <SeloDemanda classe={u.demanda} />
                <ExcedenteDemanda valor={u.demandaExcedente} />
                <Botao
                  type="button"
                  variante={escolhida ? "perigo" : "secundaria"}
                  disabled={!escolhida && cheio}
                  onClick={() => alternar(u.escCodigo)}
                >
                  {escolhida ? "Remover" : "Adicionar"}
                </Botao>
              </div>
            );
          })}
        </div>
      )}

      {origem !== "livre" && (
      <details className="rounded-md border border-line p-3">
        <summary className="cursor-pointer text-sm font-medium text-ink">
          Unidades sem localização conhecida
        </summary>
        <div className="mt-3 space-y-3">
          <Campo
            value={buscaSemGeo}
            onChange={(e) => setBuscaSemGeo(e.target.value)}
            placeholder="Buscar por nome"
          />
          <div className="space-y-2">
            {unidadesSemGeo.map((u) => {
              const escolhida = estaEscolhida(u.escCodigo);
              const cheio = opcoes.length >= LIMITE_OPCOES;
              return (
                <div
                  key={u.escCodigo}
                  className="flex flex-wrap items-center gap-3 rounded-md border border-line p-3 text-sm"
                >
                  <div className="min-w-[200px] flex-1">
                    <p className="font-medium text-ink">{u.nome}</p>
                    <p className="text-xs text-muted">{u.bairro ?? "Bairro não informado"}</p>
                  </div>
                  <SeloDemanda classe={u.demanda} />
                  <Botao
                    type="button"
                    variante={escolhida ? "perigo" : "secundaria"}
                    disabled={!escolhida && cheio}
                    onClick={() => alternar(u.escCodigo)}
                  >
                    {escolhida ? "Remover" : "Adicionar"}
                  </Botao>
                </div>
              );
            })}
            {unidadesSemGeo.length === 0 && <p className="text-sm text-muted">Nenhuma unidade encontrada.</p>}
          </div>
        </div>
      </details>
      )}

      <div className="space-y-2">
        <Rotulo>Ordem de preferência</Rotulo>
        {opcoes.length === 0 && <p className="text-sm text-muted">Escolha ao menos uma creche acima.</p>}
        <ol className="space-y-2">
          {opcoes.map((opcao, indice) => {
            const unidade = porCodigo.get(opcao.unidadeEscCodigo);
            return (
              <li
                key={opcao.unidadeEscCodigo}
                draggable
                onDragStart={() => setArrastandoIndice(indice)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (arrastandoIndice !== null) {
                    onOpcoesChange(moverPosicao(opcoes, arrastandoIndice, indice));
                  }
                  setArrastandoIndice(null);
                }}
                className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface p-3 text-sm"
              >
                <span className="w-6 text-center font-semibold text-accent">{indice + 1}ª</span>
                <span className="min-w-[180px] flex-1 font-medium text-ink">
                  {unidade?.nome ?? opcao.unidadeEscCodigo}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label="Subir posição"
                    disabled={indice === 0}
                    onClick={() => mover(indice, -1)}
                    className="rounded px-2 py-1 text-ink-2 hover:bg-surface-2 disabled:opacity-30"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    aria-label="Descer posição"
                    disabled={indice === opcoes.length - 1}
                    onClick={() => mover(indice, 1)}
                    className="rounded px-2 py-1 text-ink-2 hover:bg-surface-2 disabled:opacity-30"
                  >
                    ↓
                  </button>
                </div>
                <CampoSelect
                  className="max-w-[140px]"
                  value={opcao.turno}
                  onChange={(e) => atualizarTurno(indice, e.target.value as "Integral" | "Parcial")}
                >
                  <option value="Integral">Integral</option>
                  <option value="Parcial">Parcial</option>
                </CampoSelect>
                <Botao type="button" variante="fantasma" className="text-bad hover:bg-bad-soft" onClick={() => remover(indice)}>
                  Remover
                </Botao>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="flex items-center justify-between border-t border-line pt-4">
        <p className="text-sm text-ink-2">
          {opcoes.length === 0
            ? "Escolha ao menos uma creche para enviar a inscrição."
            : `${opcoes.length} creche${opcoes.length === 1 ? "" : "s"} na ordem de preferência acima.`}
        </p>
        <Botao type="button" disabled={opcoes.length === 0 || enviando} onClick={onEnviar}>
          {enviando ? "Enviando..." : "Enviar inscrição"}
        </Botao>
      </div>
    </div>
  );
}
