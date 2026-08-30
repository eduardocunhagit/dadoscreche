import Link from "next/link";
import { redirect, notFound } from "next/navigation";
import { auth } from "@/core/auth";
import { obterCriancaComContatos, criancaNoEscopoDoUsuario } from "@/modules/perfil-contatos";
import { listarInscricoesDaCrianca } from "@/modules/alocacao";
import { CANAIS_CONTATO_LABEL, type EstadoOpcao } from "@/core/domain/constants";
import { Cartao, CartaoCorpo, CartaoTitulo } from "@/core/ui/Card";
import { Selo, SeloEstadoOpcao } from "@/core/ui/Badge";
import { Botao } from "@/core/ui/Button";
import { Campo } from "@/core/ui/Input";
import { FormularioContato } from "./FormularioContato";
import { SecaoMensagens } from "@/modules/mensagens/SecaoMensagens";
import { actionDeclararSemAlternativo, actionDesativar, actionEditarValor, actionVerificar } from "./actions";

function formatarData(d: Date | null) {
  if (!d) return null;
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

export default async function PaginaCrianca(props: PageProps<"/meus-filhos/[criancaId]">) {
  const { criancaId } = await props.params;
  const session = await auth();
  const user = session!.user;

  const crianca = await obterCriancaComContatos(criancaId);
  if (!crianca) notFound();

  const podeAcessar = await criancaNoEscopoDoUsuario(criancaId, user);
  if (!podeAcessar) redirect("/");

  const inscricoes = await listarInscricoesDaCrianca(criancaId);
  const podeEditar = user.papel === "RESPONSAVEL" || user.papel.startsWith("SERVIDOR");
  const contatosAtivos = crianca.contatos.filter((c) => c.ativo);
  const temAlternativo = contatosAtivos.some((c) => c.papel === "ALTERNATIVO");
  const proximaOrdem = contatosAtivos.length + 1;

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">
          {crianca.responsavelPrincipal.nomeExibicao}
        </p>
        <h1 className="font-serif text-2xl text-ink">{crianca.nomeExibicao}</h1>
        <p className="mt-1 text-sm text-muted">Nascimento: {crianca.nascimentoAnoMes}</p>
      </div>

      <Cartao>
        <CartaoTitulo className="flex items-center justify-between">
          <span>Inscrições</span>
          {podeEditar && (
            <Link href={`/meus-filhos/${criancaId}/inscrever`} className="text-sm font-medium text-accent hover:underline">
              + Nova inscrição
            </Link>
          )}
        </CartaoTitulo>
        <CartaoCorpo className="space-y-4">
          {inscricoes.length === 0 && (
            <p className="text-sm text-muted">
              Nenhuma inscrição ainda.{" "}
              {podeEditar && (
                <Link href={`/meus-filhos/${criancaId}/inscrever`} className="font-medium text-accent hover:underline">
                  Escolher creches
                </Link>
              )}
            </p>
          )}
          {inscricoes.map((inscricao) => (
            <div key={inscricao.id} className="rounded-md border border-line p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                Processo {inscricao.processo.ano} — inscrita em {formatarData(inscricao.dataCriacao)}
              </p>
              <ul className="space-y-1.5">
                {inscricao.opcoes.map((o) => (
                  <li key={o.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-mono text-xs text-faint">{o.ordem}ª</span>
                    <span className="text-ink">{o.unidade.nome}</span>
                    <span className="text-muted">— {o.grupamento} · {o.turno}</span>
                    <SeloEstadoOpcao estado={o.estado as EstadoOpcao} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </CartaoCorpo>
      </Cartao>

      <Cartao>
        <CartaoTitulo>Contatos cadastrados</CartaoTitulo>
        <CartaoCorpo className="space-y-4">
          {contatosAtivos.length === 0 && (
            <p className="text-sm text-muted">Nenhum contato ativo ainda.</p>
          )}

          {contatosAtivos.map((c) => (
            <div key={c.id} className="rounded-md border border-line p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Selo tom={c.papel === "ALTERNATIVO" ? "acento" : "neutro"}>
                  {c.papel === "ALTERNATIVO" ? `${c.parentesco} — ${c.nomeContato}` : "Responsável"}
                </Selo>
                <Selo tom="neutro">{CANAIS_CONTATO_LABEL[c.canal as keyof typeof CANAIS_CONTATO_LABEL]}</Selo>
                <Selo tom="neutro">tentativa {c.ordemTentativa}</Selo>
                {c.verificadoEm ? (
                  <Selo tom="bom">Verificado em {formatarData(c.verificadoEm)}</Selo>
                ) : (
                  <Selo tom="atencao">Nunca verificado</Selo>
                )}
              </div>

              <div className="mt-3 flex flex-wrap items-end gap-2">
                <form action={actionEditarValor} className="flex items-end gap-2">
                  <input type="hidden" name="criancaId" value={criancaId} />
                  <input type="hidden" name="contatoId" value={c.id} />
                  <div>
                    <Campo name="valor" defaultValue={c.valor} disabled={!podeEditar} className="w-56" />
                  </div>
                  {podeEditar && (
                    <Botao type="submit" variante="secundaria">
                      Salvar
                    </Botao>
                  )}
                </form>

                {podeEditar && (
                  <>
                    <form action={actionVerificar}>
                      <input type="hidden" name="criancaId" value={criancaId} />
                      <input type="hidden" name="contatoId" value={c.id} />
                      <Botao type="submit" variante="fantasma">
                        Marcar como verificado
                      </Botao>
                    </form>
                    <form action={actionDesativar}>
                      <input type="hidden" name="criancaId" value={criancaId} />
                      <input type="hidden" name="contatoId" value={c.id} />
                      <Botao type="submit" variante="fantasma" className="text-bad hover:bg-bad-soft">
                        Remover
                      </Botao>
                    </form>
                  </>
                )}
              </div>

              {c.historico.length > 0 && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-medium text-muted">
                    Histórico ({c.historico.length})
                  </summary>
                  <ul className="mt-2 space-y-1 text-xs text-faint">
                    {c.historico.map((h) => (
                      <li key={h.id}>
                        {formatarData(h.quando)} · {h.autorPapel} alterou {h.campo}
                        {h.valorAntes || h.valorDepois ? `: "${h.valorAntes ?? "—"}" → "${h.valorDepois ?? "—"}"` : ""}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))}
        </CartaoCorpo>
      </Cartao>

      {user.papel !== "RESPONSAVEL" && <SecaoMensagens criancaId={criancaId} />}

      {podeEditar && (
        <Cartao>
          <CartaoTitulo>Adicionar contato</CartaoTitulo>
          <CartaoCorpo>
            <FormularioContato criancaId={criancaId} proximaOrdem={proximaOrdem} />
          </CartaoCorpo>
        </Cartao>
      )}

      {!temAlternativo && podeEditar && (
        <Cartao className="border-warn/40">
          <CartaoCorpo className="space-y-2">
            <p className="text-sm font-medium text-ink">Não tem um segundo contato para informar?</p>
            <p className="text-sm text-ink-2">
              Tudo bem — mas isso ajuda a equipe a saber que, se o telefone do responsável não atender,
              não existe um caminho alternativo para localizar a família.
            </p>
            <form action={actionDeclararSemAlternativo}>
              <input type="hidden" name="criancaId" value={criancaId} />
              <input type="hidden" name="declarado" value={crianca.semContatoAlternativoDeclarado ? "false" : "true"} />
              <Botao type="submit" variante="secundaria">
                {crianca.semContatoAlternativoDeclarado
                  ? "Desfazer — na verdade eu tenho um contato"
                  : "Declarar que não tenho outro contato"}
              </Botao>
            </form>
            {crianca.semContatoAlternativoDeclarado && (
              <p className="text-xs text-faint">
                Declarado em {formatarData(crianca.semContatoAlternativoDeclaradoEm)}.
              </p>
            )}
          </CartaoCorpo>
        </Cartao>
      )}
    </div>
  );
}
