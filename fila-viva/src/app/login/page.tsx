import { autenticar } from "./actions";
import { Botao } from "@/core/ui/Button";
import { Campo, Rotulo } from "@/core/ui/Input";

export default async function PaginaLogin(props: PageProps<"/login">) {
  const searchParams = await props.searchParams;
  const comErro = searchParams.erro === "1";

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-accent">
            Inscrição Creche · SME-Rio
          </p>
          <h1 className="font-serif text-3xl text-ink">Fila Viva</h1>
        </div>

        <form
          action={autenticar}
          className="space-y-4 rounded-lg border border-line bg-surface p-6 shadow-sm"
        >
          {comErro && (
            <p className="rounded-md bg-bad-soft px-3 py-2 text-sm text-bad">
              E-mail ou senha incorretos.
            </p>
          )}
          <div>
            <Rotulo htmlFor="email">E-mail</Rotulo>
            <Campo id="email" name="email" type="email" required autoFocus />
          </div>
          <div>
            <Rotulo htmlFor="senha">Senha</Rotulo>
            <Campo id="senha" name="senha" type="password" required />
          </div>
          <Botao type="submit" className="w-full">
            Entrar
          </Botao>
        </form>

        <p className="mt-6 text-center text-xs text-faint">
          Contas de demonstração no seed — ver README do projeto.
        </p>
      </div>
    </main>
  );
}
