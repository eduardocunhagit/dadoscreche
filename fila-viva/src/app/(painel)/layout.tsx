import { redirect } from "next/navigation";
import Link from "next/link";
import { auth } from "@/core/auth";
import { PAPEIS_USUARIO_LABEL } from "@/core/domain/constants";
import { menuParaPapel } from "@/modules/registry";
import { sair } from "./actions";

export default async function LayoutDoPainel({ children }: LayoutProps<"/">) {
  const session = await auth();
  if (!session?.user) redirect("/login");

  const itens = menuParaPapel(session.user.papel);

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-surface">
        <div className="border-b border-line px-5 py-5">
          <p className="text-xs font-semibold uppercase tracking-widest text-accent">Inscrição Creche</p>
          <p className="font-serif text-xl text-ink">Fila Viva</p>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-4">
          <Link
            href="/"
            className="block rounded-md px-3 py-2 text-sm font-medium text-ink-2 hover:bg-surface-2"
          >
            Início
          </Link>
          {itens.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-md px-3 py-2 text-sm font-medium text-ink-2 hover:bg-surface-2"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="border-t border-line px-5 py-4">
          <p className="text-sm font-medium text-ink">{session.user.name}</p>
          <p className="mb-3 text-xs text-muted">{PAPEIS_USUARIO_LABEL[session.user.papel]}</p>
          <form action={sair}>
            <button type="submit" className="text-xs font-semibold text-accent hover:underline">
              Sair
            </button>
          </form>
        </div>
      </aside>

      <div className="flex-1 bg-paper">
        <main className="mx-auto max-w-5xl px-8 py-10">{children}</main>
      </div>
    </div>
  );
}
