import { randomUUID } from "node:crypto";
import { prisma } from "@/core/db/client";
import { cpfValido, normalizarCpf } from "./dominio/cpf";
import { centroide, normalizarBairro, type Ponto } from "./dominio/geo";
import { grupamentoPorNascimento } from "./dominio/grupamento";

// Fronteira do módulo: todo o fluxo "Nova inscrição" do responsável (busca de
// CEP, escolha de unidade, criação de criança e da inscrição em si) passa por
// aqui — nunca prisma.inscricao.create/prisma.crianca.create direto numa
// Server Action. É isso que garante que uma inscrição nova sempre nasce com
// as validações server-side abaixo e com as linhas satélite (perfil +
// contexto de segurança) coerentes com o núcleo.
//
// Dado sensível: InscContextoSeguranca (área sob influência / facção
// relatada) e o CPF em InscPerfilInscricao só podem ser lidos por escrita
// (criarInscricaoCompleta) ou por agregação com piso de k-anonimato
// (contarContextoSegurancaAgregado). Nenhuma outra função deste módulo pode
// devolver uma linha individual dessas duas tabelas — se precisar de mais um
// consumidor desse dado, adicione uma função nova aqui com a mesma regra, não
// leia a tabela direto de uma rota.

const ANO_PROCESSO_ATUAL = 2025; // único processo do piloto — ver Briefing
const PLM_ID_FALLBACK = 1; // usado quando a unidade da 1ª opção não tem InscUnidadeGeo/plmId
const IPL_ID_INICIAL_SINTETICO = 900001; // faixa que não colide com o histórico importado (Query C)
const LIMITE_MINIMO_K_ANONIMATO = 5;

export interface EnderecoGeocodificado {
  cep: string;
  logradouro?: string;
  bairro?: string;
  latitude?: number;
  longitude?: number;
  origem: "VIACEP_CENTROIDE" | "CENTROIDE_BAIRRO" | "INDISPONIVEL";
}

interface RespostaViaCep {
  erro?: boolean;
  logradouro?: string;
  bairro?: string;
}

/**
 * Agrupa InscUnidadeGeo por bairro normalizado da Unidade e calcula o
 * centroide de cada grupo. Base de listarBairrosComCentroide e do fallback
 * de geocodificarCep quando o ViaCEP devolve um bairro sem lat/lon próprio.
 */
async function centroidesPorBairro(): Promise<Map<string, Ponto>> {
  const geos = await prisma.inscUnidadeGeo.findMany({ include: { unidade: true } });

  const pontosPorBairro = new Map<string, Ponto[]>();
  for (const geo of geos) {
    const bairroBruto = geo.unidade.bairro;
    if (!bairroBruto) continue;
    const chave = normalizarBairro(bairroBruto);
    const lista = pontosPorBairro.get(chave) ?? [];
    lista.push({ latitude: geo.latitude, longitude: geo.longitude });
    pontosPorBairro.set(chave, lista);
  }

  const mapa = new Map<string, Ponto>();
  for (const [chave, pontos] of pontosPorBairro) {
    const c = centroide(pontos);
    if (c) mapa.set(chave, c);
  }
  return mapa;
}

/**
 * Geocodifica um CEP via ViaCEP e resolve lat/lon pelo centroide do bairro
 * devolvido (não existe geocodificação de endereço fino nesta base — só de
 * unidade). CEP malformado, timeout (3s) ou erro do ViaCEP -> INDISPONIVEL.
 * Bairro reconhecido mas sem centroide calculável -> devolve logradouro/
 * bairro sem lat/lon; a UI cai para o select de bairro nesse caso.
 */
