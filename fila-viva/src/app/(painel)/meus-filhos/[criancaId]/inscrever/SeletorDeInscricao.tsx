"use client";

import { useEffect, useState, useTransition } from "react";
import { GRUPAMENTOS, TURNOS } from "@/core/domain/constants";
import { Botao } from "@/core/ui/Button";
import { Campo, CampoSelect, Rotulo } from "@/core/ui/Input";
import { actionBuscarUnidades, actionCriarInscricao } from "./actions";

interface Polo {
  id: string;
  nome: string;
}

interface ResultadoUnidade {
  escCodigo: string;
  nome: string;
  bairro: string | null;
}

interface Escolha extends ResultadoUnidade {
  grupamento: string;
  turno: string;
}

const MAX_OPCOES = 5;

export function SeletorDeInscricao({
  criancaId,
  processoId,
  polos,
  grupamentoSugerido,
}: {
  criancaId: string;
  processoId: string;
  polos: Polo[];
  grupamentoSugerido: string;
}) {
  const [poloId, setPoloId] = useState(polos[0]?.id ?? "");
  const [grupamentoPadrao, setGrupamentoPadrao] = useState(grupamentoSugerido);
  const [turnoPadrao, setTurnoPadrao] = useState<string>(TURNOS[0]);
  const [termo, setTermo] = useState("");
  const [resultados, setResultados] = useState<ResultadoUnidade[]>([]);
  const [escolhas, setEscolhas] = useState<Escolha[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [pendente, iniciarTransicao] = useTransition();

  useEffect(() => {
    if (termo.trim().length < 2) return;
    const id = setTimeout(() => {
      actionBuscarUnidades(termo).then(setResultados).catch(() => setResultados([]));
    }, 250);
    return () => clearTimeout(id);
  }, [termo]);

  const resultadosVisiveis = termo.trim().length < 2 ? [] : resultados;

  function adicionar(u: ResultadoUnidade) {
    if (escolhas.length >= MAX_OPCOES) return;
    if (escolhas.some((e) => e.escCodigo === u.escCodigo && e.grupamento === grupamentoPadrao && e.turno === turnoPadrao)) {
      return;
    }
    setEscolhas((atual) => [...atual, { ...u, grupamento: grupamentoPadrao, turno: turnoPadrao }]);
    setTermo("");
    setResultados([]);
  }

  function remover(i: number) {
    setEscolhas((atual) => atual.filter((_, idx) => idx !== i));
  }

  function mover(i: number, delta: number) {
    setEscolhas((atual) => {
      const novo = [...atual];
      const alvo = i + delta;
      if (alvo < 0 || alvo >= novo.length) return atual;
      [novo[i], novo[alvo]] = [novo[alvo], novo[i]];
      return novo;
    });
  }

  function atualizarCampo(i: number, campo: "grupamento" | "turno", valor: string) {
    setEscolhas((atual) => atual.map((e, idx) => (idx === i ? { ...e, [campo]: valor } : e)));
  }

  function enviar() {
    setErro(null);
    if (escolhas.length === 0) {
      setErro("Escolha pelo menos uma unidade.");
      return;
    }
    if (!poloId) {
      setErro("Selecione a CRE de referência.");
      return;
    }
    iniciarTransicao(async () => {
      try {
        await actionCriarInscricao({
          criancaId,
          processoId,
          poloId,
          opcoes: escolhas.map((e) => ({
            unidadeEscCodigo: e.escCodigo,
            grupamento: e.grupamento,
            turno: e.turno,
          })),
        });
      } catch (e) {
        if (e instanceof Error && e.message !== "NEXT_REDIRECT") {
          setErro(e.message);
        }
      }
    });
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Rotulo htmlFor="polo">CRE de referência</Rotulo>
          <CampoSelect id="polo" value={poloId} onChange={(e) => setPoloId(e.target.value)}>
            {polos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </CampoSelect>
        </div>
        <div>
          <Rotulo htmlFor="grupamento-padrao">Grupamento etário</Rotulo>
          <CampoSelect
            id="grupamento-padrao"
            value={grupamentoPadrao}
            onChange={(e) => setGrupamentoPadrao(e.target.value)}
          >
            {GRUPAMENTOS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </CampoSelect>
        </div>
      </div>

      <div>
        <Rotulo htmlFor="turno-padrao">Turno preferido para novas opções</Rotulo>
        <CampoSelect
          id="turno-padrao"
          value={turnoPadrao}
          onChange={(e) => setTurnoPadrao(e.target.value)}
          className="max-w-xs"
        >
          {TURNOS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </CampoSelect>
      </div>

      <div>
        <Rotulo>Opções escolhidas ({escolhas.length}/{MAX_OPCOES}) — em ordem de preferência</Rotulo>
        {escolhas.length === 0 && (
          <p className="rounded-md border border-dashed border-line px-3 py-4 text-sm text-faint">
            Nenhuma unidade escolhida ainda. Busque abaixo e clique para adicionar.
          </p>
        )}
        <ol className="space-y-2">
          {escolhas.map((e, i) => (
            <li key={`${e.escCodigo}-${i}`} className="rounded-md border border-line bg-surface p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-ink">
                    {i + 1}ª — {e.nome}
                  </p>
                  <p className="text-xs text-muted">{e.bairro}</p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => mover(i, -1)}
                    disabled={i === 0}
                    className="rounded border border-line px-2 py-1 text-xs text-ink-2 disabled:opacity-30"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    onClick={() => mover(i, 1)}
                    disabled={i === escolhas.length - 1}
                    className="rounded border border-line px-2 py-1 text-xs text-ink-2 disabled:opacity-30"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => remover(i)}
                    className="rounded border border-line px-2 py-1 text-xs text-bad"
                  >
                    Remover
                  </button>
                </div>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <CampoSelect
                  value={e.grupamento}
                  onChange={(ev) => atualizarCampo(i, "grupamento", ev.target.value)}
                  className="text-xs"
                >
                  {GRUPAMENTOS.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </CampoSelect>
                <CampoSelect
                  value={e.turno}
                  onChange={(ev) => atualizarCampo(i, "turno", ev.target.value)}
                  className="text-xs"
                >
                  {TURNOS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </CampoSelect>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {escolhas.length < MAX_OPCOES && (
        <div>
          <Rotulo htmlFor="busca-unidade">Buscar creche por nome ou bairro</Rotulo>
          <Campo
            id="busca-unidade"
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="Ex.: Vila Isabel, ou CM Ladeira"
          />
          {resultadosVisiveis.length > 0 && (
            <ul className="mt-2 max-h-64 divide-y divide-line overflow-y-auto rounded-md border border-line bg-surface">
              {resultadosVisiveis.map((u) => (
                <li key={u.escCodigo}>
                  <button
                    type="button"
                    onClick={() => adicionar(u)}
                    className="block w-full px-3 py-2 text-left text-sm text-ink hover:bg-surface-2"
                  >
                    <span className="font-medium">{u.nome}</span>
                    {u.bairro && <span className="text-muted"> — {u.bairro}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {erro && <p className="rounded-md bg-bad-soft px-3 py-2 text-sm text-bad">{erro}</p>}

      <Botao type="button" onClick={enviar} disabled={pendente}>
        {pendente ? "Enviando…" : "Confirmar inscrição"}
      </Botao>
    </div>
  );
}
