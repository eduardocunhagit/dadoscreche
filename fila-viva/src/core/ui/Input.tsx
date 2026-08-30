import { type InputHTMLAttributes, type SelectHTMLAttributes, forwardRef } from "react";

const CAMPO_CLASSES =
  "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-faint " +
  "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:bg-surface-2 disabled:text-faint";

export const Campo = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Campo({ className = "", ...props }, ref) {
    return <input ref={ref} className={`${CAMPO_CLASSES} ${className}`} {...props} />;
  }
);

export const CampoSelect = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function CampoSelect({ className = "", ...props }, ref) {
    return <select ref={ref} className={`${CAMPO_CLASSES} ${className}`} {...props} />;
  }
);

export function Rotulo({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
      {children}
    </label>
  );
}
