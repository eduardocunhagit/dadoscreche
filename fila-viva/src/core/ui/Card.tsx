import type { HTMLAttributes } from "react";

export function Cartao({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-line bg-surface shadow-sm ${className}`}
      {...props}
    />
  );
}

export function CartaoTitulo({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`border-b border-line px-5 py-3.5 font-serif text-lg leading-tight text-ink ${className}`}
      {...props}
    />
  );
}

export function CartaoCorpo({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`p-5 ${className}`} {...props} />;
}
