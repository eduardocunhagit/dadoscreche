import type { UnidadeParaEscolha } from "@/modules/inscricao";

// Tipos compartilhados entre a rota (page.tsx/actions.ts) e os componentes do
// assistente ("./AssistenteInscricao" e afins). Sem "use server" — são só
// tipos, importáveis de ambos os lados.

export interface ContatoResumo {
  id: string;
  canal: string;
  valor: string;
  papel: string;
}

export interface DadosDoAssistente {
  criancas: {
    id: string;
    nomeExibicao: string;
    nascimentoAnoMes: string;
    contatos: ContatoResumo[];
  }[];
  perguntas: { id: string; texto: string; pontuacao: number }[];
  unidades: UnidadeParaEscolha[];
  bairros: { bairro: string; latitude: number; longitude: number }[];
  anoProcesso: number;
}
