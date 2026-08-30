import { redirect } from "next/navigation";
import Link from "next/link";
import { auth } from "@/core/auth";
import { filaDeRevalidacao } from "@/modules/perfil-contatos";
import { Cartao, CartaoCorpo } from "@/core/ui/Card";
import { Selo } from "@/core/ui/Badge";

function formatarData(d: Date | null) {
  if (!d) return "nunca";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

export default async function PaginaRevalidacaoContatos() {
  const session = await auth();
  const user = session!.user;
  if (user.papel === "RESPONSAVEL") redirect("/");

  const escopo =
    user.papel === "SERVIDOR_UNIDADE"
      ? { unidadeEscCodigo: user.unidadeEscCodigo ?? undefined }
      : user.papel === "SERVIDOR_CRE"
        ? { poloId: user.poloId ?? undefined }
        : {};

  const criancas = await filaDeRevalidacao(escopo);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-ink">Revalidar contatos</h1>
        <p className="mt-1 text-sm text-muted">
          Contatos nunca verificados ou vencidos há mais de 6 meses, ordenados aqui como fila de
          trabalho — priorize quem está mais perto de ser chamado.
        </p>
      </div>

      {criancas.length === 0 && (
        <Cartao>
          <CartaoCorpo>
            <p className="text-sm text-muted">Nenhum contato pendente de revalidação no seu escopo.</p>
          </CartaoCorpo>
        </Cartao>
      )}

      <div className="space-y-3">
        {criancas.map((crianca) => (
          <Link key={crianca.id} href={`/meus-filhos/${crianca.id}`}>
            <Cartao className="transition-colors hover:border-accent">
              <CartaoCorpo className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-ink">{crianca.nomeExibicao}</p>
                  <p className="text-xs text-muted">Responsável: {crianca.responsavelPrincipal.nomeExibicao}</p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {crianca.contatos.map((c) => (
                    <Selo key={c.id} tom={c.verificadoEm ? "neutro" : "atencao"}>
                      {c.canal} · {formatarData(c.verificadoEm)}
                    </Selo>
                  ))}
                </div>
              </CartaoCorpo>
            </Cartao>
          </Link>
        ))}
      </div>
    </div>
  );
}
