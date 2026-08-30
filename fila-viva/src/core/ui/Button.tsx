import { type ButtonHTMLAttributes, forwardRef } from "react";

type Variante = "primaria" | "secundaria" | "perigo" | "fantasma";

const VARIANTES: Record<Variante, string> = {
  primaria: "bg-accent text-white hover:bg-accent-2 disabled:bg-line disabled:text-faint",
  secundaria:
    "bg-surface text-ink border border-line hover:border-line-2 disabled:text-faint",
  perigo: "bg-bad text-white hover:opacity-90 disabled:bg-line disabled:text-faint",
  fantasma: "text-accent hover:bg-accent-soft disabled:text-faint",
};

export interface BotaoProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
}

export const Botao = forwardRef<HTMLButtonElement, BotaoProps>(function Botao(
  { variante = "primaria", className = "", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium
        transition-colors disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2
        focus-visible:outline-offset-2 focus-visible:outline-accent ${VARIANTES[variante]} ${className}`}
      {...props}
    />
  );
});
