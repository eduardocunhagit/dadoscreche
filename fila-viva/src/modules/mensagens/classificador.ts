export type ClassificacaoResposta =
  | "CONFIRMOU_CONTATO"
  | "NUMERO_INCORRETO"
  | "DUVIDA"
  | "ATENDIMENTO_HUMANO"
  | "INCERTA";

export interface ResultadoClassificacao {
  classificacao: ClassificacaoResposta;
  sugestaoResposta: string;
}

function normalizar(texto: string) {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function classificarResposta(texto: string): ResultadoClassificacao {
  const resposta = normalizar(texto);

  if (/numero errado|nao e|nao sou|nao conheco|pessoa errada/.test(resposta)) {
    return {
      classificacao: "NUMERO_INCORRETO",
      sugestaoResposta: "Obrigado por avisar. Vamos revisar o cadastro e não enviaremos novas mensagens para este número.",
    };
  }

  if (/atendente|humano|ligar|falar com (uma )?pessoa/.test(resposta)) {
    return {
      classificacao: "ATENDIMENTO_HUMANO",
      sugestaoResposta: "Entendido. Uma pessoa da equipe entrará em contato para ajudar.",
    };
  }

  if (/\?|duvida|como|quando|onde|qual|porque|por que/.test(resposta)) {
    return {
      classificacao: "DUVIDA",
      sugestaoResposta: "Recebemos sua dúvida. Uma pessoa da equipe vai conferir as informações e responder em seguida.",
    };
  }

  if (/^sim\b|correto|confirmo|continua|este numero|esse numero|sou eu/.test(resposta)) {
    return {
      classificacao: "CONFIRMOU_CONTATO",
      sugestaoResposta: "Obrigado pela confirmação. Este WhatsApp continuará registrado como contato da família.",
    };
  }

  return {
    classificacao: "INCERTA",
    sugestaoResposta: "Obrigado pela resposta. Você pode confirmar se este número pertence à família responsável pela criança?",
  };
}
