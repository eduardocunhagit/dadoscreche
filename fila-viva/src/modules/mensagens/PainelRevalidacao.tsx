"use client";

import Link from "next/link";
import { useActionState, useMemo, useState } from "react";
import { Botao } from "@/core/ui/Button";
import { Cartao, CartaoCorpo, CartaoTitulo } from "@/core/ui/Card";
import { Selo } from "@/core/ui/Badge";
import { actionEnviarMensagens } from "./actions";
import { ESTADO_INICIAL_MENSAGENS } from "./tipos";
import type { StatusComunicacao } from "./servico";

export interface ContatoRevalidacao {
  id: string;
  papel: string;
  nomeContato: string | null;
  parentesco: string | null;
  canal: string;
  valor: string;
  ordemTentativa: number;
  verificadoEm: string | null;
  consentimentoEm: string | null;
}

export interface CriancaRevalidacao {
  id: string;
  nomeExibicao: string;
  responsavelNome: string;
  contatos: ContatoRevalidacao[];
  statusComunicacao: StatusComunicacao;
}

const MENSAGEM_PADRAO =
  "Olá! Aqui é da equipe da Fila Viva. Estamos confirmando se este WhatsApp continua sendo o melhor contato para falar sobre a inscrição de {crianca}. Por favor, responda a esta mensagem.";

const STATUS: Record<StatusComunicacao, { label: string; tom: "neutro" | "bom" | "atencao" | "ruim" }> = {
  NAO_ENVIADA: { label: "Não enviada", tom: "neutro" },
  ENVIADA: { label: "Enviada", tom: "atencao" },
  RESPONDIDA: { label: "Respondida", tom: "bom" },
  ERRO: { label: "Erro no envio", tom: "ruim" },
};

function formatarData(data: string | null) {
  if (!data) return "nunca";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(data));
}

function contatosWhatsapp(crianca: CriancaRevalidacao) {
  return crianca.contatos.filter(
    (contato) =>
      contato.canal === "WHATSAPP" &&
      (contato.papel !== "ALTERNATIVO" || contato.consentimentoEm !== null)
  );
}

function nomeContato(contato: ContatoRevalidacao, responsavelNome: string) {
  if (contato.papel !== "ALTERNATIVO") return responsavelNome;
  return `${contato.parentesco ?? "Contato alternativo"} — ${contato.nomeContato ?? "sem nome"}`;
}

