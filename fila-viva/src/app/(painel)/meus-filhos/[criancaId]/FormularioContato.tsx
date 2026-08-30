"use client";

import { useState } from "react";
import { actionAdicionarContato } from "./actions";
import { Botao } from "@/core/ui/Button";
import { Campo, CampoSelect, Rotulo } from "@/core/ui/Input";
import { CANAIS_CONTATO, CANAIS_CONTATO_LABEL } from "@/core/domain/constants";

export function FormularioContato({ criancaId, proximaOrdem }: { criancaId: string; proximaOrdem: number }) {
  const [papel, setPapel] = useState<"RESPONSAVEL" | "ALTERNATIVO">("ALTERNATIVO");

  return (
    <form action={actionAdicionarContato} className="space-y-3">
      <input type="hidden" name="criancaId" value={criancaId} />
      <input type="hidden" name="ordemTentativa" value={proximaOrdem} />

      <div>
        <Rotulo>Tipo de contato</Rotulo>
        <div className="flex gap-4 text-sm text-ink-2">
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="papel"
              value="RESPONSAVEL"
              checked={papel === "RESPONSAVEL"}
              onChange={() => setPapel("RESPONSAVEL")}
            />
            Do responsável
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="papel"
              value="ALTERNATIVO"
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
            <Campo id="nomeContato" name="nomeContato" placeholder="Ex.: Maria" required />
          </div>
          <div>
            <Rotulo htmlFor="parentesco">Parentesco</Rotulo>
            <Campo id="parentesco" name="parentesco" placeholder="Ex.: Avó" required />
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Rotulo htmlFor="canal">Canal</Rotulo>
          <CampoSelect id="canal" name="canal" defaultValue="WHATSAPP" required>
            {CANAIS_CONTATO.map((c) => (
              <option key={c} value={c}>
                {CANAIS_CONTATO_LABEL[c]}
              </option>
            ))}
          </CampoSelect>
        </div>
        <div>
          <Rotulo htmlFor="valor">Número ou e-mail</Rotulo>
          <Campo id="valor" name="valor" placeholder="(21) 90000-0000" required />
        </div>
      </div>

      {papel === "ALTERNATIVO" && (
        <label className="flex items-start gap-2 text-xs text-ink-2">
          <input type="checkbox" name="consentimento" required className="mt-0.5" />
          <span>
            Autorizo a SME-Rio a usar este contato de terceiro apenas para localizar a família quando
            surgir uma vaga na fila de espera desta criança.
          </span>
        </label>
      )}

      <Botao type="submit" variante="secundaria">
        Adicionar contato
      </Botao>
    </form>
  );
}
