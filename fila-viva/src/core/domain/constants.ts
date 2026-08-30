// Valores válidos para colunas String que fazem papel de enum (SQLite não
// tem enum nativo — ver o comentário no topo de prisma/schema.prisma).
// Mudar um valor aqui é uma migração de dados, não só de código.

export const PAPEIS_USUARIO = [
  "RESPONSAVEL",
  "SERVIDOR_UNIDADE",
  "SERVIDOR_CRE",
  "GESTOR_SME",
] as const;
export type PapelUsuario = (typeof PAPEIS_USUARIO)[number];

export const PAPEIS_USUARIO_LABEL: Record<PapelUsuario, string> = {
  RESPONSAVEL: "Responsável",
  SERVIDOR_UNIDADE: "Servidor da unidade",
  SERVIDOR_CRE: "Servidor da CRE",
  GESTOR_SME: "Gestor SME",
};

export const PAPEIS_CONTATO = ["RESPONSAVEL", "ALTERNATIVO"] as const;
export type PapelContato = (typeof PAPEIS_CONTATO)[number];

export const CANAIS_CONTATO = ["TELEFONE", "WHATSAPP", "EMAIL", "SMS"] as const;
export type CanalContato = (typeof CANAIS_CONTATO)[number];

export const CANAIS_CONTATO_LABEL: Record<CanalContato, string> = {
  TELEFONE: "Telefone",
  WHATSAPP: "WhatsApp",
  EMAIL: "E-mail",
  SMS: "SMS",
};

// Estados de Opcao — máquina de estados do motor de alocação (Eixo 2).
// Ver src/core/domain/motor.ts para as transições permitidas.
export const ESTADOS_OPCAO = [
  "NA_FILA",
  "OFERTADA",
  "ACEITA_CONDICIONAL",
  "ACEITA_DEFINITIVA",
  "POSICAO_SUSPENSA",
  "RECUSADA",
  "EXPIRADA",
  "ENCERRADA",
] as const;
export type EstadoOpcao = (typeof ESTADOS_OPCAO)[number];

export const ESTADOS_OPCAO_LABEL: Record<EstadoOpcao, string> = {
  NA_FILA: "Na fila",
  OFERTADA: "Ofertada",
  ACEITA_CONDICIONAL: "Aceita (condicional)",
  ACEITA_DEFINITIVA: "Aceita (definitiva)",
  POSICAO_SUSPENSA: "Posição suspensa",
  RECUSADA: "Recusada",
  EXPIRADA: "Expirada",
  ENCERRADA: "Encerrada",
};

// Equivalência com a coluna `situacao` da extração original (Query A), usada
// pelo importador do seed. Mantida separada da máquina de estados nova para
// não confundir "o que a SME chamava isso" com "o que o motor faz com isso".
export const SITUACAO_ORIGINAL_PARA_ESTADO: Record<string, EstadoOpcao> = {
  "Ativo": "NA_FILA",
  "Lista de espera": "NA_FILA",
  "Selecionado": "OFERTADA",
  "Selecionado da lista": "OFERTADA",
  "Confirmado": "ACEITA_DEFINITIVA",
  "Cancelado": "RECUSADA",
  "Cancelado na confirmacao": "EXPIRADA",
  "Cancelado pelo sistema": "ENCERRADA",
};

export const GRUPAMENTOS = ["Berçário", "Maternal I", "Maternal II"] as const;
export const TURNOS = ["Integral", "Parcial"] as const;

export const TIPOS_GESTAO_UNIDADE = ["DIRETA", "CONVENIADA", "PARCERIA"] as const;
export type TipoGestaoUnidade = (typeof TIPOS_GESTAO_UNIDADE)[number];
