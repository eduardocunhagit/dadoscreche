import Link from "next/link";
import { auth } from "@/core/auth";
import { prisma } from "@/core/db/client";
import { Cartao, CartaoCorpo } from "@/core/ui/Card";
import { PAPEIS_USUARIO_LABEL } from "@/core/domain/constants";
import { listarCriancasDoResponsavel, filaDeRevalidacao } from "@/modules/perfil-contatos";
import { ofertasEmAberto, inconsistenciasDeEstado } from "@/modules/alocacao";
import { widgetsDoSlot } from "@/modules/registry";

function diasDesde(d: Date) {
  return Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
}

function WidgetsDoTopo() {
  const widgets = widgetsDoSlot("dashboard-topo");
  if (widgets.length === 0) return null;
  return (
    <div className="space-y-3">
      {widgets.map((w, i) => (
        <w.component key={i} />
      ))}
    </div>
  );
}

function Estatistica({ numero, rotulo }: { numero: number | string; rotulo: string }) {
  return (
    <Cartao>
      <CartaoCorpo>
        <p className="font-serif text-3xl text-ink">{numero}</p>
        <p className="mt-1 text-sm text-muted">{rotulo}</p>
      </CartaoCorpo>
    </Cartao>
  );
}

export default async function PaginaInicial() {
  const session = await auth();
  const user = session!.user;

  if (user.papel === "RESPONSAVEL" && user.responsavelId) {
    const criancas = await listarCriancasDoResponsavel(user.responsavelId);
    const semAlternativo = criancas.filter(
      (c) => !c.contatos.some((k) => k.papel === "ALTERNATIVO") && !c.semContatoAlternativoDeclarado
    );

    return (
      <div className="space-y-8">
        <div>
          <h1 className="font-serif text-2xl text-ink">Olá, {user.name}</h1>
          <p className="mt-1 text-sm text-muted">
            {criancas.length} {criancas.length === 1 ? "criança vinculada" : "crianças vinculadas"} ao seu cadastro.
          </p>
        </div>

        <WidgetsDoTopo />

        {semAlternativo.length > 0 && (
          <Cartao className="border-warn/40">
            <CartaoCorpo>
              <p className="text-sm font-medium text-ink">
                {semAlternativo.length === 1
                  ? "Uma criança ainda não tem um contato alternativo cadastrado."
                  : `${semAlternativo.length} crianças ainda não têm contato alternativo cadastrado.`}
              </p>
              <p className="mt-1 text-sm text-ink-2">
                Um segundo telefone de alguém próximo (avó, tio, vizinho) ajuda a não perder a vaga se você não
                atender no dia da chamada. Acesse{" "}
                <Link href="/meus-filhos" className="font-medium text-accent hover:underline">
                  Meus filhos
                </Link>{" "}
                para adicionar.
              </p>
            </CartaoCorpo>
          </Cartao>
        )}

        <Link
          href="/meus-filhos"
          className="inline-block rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-white hover:bg-accent-2"
        >
          Ver meus filhos e gerenciar contatos
        </Link>
      </div>
    );
  }

  // SERVIDOR_UNIDADE | SERVIDOR_CRE | GESTOR_SME
  const escopo =
    user.papel === "SERVIDOR_UNIDADE"
      ? { unidadeEscCodigo: user.unidadeEscCodigo ?? undefined }
      : user.papel === "SERVIDOR_CRE"
        ? { poloId: user.poloId ?? undefined }
        : {};

  const [ofertas, revalidar, inconsistentes, totalNaFila] = await Promise.all([
    ofertasEmAberto(escopo),
    filaDeRevalidacao(escopo),
    inconsistenciasDeEstado(),
    prisma.opcao.count({ where: { estado: "NA_FILA" } }),
  ]);

  const ofertaMaisAntiga = ofertas[0] ? diasDesde(ofertas[0].ofertaAbertaEm!) : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-serif text-2xl text-ink">Painel — {PAPEIS_USUARIO_LABEL[user.papel]}</h1>
        <p className="mt-1 text-sm text-muted">{user.name}</p>
      </div>

      <WidgetsDoTopo />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Estatistica numero={ofertas.length} rotulo="Ofertas abertas aguardando confirmação" />
        <Estatistica
          numero={ofertaMaisAntiga !== null ? `${ofertaMaisAntiga}d` : "—"}
          rotulo="Oferta aberta há mais tempo"
        />
        <Estatistica numero={revalidar.length} rotulo="Crianças com contato a revalidar" />
        <Estatistica numero={inconsistentes.length} rotulo="Cadastros com estado inconsistente" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link href="/fila" className="block">
          <Cartao className="transition-colors hover:border-accent">
            <CartaoCorpo>
              <p className="font-medium text-ink">Fila e ofertas</p>
              <p className="mt-1 text-sm text-muted">Acompanhar o relógio de cada oferta aberta.</p>
            </CartaoCorpo>
          </Cartao>
        </Link>
        <Link href="/revalidacao-contatos" className="block">
          <Cartao className="transition-colors hover:border-accent">
            <CartaoCorpo>
              <p className="font-medium text-ink">Revalidar contatos</p>
              <p className="mt-1 text-sm text-muted">Fila de trabalho de contatos vencidos ou nunca verificados.</p>
            </CartaoCorpo>
          </Cartao>
        </Link>
      </div>

      <p className="text-xs text-faint">{totalNaFila} opções na fila em todo o sistema.</p>
    </div>
  );
}
