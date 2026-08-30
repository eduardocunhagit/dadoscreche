import { Cartao, CartaoCorpo } from "@/core/ui/Card";

// Módulo de exemplo — prova de que dá pra acrescentar algo visível sem
// tocar em nenhum arquivo do núcleo. Ver EXTENDING.md antes de apagar ou
// copiar isto.
export function AvisoExemplo() {
  return (
    <Cartao className="border-accent/40 bg-accent-soft/40">
      <CartaoCorpo>
        <p className="text-sm text-ink-2">
          <span className="font-semibold text-ink">Este cartão vem de um módulo de exemplo</span>{" "}
          (<code>src/modules/exemplo</code>) — copie a pasta pra começar o seu. Nada em{" "}
          <code>src/core</code> ou nas telas do painel foi editado pra ele aparecer aqui.
        </p>
      </CartaoCorpo>
    </Cartao>
  );
}
