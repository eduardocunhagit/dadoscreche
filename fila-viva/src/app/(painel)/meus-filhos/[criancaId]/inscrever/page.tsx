import { redirect, notFound } from "next/navigation";
import { auth } from "@/core/auth";
import { obterCriancaComContatos, criancaNoEscopoDoUsuario } from "@/modules/perfil-contatos";
import { listarPolos, processoVigente, listarInscricoesDaCrianca } from "@/modules/alocacao";
import { Cartao, CartaoCorpo, CartaoTitulo } from "@/core/ui/Card";
import { SeletorDeInscricao } from "./SeletorDeInscricao";

function grupamentoSugerido(nascimentoAnoMes: string): string {
  const [ano, mes] = nascimentoAnoMes.split("-").map(Number);
  const agora = new Date();
  const meses = (agora.getFullYear() - ano) * 12 + (agora.getMonth() + 1 - mes);
  if (meses < 24) return "Berçário";
  if (meses < 36) return "Maternal I";
  return "Maternal II";
}

export default async function PaginaNovaInscricao(props: PageProps<"/meus-filhos/[criancaId]/inscrever">) {
  const { criancaId } = await props.params;
  const session = await auth();
  const user = session!.user;

  const crianca = await obterCriancaComContatos(criancaId);
  if (!crianca) notFound();

  const podeAcessar = await criancaNoEscopoDoUsuario(criancaId, user);
  if (!podeAcessar) redirect("/");

  const [polos, processo, inscricoesExistentes] = await Promise.all([
    listarPolos(),
    processoVigente(),
    listarInscricoesDaCrianca(criancaId),
  ]);

  const jaInscritaNoProcesso = inscricoesExistentes.some((i) => i.processoId === processo.id);

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">{crianca.nomeExibicao}</p>
        <h1 className="font-serif text-2xl text-ink">Nova inscrição — processo {processo.ano}</h1>
        <p className="mt-1 text-sm text-muted">
          Escolha até 5 creches, na ordem que a família prefere. A posição importa: é ela que decide qual
          opção é ofertada primeiro quando surge uma vaga.
        </p>
      </div>

      {jaInscritaNoProcesso ? (
        <Cartao className="border-warn/40">
          <CartaoCorpo>
            <p className="text-sm text-ink">
              {crianca.nomeExibicao} já tem uma inscrição no processo {processo.ano}. Veja o andamento no
              perfil da criança.
            </p>
          </CartaoCorpo>
        </Cartao>
      ) : (
        <Cartao>
          <CartaoTitulo>Escolher as creches</CartaoTitulo>
          <CartaoCorpo>
            <SeletorDeInscricao
              criancaId={criancaId}
              processoId={processo.id}
              polos={polos.map((p) => ({ id: p.id, nome: p.nome }))}
              grupamentoSugerido={grupamentoSugerido(crianca.nascimentoAnoMes)}
            />
          </CartaoCorpo>
        </Cartao>
      )}
    </div>
  );
}