export async function geocodificarCep(cep: string): Promise<EnderecoGeocodificado> {
  const cepNormalizado = cep.replace(/\D/g, "");
  if (cepNormalizado.length !== 8) {
    return { cep: cepNormalizado, origem: "INDISPONIVEL" };
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 3000);

  let dados: RespostaViaCep;
  try {
    const resposta = await fetch(`https://viacep.com.br/ws/${cepNormalizado}/json/`, {
      signal: controller.signal,
    });
    if (!resposta.ok) {
      return { cep: cepNormalizado, origem: "INDISPONIVEL" };
    }
    dados = (await resposta.json()) as RespostaViaCep;
  } catch {
    return { cep: cepNormalizado, origem: "INDISPONIVEL" };
  } finally {
    clearTimeout(timeoutId);
  }

  if (dados.erro) {
    return { cep: cepNormalizado, origem: "INDISPONIVEL" };
  }

  const logradouro = dados.logradouro || undefined;
  const bairro = dados.bairro || undefined;

  if (bairro) {
    const mapa = await centroidesPorBairro();
    const centro = mapa.get(normalizarBairro(bairro));
    if (centro) {
      return {
        cep: cepNormalizado,
        logradouro,
        bairro,
        latitude: centro.latitude,
        longitude: centro.longitude,
        origem: "VIACEP_CENTROIDE",
      };
    }
  }

  return { cep: cepNormalizado, logradouro, bairro, origem: "VIACEP_CENTROIDE" };
}

/** Centroide por bairro, ordenado alfabeticamente — alimenta o select de bairro da UI. */
export async function listarBairrosComCentroide(): Promise<
  { bairro: string; latitude: number; longitude: number }[]
> {
  const mapa = await centroidesPorBairro();
  return Array.from(mapa.entries())
    .map(([bairro, c]) => ({ bairro, latitude: c.latitude, longitude: c.longitude }))
    .sort((a, b) => a.bairro.localeCompare(b.bairro, "pt-BR"));
}

export interface UnidadeParaEscolha {
  escCodigo: string;
  nome: string;
  bairro: string | null;
  tipoGestao: string;
  latitude: number | null;
  longitude: number | null;
  demanda: "ALTA" | "MEDIA" | "BAIXA" | null;
  /**
   * Demanda excedente prevista = planning_gap / oferta do ano anterior
   * (ex.: 0.43 = demanda 43% acima da oferta). null quando a fonte é o
   * placeholder de pressão de fila ou quando a oferta-proxy era zero.
   */
  demandaExcedente: number | null;
}

/**
 * Unidades para a etapa de escolha da inscrição: só as que têm geo (aparecem
 * no mapa) ou já têm alguma inscrição histórica (aparecem na lista mesmo sem
 * ponto no mapa). Demanda: a previsão do modelo da frente 2 ("modelo_f2") é
 * para o ANO LETIVO SEGUINTE ao processo (inscrição de `ano` disputa vaga em
 * `ano + 1`), então buscamos [ano, ano + 1] e priorizamos modelo_f2 do ano
 * seguinte > modelo_f2 do ano > placeholder "classe_pressao_2025". Só o
 * modelo_f2 carrega o valor numérico do excedente (gap / oferta anterior).
 */
export async function listarUnidadesComGeoEDemanda(ano: number): Promise<UnidadeParaEscolha[]> {
  const unidades = await prisma.unidade.findMany({
    where: { OR: [{ geo: { isNot: null } }, { opcoes: { some: {} } }] },
    include: {
      geo: true,
      demandas: { where: { ano: { in: [ano, ano + 1] } } },
    },
    orderBy: { nome: "asc" },
  });

  return unidades.map((u) => {
    const demanda =
      u.demandas.find((d) => d.fonte === "modelo_f2" && d.ano === ano + 1) ??
      u.demandas.find((d) => d.fonte === "modelo_f2" && d.ano === ano) ??
      u.demandas.find((d) => d.fonte === "classe_pressao_2025");

    return {
      escCodigo: u.escCodigo,
      nome: u.nome,
      bairro: u.bairro,
      tipoGestao: u.tipoGestao,
      latitude: u.geo?.latitude ?? null,
      longitude: u.geo?.longitude ?? null,
      demanda: (demanda?.classe as "ALTA" | "MEDIA" | "BAIXA" | undefined) ?? null,
      demandaExcedente: demanda?.fonte === "modelo_f2" ? (demanda.valor ?? null) : null,
    };
  });
}

/**
 * Cria a Crianca para um responsável autenticado. Esta escrita não existia no
 * núcleo (só o seed populava a tabela) — é a primeira vez que o app cria uma
 * criança fora da carga inicial. alunoAnon sintético ("aluno_local_XXXXXXXX")
 * evita colidir com a numeração da extração real ("aluno_NNNNNNN").
 */
