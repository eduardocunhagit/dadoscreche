import { Selo } from "@/core/ui/Badge";

/**
 * Selo de demanda prevista de uma unidade na etapa de escolha de creches.
 * `classe` vem de UnidadeParaEscolha.demanda (src/modules/inscricao/servico.ts).
 */
export function SeloDemanda({ classe }: { classe: "ALTA" | "MEDIA" | "BAIXA" | null }) {
  if (classe === "ALTA") return <Selo tom="ruim">Alta demanda</Selo>;
  if (classe === "MEDIA") return <Selo tom="atencao">Média demanda</Selo>;
  if (classe === "BAIXA") return <Selo tom="bom">Baixa demanda</Selo>;
  return <Selo tom="neutro">Sem dado</Selo>;
}
