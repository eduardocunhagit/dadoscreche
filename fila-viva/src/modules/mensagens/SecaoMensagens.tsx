import { Cartao, CartaoCorpo, CartaoTitulo } from "@/core/ui/Card";
import { Botao } from "@/core/ui/Button";
import { Selo } from "@/core/ui/Badge";
import { actionReceberRespostaDemo, actionResponderMensagem } from "./actions";
import { listarConversasDaCrianca } from "./servico";

const CLASSIFICACOES: Record<string, string> = {
  CONFIRMOU_CONTATO: "Confirmou o contato",
  NUMERO_INCORRETO: "Número incorreto",
  DUVIDA: "Tem dúvida",
  ATENDIMENTO_HUMANO: "Pediu atendimento humano",
  INCERTA: "Resposta incerta",
};

function formatarDataHora(data: Date) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(data);
}

export async function SecaoMensagens({ criancaId }: { criancaId: string }) {
  const conversas = await listarConversasDaCrianca(criancaId);

  return (
    <Cartao>
      <CartaoTitulo className="flex items-center justify-between">
        <span>Mensagens pelo WhatsApp</span>
        <Selo tom="acento">Demonstração</Selo>
      </CartaoTitulo>
      <CartaoCorpo className="space-y-5">
        {conversas.length === 0 && (
          <p className="text-sm text-muted">
            Nenhuma mensagem enviada. Selecione esta criança em “Revalidar contatos” para iniciar.
          </p>
        )}

        {conversas.map((conversa) => (
          <div key={conversa.id} className="rounded-md border border-line p-4">
            <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line pb-3">
              <div>
                <p className="text-sm font-medium text-ink">{conversa.nomeContato}</p>
                <p className="text-xs text-muted">{conversa.telefone}</p>
              </div>
              <Selo tom={conversa.status === "RESPONDIDA" ? "bom" : conversa.status === "ERRO" ? "ruim" : "atencao"}>
                {conversa.status === "RESPONDIDA" ? "Respondida" : conversa.status === "ERRO" ? "Erro" : "Enviada"}
              </Selo>
            </div>

            <div className="mt-4 space-y-3">
              {conversa.mensagens.map((mensagem) => (
                <div
                  key={mensagem.id}
                  className={`max-w-3xl rounded-md p-3 text-sm ${
                    mensagem.direcao === "SAIDA"
                      ? "ml-auto bg-accent-soft text-ink-2"
                      : "mr-auto bg-surface-2 text-ink"
                  }`}
                >
                  <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                    <span>{mensagem.direcao === "SAIDA" ? "Equipe" : conversa.nomeContato}</span>
                    <span>{formatarDataHora(mensagem.criadaEm)}</span>
                  </div>
                  <p className="whitespace-pre-wrap">{mensagem.conteudo}</p>

                  {mensagem.classificacao && (
                    <div className="mt-3 border-t border-line pt-3">
                      <Selo tom={mensagem.classificacao === "INCERTA" ? "atencao" : "acento"}>
                        {CLASSIFICACOES[mensagem.classificacao] ?? mensagem.classificacao}
                      </Selo>

                      {mensagem.sugestaoResposta && (
                        <form action={actionResponderMensagem} className="mt-3 space-y-2">
                          <input type="hidden" name="conversaId" value={conversa.id} />
                          <input type="hidden" name="criancaId" value={criancaId} />
                          <label
                            htmlFor={`sugestao-${mensagem.id}`}
                            className="block text-xs font-semibold uppercase tracking-wide text-muted"
                          >
                            Resposta sugerida pela IA
                          </label>
                          <textarea
                            id={`sugestao-${mensagem.id}`}
                            name="resposta"
                            defaultValue={mensagem.sugestaoResposta}
                            rows={3}
                            required
                            className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
                          />
                          <Botao type="submit" variante="secundaria">
                            Revisar e enviar resposta
                          </Botao>
                        </form>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <details className="mt-4 rounded-md border border-dashed border-line p-3">
              <summary className="cursor-pointer text-sm font-medium text-accent">
                Simular resposta da família
              </summary>
              <form action={actionReceberRespostaDemo} className="mt-3 space-y-2">
                <input type="hidden" name="conversaId" value={conversa.id} />
                <input type="hidden" name="criancaId" value={criancaId} />
                <textarea
                  name="resposta"
                  rows={3}
                  required
                  placeholder="Ex.: Sim, este número continua correto."
                  className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
                />
                <Botao type="submit" variante="fantasma">
                  Receber resposta no modo demo
                </Botao>
              </form>
            </details>
          </div>
        ))}
      </CartaoCorpo>
    </Cartao>
  );
}