export async function criarCriancaDoResponsavel(
  responsavelId: string,
  dados: { nomeExibicao: string; sexo: "M" | "F"; nascimentoAnoMes: string }
): Promise<{ criancaId: string }> {
  const sufixo = randomUUID().slice(0, 8);
  const crianca = await prisma.crianca.create({
    data: {
      alunoAnon: `aluno_local_${sufixo}`,
      nomeExibicao: dados.nomeExibicao,
      sexo: dados.sexo,
      nascimentoAnoMes: dados.nascimentoAnoMes,
      responsavelPrincipalId: responsavelId,
    },
  });
  return { criancaId: crianca.id };
}

export interface DadosNovaInscricao {
  criancaId: string;
  cpfCrianca: string;
  cpfResponsavel: string;
  enderecoResidencia: EnderecoGeocodificado;
  enderecoTrabalho: EnderecoGeocodificado | null;
  contextoSeguranca: { areaSobInfluencia: boolean; faccaoRelatada?: string };
  respostas: { perguntaId: string; resposta: "Sim" | "Nao" }[];
  opcoes: { unidadeEscCodigo: string; turno: "Integral" | "Parcial" }[]; // ordem = índice+1
}

/**
 * Cria a inscrição completa (Inscricao + Opcao[] + Resposta[] +
 * InscPerfilInscricao + InscContextoSeguranca) numa única transação. Revalida
 * tudo server-side — nada do payload do cliente é confiado sem checagem.
 */
