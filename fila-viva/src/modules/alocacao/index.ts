import type { Modulo } from "../tipos";

export const moduloAlocacao: Modulo = {
  id: "alocacao",
  nome: "Motor de alocação",
  menu: [
    { href: "/fila", label: "Fila e ofertas", papeis: ["SERVIDOR_UNIDADE", "SERVIDOR_CRE", "GESTOR_SME"] },
  ],
};

export * from "./servico";
