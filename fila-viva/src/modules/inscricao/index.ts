import type { Modulo } from "../tipos";

export const moduloInscricao: Modulo = {
  id: "inscricao",
  nome: "Nova inscrição",
  menu: [{ href: "/nova-inscricao", label: "Nova inscrição", papeis: ["RESPONSAVEL"] }],
};

export * from "./servico";