export async function criarInscricaoCompleta(
  dados: DadosNovaInscricao,
  autor: { usuarioId: string; papel: string; responsavelId?: string | null }
): Promise<{ inscricaoId: string }> {
  if (!cpfValido(dados.cpfCrianca) || !cpfValido(dados.cpfResponsavel)) {
    throw new Error("CPF da criança ou do responsável inválido.");
  }

  const crianca = await prisma.crianca.findUniqueOrThrow({ where: { id: dados.criancaId } });
  if (crianca.responsavelPrincipalId !== autor.responsavelId) {
    throw new Error("Esta criança não pertence ao responsável autenticado.");
  }

  if (dados.opcoes.length < 1 || dados.opcoes.length > 5) {
    throw new Error("Escolha de 1 a 5 unidades.");
  }
  const unidadesEscolhidas = new Set(dados.opcoes.map((o) => o.unidadeEscCodigo));
  if (unidadesEscolhidas.size !== dados.opcoes.length) {
    throw new Error("Não é possível escolher a mesma unidade mais de uma vez.");
  }

  const processo = await prisma.processo.findUniqueOrThrow({ where: { ano: ANO_PROCESSO_ATUAL } });

  const grupamento = grupamentoPorNascimento(crianca.nascimentoAnoMes, ANO_PROCESSO_ATUAL);
  if (!grupamento) {
    throw new Error(
      `Esta criança está fora da faixa etária elegível (Berçário a Maternal II) para o processo ${ANO_PROCESSO_ATUAL}.`
    );
  }

  const perguntas = await prisma.pergunta.findMany({ where: { processoId: processo.id } });
  const idsPerguntas = new Set(perguntas.map((p) => p.id));
  const idsRespondidos = new Set(dados.respostas.map((r) => r.perguntaId));
  const todasRespondidas =
    idsPerguntas.size === idsRespondidos.size && [...idsPerguntas].every((id) => idsRespondidos.has(id));
  if (!todasRespondidas) {
    throw new Error("Todas as perguntas do processo precisam ser respondidas.");
  }

  const inscricaoExistente = await prisma.inscricao.findFirst({
    where: { criancaId: dados.criancaId, processoId: processo.id },
  });
  if (inscricaoExistente) {
    throw new Error("Esta criança já tem inscrição neste processo.");
  }

  // plmId da unidade da 1ª opção decide o polo (CRE) da inscrição; unidade
  // sem InscUnidadeGeo/plmId cai no polo 1 como fallback.
  const geoPrimeiraOpcao = await prisma.inscUnidadeGeo.findUnique({
    where: { unidadeEscCodigo: dados.opcoes[0].unidadeEscCodigo },
  });
  const plmId = geoPrimeiraOpcao?.plmId ?? PLM_ID_FALLBACK;
  const polo = await prisma.polo.findUniqueOrThrow({ where: { plmId } });

  const ultimaInscricaoDoPolo = await prisma.inscricao.findFirst({
    where: { processoId: processo.id, poloId: polo.id },
    orderBy: { iplId: "desc" },
  });
  const iplId = ultimaInscricaoDoPolo ? ultimaInscricaoDoPolo.iplId + 1 : IPL_ID_INICIAL_SINTETICO;

  const cpfCriancaNormalizado = normalizarCpf(dados.cpfCrianca);
  const cpfResponsavelNormalizado = normalizarCpf(dados.cpfResponsavel);

  const inscricaoId = await prisma.$transaction(async (tx) => {
    const inscricao = await tx.inscricao.create({
      data: {
        processoId: processo.id,
        poloId: polo.id,
        iplId,
        criancaId: dados.criancaId,
        responsavelId: autor.responsavelId!,
        dataCriacao: new Date(),
        cepResponsavel: dados.enderecoResidencia.cep,
        bairroResponsavel: dados.enderecoResidencia.bairro ?? null,
      },
    });

    await tx.opcao.createMany({
      data: dados.opcoes.map((opcao, indice) => ({
        inscricaoId: inscricao.id,
        ordem: indice + 1,
        unidadeEscCodigo: opcao.unidadeEscCodigo,
        grupamento,
        turno: opcao.turno,
        estado: "NA_FILA",
      })),
    });

    await tx.resposta.createMany({
      data: dados.respostas.map((r) => ({
        inscricaoId: inscricao.id,
        perguntaId: r.perguntaId,
        resposta: r.resposta,
        confirmado: "Nao",
      })),
    });

    await tx.inscPerfilInscricao.create({
      data: {
        inscricaoId: inscricao.id,
        cpfCrianca: cpfCriancaNormalizado,
        cpfResponsavel: cpfResponsavelNormalizado,
        cepResidencia: dados.enderecoResidencia.cep,
        logradouroResidencia: dados.enderecoResidencia.logradouro ?? null,
        bairroResidencia: dados.enderecoResidencia.bairro ?? null,
        latResidencia: dados.enderecoResidencia.latitude ?? null,
        lonResidencia: dados.enderecoResidencia.longitude ?? null,
        origemGeoResidencia: dados.enderecoResidencia.origem,
        cepTrabalho: dados.enderecoTrabalho?.cep ?? null,
        logradouroTrabalho: dados.enderecoTrabalho?.logradouro ?? null,
        bairroTrabalho: dados.enderecoTrabalho?.bairro ?? null,
        latTrabalho: dados.enderecoTrabalho?.latitude ?? null,
        lonTrabalho: dados.enderecoTrabalho?.longitude ?? null,
        origemGeoTrabalho: dados.enderecoTrabalho?.origem ?? null,
      },
    });

    await tx.inscContextoSeguranca.create({
      data: {
        inscricaoId: inscricao.id,
        areaSobInfluencia: dados.contextoSeguranca.areaSobInfluencia,
        faccaoRelatada: dados.contextoSeguranca.faccaoRelatada ?? null,
      },
    });

    return inscricao.id;
  });

  return { inscricaoId };
}

/**
 * Contagem agregada de contexto de segurança (para o painel de GESTOR_SME).
 * Piso de k-anonimato: grupo com menos de 5 inscrições devolve null em vez de
 * um total que poderia reidentificar poucas famílias. Nunca exponha `total`/
 * `sim` calculados fora desta função nem devolva a linha individual.
 */
export async function contarContextoSegurancaAgregado(
  poloId?: string
): Promise<{ total: number; sim: number } | null> {
  const where = poloId ? { inscricao: { poloId } } : undefined;

  const total = await prisma.inscContextoSeguranca.count({ where });
  if (total < LIMITE_MINIMO_K_ANONIMATO) {
    return null;
  }

  const sim = await prisma.inscContextoSeguranca.count({
    where: { ...where, areaSobInfluencia: true },
  });

  return { total, sim };
}
