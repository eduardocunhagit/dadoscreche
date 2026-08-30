import { redirect } from "next/navigation";
import { auth } from "@/core/auth";
import { filaDeRevalidacao } from "@/modules/perfil-contatos";
import { Cartao, CartaoCorpo } from "@/core/ui/Card";
import { PainelRevalidacao } from "@/modules/mensagens/PainelRevalidacao";
import { statusPorCrianca } from "@/modules/mensagens";

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
  const statusComunicacao = await statusPorCrianca(criancas.map((crianca) => crianca.id));

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

      {criancas.length > 0 && (
        <PainelRevalidacao
          criancas={criancas.map((crianca) => ({
            id: crianca.id,
            nomeExibicao: crianca.nomeExibicao,
            responsavelNome: crianca.responsavelPrincipal.nomeExibicao,
            statusComunicacao: statusComunicacao[crianca.id] ?? "NAO_ENVIADA",
            contatos: crianca.contatos.map((contato) => ({
              id: contato.id,
              papel: contato.papel,
              nomeContato: contato.nomeContato,
              parentesco: contato.parentesco,
              canal: contato.canal,
              valor: contato.valor,
              ordemTentativa: contato.ordemTentativa,
              verificadoEm: contato.verificadoEm?.toISOString() ?? null,
              consentimentoEm: contato.consentimentoEm?.toISOString() ?? null,
            })),
          }))}
        />
      )}
    </div>
  );
}
