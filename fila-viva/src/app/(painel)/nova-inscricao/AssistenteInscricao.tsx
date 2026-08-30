"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Botao } from "@/core/ui/Button";
import { Cartao, CartaoCorpo } from "@/core/ui/Card";
import type { DadosNovaInscricao, EnderecoGeocodificado } from "@/modules/inscricao";
import { cpfValido } from "@/modules/inscricao/dominio/cpf";
import { actionCriarInscricao } from "./actions";
import type { ContatoResumo, DadosDoAssistente } from "./tipos";
import { PassoCrianca, type CriancaLocal } from "./PassoCrianca";
import { PassoContatos } from "./PassoContatos";
import { PassoIdentificacao } from "./PassoIdentificacao";
import { PassoPerguntas } from "./PassoPerguntas";
import { PassoEscolhaCreches, type OpcaoEscolhida } from "./PassoEscolhaCreches";

const PASSOS = ["Criança", "Contatos", "Identificação", "Perguntas", "Creches"] as const;

function enderecoTemGeo(endereco: EnderecoGeocodificado | null): boolean {
  return endereco !== null && endereco.latitude !== undefined && endereco.longitude !== undefined;
}

export function AssistenteInscricao({ dados }: { dados: DadosDoAssistente }) {
  const router = useRouter();

  const [passo, setPasso] = useState(1);

  // Passo 1 — criança
  const [criancas, setCriancas] = useState<CriancaLocal[]>(dados.criancas);
  const [criancaId, setCriancaId] = useState<string | null>(dados.criancas[0]?.id ?? null);

  // Passo 3 — identificação
  const [cpfCrianca, setCpfCrianca] = useState("");
  const [cpfResponsavel, setCpfResponsavel] = useState("");
  const [enderecoResidencia, setEnderecoResidencia] = useState<EnderecoGeocodificado | null>(null);
  const [enderecoTrabalho, setEnderecoTrabalho] = useState<EnderecoGeocodificado | null>(null);
  const [areaSobInfluencia, setAreaSobInfluencia] = useState<boolean | null>(null);
  const [faccaoRelatada, setFaccaoRelatada] = useState("");

  // Passo 4 — perguntas
  const [respostas, setRespostas] = useState<Record<string, "Sim" | "Nao">>({});

  // Passo 5 — escolha de creches
  const [opcoes, setOpcoes] = useState<OpcaoEscolhida[]>([]);

  const [erroServidor, setErroServidor] = useState<string | null>(null);
  const [enviando, iniciarEnvio] = useTransition();

  const criancaAtiva = useMemo(() => criancas.find((c) => c.id === criancaId) ?? null, [criancas, criancaId]);

  function atualizarContatosDaCrianca(contatos: ContatoResumo[]) {
    if (!criancaId) return;
    setCriancas((prev) => prev.map((c) => (c.id === criancaId ? { ...c, contatos } : c)));
  }

  function adicionarCriancaLocal(crianca: CriancaLocal) {
    setCriancas((prev) => [...prev, crianca]);
    setCriancaId(crianca.id);
  }

  const passoValido: Record<number, boolean> = {
    1: criancaId !== null,
    2: (criancaAtiva?.contatos.length ?? 0) >= 1,
    3:
      cpfValido(cpfCrianca) &&
      cpfValido(cpfResponsavel) &&
      enderecoTemGeo(enderecoResidencia) &&
      areaSobInfluencia !== null,
    4: dados.perguntas.length === 0 || dados.perguntas.every((p) => respostas[p.id] !== undefined),
  };

  function irParaProximo() {
    setErroServidor(null);
    setPasso((p) => Math.min(p + 1, PASSOS.length));
  }

  function voltar() {
    setErroServidor(null);
    setPasso((p) => Math.max(p - 1, 1));
  }

  function enviarInscricao() {
    if (!criancaId || !enderecoResidencia || areaSobInfluencia === null) return;

    setErroServidor(null);
    iniciarEnvio(async () => {
      const dadosInscricao: DadosNovaInscricao = {
        criancaId,
        cpfCrianca,
        cpfResponsavel,
        enderecoResidencia,
        enderecoTrabalho,
        contextoSeguranca: {
          areaSobInfluencia,
          faccaoRelatada: faccaoRelatada.trim() || undefined,
        },
        respostas: dados.perguntas.map((p) => ({ perguntaId: p.id, resposta: respostas[p.id] })),
        opcoes,
      };

      const resultado = await actionCriarInscricao(dadosInscricao);
      if (resultado.ok) {
        router.push("/meus-filhos");
      } else {
        setErroServidor(resultado.erro);
      }
    });
  }

  return (
    <div className="space-y-6">
      <ol className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide">
        {PASSOS.map((nome, indice) => {
          const numero = indice + 1;
          const ativo = numero === passo;
          const concluido = numero < passo;
          return (
            <li key={nome} className="flex items-center gap-2">
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  ativo
                    ? "bg-accent text-white"
                    : concluido
                      ? "bg-accent-soft text-accent-2"
                      : "bg-surface-2 text-faint"
                }`}
              >
                {numero}
              </span>
              <span className={ativo ? "text-ink" : "text-muted"}>{nome}</span>
              {numero < PASSOS.length && <span className="text-faint">—</span>}
            </li>
          );
        })}
      </ol>

      <Cartao>
        <CartaoCorpo>
          {passo === 1 && (
            <PassoCrianca
              criancas={criancas}
              criancaIdSelecionada={criancaId}
              onSelecionar={setCriancaId}
              onCriar={adicionarCriancaLocal}
            />
          )}
          {passo === 2 && criancaAtiva && (
            <PassoContatos
              criancaId={criancaAtiva.id}
              contatos={criancaAtiva.contatos}
              onContatosChange={atualizarContatosDaCrianca}
            />
          )}
          {passo === 3 && (
            <PassoIdentificacao
              cpfCrianca={cpfCrianca}
              onCpfCriancaChange={setCpfCrianca}
              cpfResponsavel={cpfResponsavel}
              onCpfResponsavelChange={setCpfResponsavel}
              enderecoResidencia={enderecoResidencia}
              onEnderecoResidenciaChange={setEnderecoResidencia}
              enderecoTrabalho={enderecoTrabalho}
              onEnderecoTrabalhoChange={setEnderecoTrabalho}
              areaSobInfluencia={areaSobInfluencia}
              onAreaSobInfluenciaChange={setAreaSobInfluencia}
              faccaoRelatada={faccaoRelatada}
              onFaccaoRelatadaChange={setFaccaoRelatada}
              bairros={dados.bairros}
            />
          )}
          {passo === 4 && (
            <PassoPerguntas perguntas={dados.perguntas} respostas={respostas} onRespostasChange={setRespostas} />
          )}
          {passo === 5 && (
            <PassoEscolhaCreches
              unidades={dados.unidades}
              enderecoResidencia={enderecoResidencia}
              enderecoTrabalho={enderecoTrabalho}
              opcoes={opcoes}
              onOpcoesChange={setOpcoes}
              onEnviar={enviarInscricao}
              enviando={enviando}
            />
          )}
        </CartaoCorpo>
      </Cartao>

      {erroServidor && (
        <Cartao className="border-bad/40">
          <CartaoCorpo>
            <p className="text-sm text-bad">{erroServidor}</p>
          </CartaoCorpo>
        </Cartao>
      )}

      {passo < PASSOS.length && (
        <div className="flex items-center justify-between">
          <Botao type="button" variante="secundaria" disabled={passo === 1} onClick={voltar}>
            Voltar
          </Botao>
          <Botao type="button" disabled={!passoValido[passo]} onClick={irParaProximo}>
            Avançar
          </Botao>
        </div>
      )}
      {passo === PASSOS.length && (
        <div className="flex justify-start">
          <Botao type="button" variante="secundaria" onClick={voltar}>
            Voltar
          </Botao>
        </div>
      )}
    </div>
  );
}
