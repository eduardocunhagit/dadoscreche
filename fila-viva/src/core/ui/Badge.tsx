import type { HTMLAttributes } from "react";
import { ESTADOS_OPCAO_LABEL, type EstadoOpcao } from "@/core/domain/constants";

type Tom = "neutro" | "acento" | "bom" | "atencao" | "ruim";

const TONS: Record<Tom, string> = {
  neutro: "bg-surface-2 text-muted",
  acento: "bg-accent-soft text-accent-2",
  bom: "bg-good-soft text-good",
  atencao: "bg-warn-soft text-warn",
  ruim: "bg-bad-soft text-bad",
};

export function Selo({
  tom = "neutro",
  className = "",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tom?: Tom }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold tracking-wide uppercase ${TONS[tom]} ${className}`}
      {...props}
    />
  );
}

const TOM_POR_ESTADO: Record<EstadoOpcao, Tom> = {
  NA_FILA: "neutro",
  OFERTADA: "atencao",
  ACEITA_CONDICIONAL: "acento",
  ACEITA_DEFINITIVA: "bom",
  POSICAO_SUSPENSA: "atencao",
  RECUSADA: "ruim",
  EXPIRADA: "ruim",
  ENCERRADA: "neutro",
};

export function SeloEstadoOpcao({ estado }: { estado: EstadoOpcao }) {
  return <Selo tom={TOM_POR_ESTADO[estado]}>{ESTADOS_OPCAO_LABEL[estado]}</Selo>;
}
