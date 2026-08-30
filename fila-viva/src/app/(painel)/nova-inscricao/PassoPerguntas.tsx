"use client";

import { Selo } from "@/core/ui/Badge";

interface PassoPerguntasProps {
  perguntas: { id: string; texto: string; pontuacao: number }[];
  respostas: Record<string, "Sim" | "Nao">;
  onRespostasChange: (respostas: Record<string, "Sim" | "Nao">) => void;
}

export function PassoPerguntas({ perguntas, respostas, onRespostasChange }: PassoPerguntasProps) {
  function responder(perguntaId: string, resposta: "Sim" | "Nao") {
    onRespostasChange({ ...respostas, [perguntaId]: resposta });
  }

  return (
    <div className="space-y-3">
      {perguntas.length === 0 && <p className="text-sm text-muted">Nenhuma pergunta cadastrada para este processo.</p>}
      {perguntas.map((p) => (
        <div key={p.id} className="space-y-2 rounded-md border border-line p-4">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-ink">{p.texto}</p>
            <Selo tom="neutro">{p.pontuacao} pts</Selo>
          </div>
          <div className="flex gap-4 text-sm text-ink-2">
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name={`pergunta-${p.id}`}
                checked={respostas[p.id] === "Sim"}
                onChange={() => responder(p.id, "Sim")}
              />
              Sim
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name={`pergunta-${p.id}`}
                checked={respostas[p.id] === "Nao"}
                onChange={() => responder(p.id, "Nao")}
              />
              Não
            </label>
          </div>
        </div>
      ))}
    </div>
  );
}
