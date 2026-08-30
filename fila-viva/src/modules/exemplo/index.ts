import type { Modulo } from "../tipos";
import { AvisoExemplo } from "./AvisoExemplo";

// Módulo mínimo de exemplo — copie esta pasta como ponto de partida.
// Passo a passo completo em EXTENDING.md.
export const moduloExemplo: Modulo = {
  id: "exemplo",
  nome: "Exemplo",
  widgets: [{ slot: "dashboard-topo", component: AvisoExemplo }],
};
