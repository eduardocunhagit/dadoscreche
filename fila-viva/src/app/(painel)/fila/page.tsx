import { redirect } from "next/navigation";
import { auth } from "@/core/auth";
import { prisma } from "@/core/db/client";
import { ofertasEmAberto, inconsistenciasDeEstado } from "@/modules/alocacao";
import { Cartao, CartaoCorpo, CartaoTitulo } from "@/core/ui/Card";
import { Selo } from "@/core/ui/Badge";
import { Botao } from "@/core/ui/Button";
import { actionAplicarEvento, actionAlternarFlag } from "./actions";

function diasDesde(d: Date) {
  return Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
}

export default async function PaginaFila() {
  const session = await auth();
  const user = session!.user;
  if (user.papel === "RESPONSAVEL") redirect("/");

  const processo = await prisma.processo.findUnique({ where: { ano: 2025 } });

  const escopo =
    user.papel === "SERVIDOR_UNIDADE"
      ? { unidadeEscCodigo: user.unidadeEscCodigo ?? undefined }
      : user.papel === "SERVIDOR_CRE"
        ? { poloId: user.poloId ?? undefined }
        : {};

  const [ofertas, inconsistentes] = await Promise.all([ofertasEmAberto(escopo), inconsistenciasDeEstado()]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-serif text-2xl text-ink">Fila e ofertas</h1>
        <p className="mt-1 text-sm text-muted">
          Toda oferta aqui mostra há quanto tempo está aberta — é o registro que a base histórica não tinha.
        </p>
      </div>

      {processo && (
        <Cartao>
          <CartaoTitulo>Regras do motor — processo {processo.ano}</CartaoTitulo>
          <CartaoCorpo className="flex flex-wrap gap-6">
            {(["liberacaoEmCascata", "aceiteCondicional"] as const).map((campo) => (
              <form key={campo} action={actionAlternarFlag} className="flex items-center gap-3">
                <input type="hidden" name="processoId" value={processo.id} />
                <input type="hidden" name="campo" value={campo} />
                <Selo tom={processo[campo] ? "bom" : "neutro"}>
                  {campo === "liberacaoEmCascata" ? "Liberação em cascata" : "Aceite condicional"}:{" "}
                  {processo[campo] ? "ligada" : "desligada"}
                </Selo>
                {user.papel === "GESTOR_SME" && (
                  <Botao type="submit" variante="fantasma">
                    Alternar
                  </Botao>
                )}
              </form>
            ))}
          </CartaoCorpo>
        </Cartao>
      )}

      <Cartao>
        <CartaoTitulo>Ofertas abertas ({ofertas.length})</CartaoTitulo>
        <CartaoCorpo className="space-y-3">
          {ofertas.length === 0 && <p className="text-sm text-muted">Nenhuma oferta aberta no momento.</p>}
          {ofertas.map((o) => (
            <div key={o.id} className="rounded-md border border-line p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-ink">
                    {o.inscricao.crianca.nomeExibicao} · {o.ordem}ª opção
                  </p>
                  <p className="text-xs text-muted">
                    {o.unidade.nome} — {o.grupamento} · {o.turno}
                  </p>
                </div>
                <Selo tom={diasDesde(o.ofertaAbertaEm!) >= 5 ? "ruim" : "atencao"}>
                  {diasDesde(o.ofertaAbertaEm!)} dia(s) em aberto
                </Selo>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <form action={actionAplicarEvento}>
                  <input type="hidden" name="opcaoId" value={o.id} />
                  <input type="hidden" name="evento" value="ACEITAR_DEFINITIVO" />
                  <Botao type="submit" variante="secundaria">
                    Aceitar definitivo
                  </Botao>
                </form>
                {processo?.aceiteCondicional && (
                  <form action={actionAplicarEvento}>
                    <input type="hidden" name="opcaoId" value={o.id} />
                    <input type="hidden" name="evento" value="ACEITAR_CONDICIONAL" />
                    <Botao type="submit" variante="secundaria">
                      Aceitar condicional
                    </Botao>
                  </form>
                )}
                <form action={actionAplicarEvento}>
                  <input type="hidden" name="opcaoId" value={o.id} />
                  <input type="hidden" name="evento" value="RECUSAR" />
                  <Botao type="submit" variante="fantasma">
                    Recusar
                  </Botao>
                </form>
                <form action={actionAplicarEvento}>
                  <input type="hidden" name="opcaoId" value={o.id} />
                  <input type="hidden" name="evento" value="EXPIRAR" />
                  <Botao type="submit" variante="fantasma" className="text-bad hover:bg-bad-soft">
                    Expirar (não localizada)
                  </Botao>
                </form>
              </div>
            </div>
          ))}
        </CartaoCorpo>
      </Cartao>

      {inconsistentes.length > 0 && (
        <Cartao className="border-bad/40">
          <CartaoTitulo>Estados inconsistentes ({inconsistentes.length})</CartaoTitulo>
          <CartaoCorpo className="space-y-2">
            <p className="text-sm text-ink-2">
              Cadastros com uma opção ofertada enquanto outra ainda está na fila — checagem manual, linha a
              linha, hoje. Aqui já sai calculado.
            </p>
            {inconsistentes.map((i) => (
              <p key={i.id} className="text-sm text-ink">
                {i.crianca.nomeExibicao} — inscrição {i.iplId}
              </p>
            ))}
          </CartaoCorpo>
        </Cartao>
      )}
    </div>
  );
}
