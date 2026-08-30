"use client";

import { useState } from "react";
import { Botao } from "@/core/ui/Button";
import { Campo, CampoSelect, Rotulo } from "@/core/ui/Input";
import { actionCriarCrianca } from "./actions";
import type { ContatoResumo } from "./tipos";

export interface CriancaLocal {
  id: string;
  nomeExibicao: string;
  nascimentoAnoMes: string;
  contatos: ContatoResumo[];
}

interface PassoCriancaProps {
  criancas: CriancaLocal[];
  criancaIdSelecionada: string | null;
  onSelecionar: (id: string) => void;
  onCriar: (crianca: CriancaLocal) => void;
}

export function PassoCrianca({ criancas, criancaIdSelecionada, onSelecionar, onCriar }: PassoCriancaProps) {
  const [modo, setModo] = useState<"existente" | "nova">(criancas.length > 0 ? "existente" : "nova");
  const [nomeExibicao, setNomeExibicao] = useState("");
  const [sexo, setSexo] = useState<"M" | "F">("F");
  const [nascimentoAnoMes, setNascimentoAnoMes] = useState("");
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function criarCrianca() {
    const nome = nomeExibicao.trim();
    if (!nome || !nascimentoAnoMes) return;

    setCriando(true);
    setErro(null);
    try {
      const { criancaId } = await actionCriarCrianca({ nomeExibicao: nome, sexo, nascimentoAnoMes });
      onCriar({ id: criancaId, nomeExibicao: nome, nascimentoAnoMes, contatos: [] });
      setModo("existente");
      setNomeExibicao("");
      setNascimentoAnoMes("");
      setSexo("F");
    } catch {
      setErro("Não foi possível cadastrar a criança. Tente novamente.");
    } finally {
      setCriando(false);
    }
  }

  return (
    <div className="space-y-5">
      {criancas.length > 0 && (
        <div className="space-y-2">
          <Rotulo>Para qual criança é esta inscrição?</Rotulo>
          <div className="space-y-2">
            {criancas.map((c) => {
              const selecionada = modo === "existente" && criancaIdSelecionada === c.id;
              return (
                <label
                  key={c.id}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm ${
                    selecionada ? "border-accent bg-accent-soft" : "border-line"
                  }`}
                >
                  <input
                    type="radio"
                    name="crianca-existente"
                    checked={selecionada}
                    onChange={() => {
                      setModo("existente");
                      onSelecionar(c.id);
                    }}
                  />
                  <span className="flex-1">
                    <span className="font-medium text-ink">{c.nomeExibicao}</span>
                    <span className="ml-2 text-muted">Nascimento: {c.nascimentoAnoMes}</span>
                    <span className="ml-2 text-faint">
                      {c.contatos.length} contato{c.contatos.length === 1 ? "" : "s"}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
          {modo !== "nova" && (
            <button
              type="button"
              className="text-xs font-medium text-accent hover:underline"
              onClick={() => setModo("nova")}
            >
              + Cadastrar outra criança
            </button>
          )}
        </div>
      )}

      {modo === "nova" && (
        <div className="space-y-3 rounded-md border border-line p-4">
          <p className="text-sm font-medium text-ink">Cadastrar nova criança</p>
          <div>
            <Rotulo htmlFor="nomeExibicao">Nome</Rotulo>
            <Campo
              id="nomeExibicao"
              value={nomeExibicao}
              onChange={(e) => setNomeExibicao(e.target.value)}
              placeholder="Nome da criança"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Rotulo htmlFor="sexo">Sexo</Rotulo>
              <CampoSelect id="sexo" value={sexo} onChange={(e) => setSexo(e.target.value as "M" | "F")}>
                <option value="F">Feminino</option>
                <option value="M">Masculino</option>
              </CampoSelect>
            </div>
            <div>
              <Rotulo htmlFor="nascimentoAnoMes">Nascimento</Rotulo>
              <Campo
                id="nascimentoAnoMes"
                type="month"
                value={nascimentoAnoMes}
                onChange={(e) => setNascimentoAnoMes(e.target.value)}
              />
            </div>
          </div>
          {erro && <p className="text-sm text-bad">{erro}</p>}
          <Botao
            type="button"
            variante="secundaria"
            disabled={criando || !nomeExibicao.trim() || !nascimentoAnoMes}
            onClick={criarCrianca}
          >
            {criando ? "Cadastrando..." : "Cadastrar criança"}
          </Botao>
        </div>
      )}
    </div>
  );
}
