"use client";

import { useState } from "react";
import { Botao } from "@/core/ui/Button";
import { Campo, CampoSelect, Rotulo } from "@/core/ui/Input";
import { Selo } from "@/core/ui/Badge";
import { CANAIS_CONTATO, CANAIS_CONTATO_LABEL } from "@/core/domain/constants";
import { actionAdicionarContatoInscricao } from "./actions";
import type { ContatoResumo } from "./tipos";

interface PassoContatosProps {
  criancaId: string;
  contatos: ContatoResumo[];
  onContatosChange: (contatos: ContatoResumo[]) => void;
}

export function PassoContatos({ criancaId, contatos, onContatosChange }: PassoContatosProps) {
  const [canal, setCanal] = useState<(typeof CANAIS_CONTATO)[number]>("WHATSAPP");
  const [valor, setValor] = useState("");
  const [papel, setPapel] = useState<"RESPONSAVEL" | "ALTERNATIVO">("RESPONSAVEL");
  const [nomeContato, setNomeContato] = useState("");
  const [parentesco, setParentesco] = useState("");
  const [consentimento, setConsentimento] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const podeAdicionar =
    valor.trim().length > 0 &&
    (papel === "RESPONSAVEL" || (nomeContato.trim().length > 0 && parentesco.trim().length > 0 && consentimento));

  async function adicionarContato() {
    if (!podeAdicionar) return;
    setEnviando(true);
    setErro(null);
    try {
      const { contatos: novosContatos } = await actionAdicionarContatoInscricao({
        criancaId,
        canal,
        valor: valor.trim(),
        papel,
        nomeContato: papel === "ALTERNATIVO" ? nomeContato.trim() : undefined,
        parentesco: papel === "ALTERNATIVO" ? parentesco.trim() : undefined,
        consentimento: papel === "ALTERNATIVO" ? consentimento : undefined,
      });
      onContatosChange(novosContatos);
      setValor("");
      setNomeContato("");
      setParentesco("");
      setConsentimento(false);
    } catch {
      setErro("Não foi possível adicionar o contato. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Rotulo>Contatos cadastrados</Rotulo>
        {contatos.length === 0 && <p className="text-sm text-muted">Nenhum contato ainda.</p>}
        <div className="space-y-2">
          {contatos.map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-2 rounded-md border border-line p-3 text-sm">
              <Selo tom={c.papel === "ALTERNATIVO" ? "acento" : "neutro"}>
                {c.papel === "ALTERNATIVO" ? "Alternativo" : "Responsável"}
              </Selo>
              <Selo tom="neutro">
                {CANAIS_CONTATO_LABEL[c.canal as keyof typeof CANAIS_CONTATO_LABEL] ?? c.canal}
              </Selo>
              <span className="text-ink-2">{c.valor}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3 rounded-md border border-line p-4">
        <p className="text-sm font-medium text-ink">Adicionar contato</p>

        <div>
          <Rotulo>Tipo de contato</Rotulo>
          <div className="flex gap-4 text-sm text-ink-2">
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="papel-contato"
                checked={papel === "RESPONSAVEL"}
                onChange={() => setPapel("RESPONSAVEL")}
              />
              Do responsável
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="papel-contato"
                checked={papel === "ALTERNATIVO"}
                onChange={() => setPapel("ALTERNATIVO")}
              />
              Contato alternativo (terceiro)
            </label>
          </div>
        </div>

        {papel === "ALTERNATIVO" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Rotulo htmlFor="nomeContato">Nome</Rotulo>
              <Campo
                id="nomeContato"
                value={nomeContato}
                onChange={(e) => setNomeContato(e.target.value)}
                placeholder="Ex.: Maria"
              />
            </div>
            <div>
              <Rotulo htmlFor="parentesco">Parentesco</Rotulo>
              <Campo
                id="parentesco"
                value={parentesco}
                onChange={(e) => setParentesco(e.target.value)}
                placeholder="Ex.: Avó"
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Rotulo htmlFor="canal">Canal</Rotulo>
            <CampoSelect
              id="canal"
              value={canal}
              onChange={(e) => setCanal(e.target.value as (typeof CANAIS_CONTATO)[number])}
            >
              {CANAIS_CONTATO.map((c) => (
                <option key={c} value={c}>
                  {CANAIS_CONTATO_LABEL[c]}
                </option>
              ))}
            </CampoSelect>
          </div>
          <div>
            <Rotulo htmlFor="valor">Número ou e-mail</Rotulo>
            <Campo id="valor" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="(21) 90000-0000" />
          </div>
        </div>

        {papel === "ALTERNATIVO" && (
          <label className="flex items-start gap-2 text-xs text-ink-2">
            <input
              type="checkbox"
              checked={consentimento}
              onChange={(e) => setConsentimento(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              Autorizo a SME-Rio a usar este contato de terceiro apenas para localizar a família quando
              surgir uma vaga na fila de espera desta criança.
            </span>
          </label>
        )}

        {erro && <p className="text-sm text-bad">{erro}</p>}

        <Botao type="button" variante="secundaria" disabled={!podeAdicionar || enviando} onClick={adicionarContato}>
          {enviando ? "Adicionando..." : "Adicionar contato"}
        </Botao>
      </div>
    </div>
  );
}
