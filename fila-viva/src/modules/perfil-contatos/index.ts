import type { Modulo } from "../tipos";

export const moduloPerfilContatos: Modulo = {
  id: "perfil-contatos",
  nome: "Perfil e contatos",
  menu: [
    { href: "/meus-filhos", label: "Meus filhos", papeis: ["RESPONSAVEL"] },
    {
      href: "/revalidacao-contatos",
      label: "Revalidar contatos",
      papeis: ["SERVIDOR_UNIDADE", "SERVIDOR_CRE", "GESTOR_SME"],
    },
  ],
};

export * from "./servico";