export function PainelRevalidacao({ criancas }: { criancas: CriancaRevalidacao[] }) {
  const elegiveis = useMemo(
    () => criancas.filter((crianca) => contatosWhatsapp(crianca).length > 0),
    [criancas]
  );
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set());
  const [preparando, setPreparando] = useState(false);
  const [contatoPorCrianca, setContatoPorCrianca] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      elegiveis.map((crianca) => [crianca.id, contatosWhatsapp(crianca)[0]!.id])
    )
  );
  const [estado, formAction, pendente] = useActionState(
    actionEnviarMensagens,
    ESTADO_INICIAL_MENSAGENS
  );

  const todasSelecionadas =
    elegiveis.length > 0 && elegiveis.every((crianca) => selecionadas.has(crianca.id));
  const criancasSelecionadas = criancas.filter((crianca) => selecionadas.has(crianca.id));
  const destinatarios = criancasSelecionadas.map((crianca) => ({
    criancaId: crianca.id,
    contatoId: contatoPorCrianca[crianca.id] ?? contatosWhatsapp(crianca)[0]!.id,
  }));

  function alternarCrianca(crianca: CriancaRevalidacao) {
    if (contatosWhatsapp(crianca).length === 0) return;
    setSelecionadas((atuais) => {
      const proximas = new Set(atuais);
      if (proximas.has(crianca.id)) proximas.delete(crianca.id);
      else proximas.add(crianca.id);
      return proximas;
    });
  }

  function alternarTodas() {
    setSelecionadas(
      todasSelecionadas ? new Set() : new Set(elegiveis.map((crianca) => crianca.id))
    );
  }

  return (
    <div className="space-y-4">
      <Cartao>
        <CartaoCorpo className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-ink">
            <input
              type="checkbox"
              checked={todasSelecionadas}
              onChange={alternarTodas}
              disabled={elegiveis.length === 0}
              className="h-4 w-4 accent-accent"
            />
            Selecionar todas com WhatsApp
          </label>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted">{selecionadas.size} selecionada(s)</span>
            <Botao
              type="button"
              disabled={selecionadas.size === 0}
              onClick={() => setPreparando(true)}
            >
              Enviar mensagem
            </Botao>
          </div>
        </CartaoCorpo>
      </Cartao>

      {preparando && criancasSelecionadas.length > 0 && (
        <Cartao className="border-accent/40">
          <CartaoTitulo>Confirmar mensagens</CartaoTitulo>
          <CartaoCorpo>
            <form action={formAction} className="space-y-5">
              <input type="hidden" name="destinatarios" value={JSON.stringify(destinatarios)} />

              <div className="space-y-3">
                {criancasSelecionadas.map((crianca) => (
                  <div
                    key={crianca.id}
                    className="grid gap-2 rounded-md border border-line p-3 md:grid-cols-[1fr_2fr] md:items-center"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink">{crianca.nomeExibicao}</p>
                      <p className="text-xs text-muted">{crianca.responsavelNome}</p>
                    </div>
                    <select
                      value={contatoPorCrianca[crianca.id]}
                      onChange={(evento) =>
                        setContatoPorCrianca((atuais) => ({
                          ...atuais,
                          [crianca.id]: evento.target.value,
                        }))
                      }
                      className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                      aria-label={`WhatsApp para ${crianca.nomeExibicao}`}
                    >
                      {contatosWhatsapp(crianca).map((contato) => (
                        <option key={contato.id} value={contato.id}>
                          {nomeContato(contato, crianca.responsavelNome)} · {contato.valor}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              <div>
                <label
                  htmlFor="mensagem-whatsapp"
                  className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  Mensagem
                </label>
                <textarea
                  id="mensagem-whatsapp"
                  name="mensagem"
                  defaultValue={MENSAGEM_PADRAO}
                  rows={5}
                  required
                  className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <p className="mt-1 text-xs text-faint">
                  O campo {"{crianca}"} será substituído pelo nome de cada criança.
                </p>
              </div>

              <div className="rounded-md bg-accent-soft p-3 text-sm text-ink-2">
                Modo de demonstração: nenhuma mensagem será enviada para o WhatsApp real.
              </div>

              {estado.mensagem && (
                <p className={`text-sm ${estado.ok ? "text-good" : "text-bad"}`} aria-live="polite">
                  {estado.mensagem}
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <Botao type="submit" disabled={pendente}>
                  {pendente ? "Enviando..." : `Confirmar envio para ${selecionadas.size}`}
                </Botao>
                <Botao type="button" variante="fantasma" onClick={() => setPreparando(false)}>
                  Cancelar
                </Botao>
              </div>
            </form>
          </CartaoCorpo>
        </Cartao>
      )}

      <div className="space-y-3">
        {criancas.map((crianca) => {
          const whatsapps = contatosWhatsapp(crianca);
          const selecionavel = whatsapps.length > 0;
          const status = STATUS[crianca.statusComunicacao];

          return (
            <Cartao key={crianca.id} className="transition-colors hover:border-accent">
              <CartaoCorpo className="flex flex-wrap items-center gap-4">
                <input
                  type="checkbox"
                  checked={selecionadas.has(crianca.id)}
                  onChange={() => alternarCrianca(crianca)}
                  disabled={!selecionavel}
                  aria-label={`Selecionar ${crianca.nomeExibicao}`}
                  className="h-4 w-4 accent-accent"
                />

                <Link href={`/meus-filhos/${crianca.id}`} className="min-w-52 flex-1">
                  <p className="font-medium text-ink">{crianca.nomeExibicao}</p>
                  <p className="text-xs text-muted">Responsável: {crianca.responsavelNome}</p>
                </Link>

                <div className="flex flex-wrap items-center justify-end gap-1.5">
                  <Selo tom={status.tom}>{status.label}</Selo>
                  {crianca.contatos.map((contato) => (
                    <Selo key={contato.id} tom={contato.verificadoEm ? "neutro" : "atencao"}>
                      {contato.canal} · {formatarData(contato.verificadoEm)}
                    </Selo>
                  ))}
                </div>
              </CartaoCorpo>
            </Cartao>
          );
        })}
      </div>
    </div>
  );
}
