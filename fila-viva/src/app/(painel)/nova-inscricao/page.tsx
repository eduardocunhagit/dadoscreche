import { redirect } from "next/navigation";
import { auth } from "@/core/auth";
import { prisma } from "@/core/db/client";
import { listarCriancasDoResponsavel } from "@/modules/perfil-contatos";
import { listarUnidadesComGeoEDemanda, listarBairrosComCentroide } from "@/modules/inscricao";
import { AssistenteInscricao } from "./AssistenteInscricao";
import type { DadosDoAssistente } from "./tipos";

const ANO_PROCESSO_ATUAL = 2025; // único processo do piloto — ver Briefing

export default async function PaginaNovaInscricao() {
  const session = await auth();
  const user = session!.user;
  if (user.papel !== "RESPONSAVEL" || !user.responsavelId) redirect("/");

  const [criancas, perguntas, unidades, bairros] = await Promise.all([
    listarCriancasDoResponsavel(user.responsavelId),
    prisma.pergunta.findMany({
      where: { processo: { ano: ANO_PROCESSO_ATUAL } },
      orderBy: { ordemVisualizacao: "asc" },
    }),
    listarUnidadesComGeoEDemanda(ANO_PROCESSO_ATUAL),
    listarBairrosComCentroide(),
  ]);

  const dados: DadosDoAssistente = {
    criancas: criancas.map((c) => ({
      id: c.id,
      nomeExibicao: c.nomeExibicao,
      nascimentoAnoMes: c.nascimentoAnoMes,
      contatos: c.contatos.map((k) => ({ id: k.id, canal: k.canal, valor: k.valor, papel: k.papel })),
    })),
    perguntas: perguntas.map((p) => ({ id: p.id, texto: p.texto, pontuacao: p.pontuacao })),
    unidades,
    bairros,
    anoProcesso: ANO_PROCESSO_ATUAL,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-ink">Nova inscrição</h1>
        <p className="mt-1 text-sm text-muted">
          Preencha os dados da criança e escolha até 5 unidades para concorrer a uma vaga.
        </p>
      </div>

      <AssistenteInscricao dados={dados} />
    </div>
  );
}
