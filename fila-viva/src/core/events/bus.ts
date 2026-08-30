// Barramento de eventos — a peça que evita que um módulo precise editar o
// código de outro. Exemplo real: quando o motor de alocação abre uma oferta,
// o módulo de convocação (Eixo 3) precisa disparar a régua de contato. Sem
// isto, ele teria que editar src/core/domain/motor.ts. Com isto, ele só
// assina "oferta.criada" no próprio manifesto — ver EXTENDING.md.
//
// Handlers rodam em sequência e um erro num handler não derruba os outros
// (fica só logado); isso evita que um módulo com bug tire o núcleo do ar.

export interface EventoDoBarramento {
  "oferta.criada": { opcaoId: string; inscricaoId: string; prazo: Date };
  "oferta.aceita_definitiva": { opcaoId: string; inscricaoId: string };
  "oferta.aceita_condicional": { opcaoId: string; inscricaoId: string };
  "oferta.recusada": { opcaoId: string; inscricaoId: string };
  "oferta.expirada": { opcaoId: string; inscricaoId: string };
  "contato.alterado": { contatoId: string; criancaId: string; autorPapel: string };
}

export type NomeEvento = keyof EventoDoBarramento;
type Handler<K extends NomeEvento> = (payload: EventoDoBarramento[K]) => void | Promise<void>;
// O mapa interno guarda handlers de payloads diferentes por evento — não
// dá pra tipar isso sem perder a variância. `any` fica só aqui dentro; a
// API pública (`on`/`emit`) continua totalmente tipada por K.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HandlerArmazenado = Handler<any>;

class BarramentoDeEventos {
  private handlers = new Map<NomeEvento, Set<HandlerArmazenado>>();

  on<K extends NomeEvento>(evento: K, handler: Handler<K>): () => void {
    if (!this.handlers.has(evento)) this.handlers.set(evento, new Set());
    this.handlers.get(evento)!.add(handler as HandlerArmazenado);
    return () => this.handlers.get(evento)?.delete(handler as HandlerArmazenado);
  }

  /**
   * Mesma coisa que `on`, mas para quando o evento vem de uma estrutura
   * dinâmica (o `assina` de um manifesto de módulo, ver registry.ts) e já
   * perdeu a especificidade de K antes de chegar aqui. Só use isto se você
   * não tem como saber K em tempo de compilação — o registry é o único
   * lugar do projeto que se encaixa nesse caso.
   */
  onDynamic(evento: NomeEvento, handler: HandlerArmazenado): void {
    if (!this.handlers.has(evento)) this.handlers.set(evento, new Set());
    this.handlers.get(evento)!.add(handler);
  }

  async emit<K extends NomeEvento>(evento: K, payload: EventoDoBarramento[K]): Promise<void> {
    const ouvintes = this.handlers.get(evento);
    if (!ouvintes) return;
    for (const handler of ouvintes) {
      try {
        await handler(payload);
      } catch (erro) {
        console.error(`[eventos] handler de "${evento}" falhou:`, erro);
      }
    }
  }
}

export const barramento = new BarramentoDeEventos();
