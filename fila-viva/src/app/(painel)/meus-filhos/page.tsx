import { redirect } from "next/navigation";
import Link from "next/link";
import { auth } from "@/core/auth";
import { listarCriancasDoResponsavel } from "@/modules/perfil-contatos";
import { Cartao, CartaoCorpo } from "@/core/ui/Card";
import { Selo } from "@/core/ui/Badge";

export default async function PaginaMeusFilhos() {
  const session = await auth();
  const user = session!.user;
  if (user.papel !== "RESPONSAVEL" || !user.responsavelId) redirect("/");

  const criancas = await listarCriancasDoResponsavel(user.responsavelId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-ink">Meus filhos</h1>
        <p className="mt-1 text-sm text-muted">
          Mantenha os contatos em dia — é como a equipe da creche avisa quando surge uma vaga.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {criancas.map((crianca) => {
          const temAlternativo = crianca.contatos.some((c) => c.papel === "ALTERNATIVO");
          return (
            <Link key={crianca.id} href={`/meus-filhos/${crianca.id}`}>
              <Cartao className="h-full transition-colors hover:border-accent">
                <CartaoCorpo>
                  <p className="font-medium text-ink">{crianca.nomeExibicao}</p>
                  <p className="mt-1 text-xs text-muted">Nascimento: {crianca.nascimentoAnoMes}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <Selo tom={crianca.contatos.length > 0 ? "bom" : "atencao"}>
                      {crianca.contatos.length} contato{crianca.contatos.length === 1 ? "" : "s"}
                    </Selo>
                    {!temAlternativo && !crianca.semContatoAlternativoDeclarado && (
                      <Selo tom="atencao">Sem contato alternativo</Selo>
                    )}
                  </div>
                </CartaoCorpo>
              </Cartao>
            </Link>
          );
        })}
      </div>

      {criancas.length === 0 && (
        <p className="text-sm text-muted">Nenhuma criança vinculada a este cadastro ainda.</p>
      )}
    </div>
  );
}
