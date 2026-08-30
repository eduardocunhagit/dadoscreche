"""Contrato da API de validacao automatica de criterios da fila de creche.

Este modulo E o contrato. O site (parte 1) e o motor (parte 2) conversam pelas
estruturas definidas aqui; qualquer mudanca incompativel deve subir a versao do
endpoint, nao alterar estas classes em silencio.

Duas decisoes de projeto estao codificadas nos tipos e nao devem ser afrouxadas:

1. A validacao automatica NUNCA nega um criterio. Quando a base nao confirma o que
   a familia declarou, o status e DIVERGENTE e a acao e REVISAO_MANUAL -- a familia
   mantem o direito de comprovar. Extrato desatualizado ou incompleto nao pode tirar
   ponto de ninguem.
2. Toda validacao carrega proveniencia (`Fonte`): qual base, qual campo, de que data
   e sob qual versao de regra. Sem isso nao ha como explicar a decisao a familia nem
   atender ao direito de revisao de decisao automatizada (LGPD art. 20).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class StatusValidacao(str, Enum):
    """Resultado da validacao de um criterio. Contrato de UI: o site decide o que
    mostrar e o que pedir a partir deste campo."""

    VALIDADO = "validado"
    """Confirmado em base oficial. O site mostra como provado e NAO pede documento."""

    NAO_ENCONTRADO = "nao_encontrado"
    """A base foi consultada e a familia nao atende ao criterio. Segue o fluxo normal
    de declaracao e comprovacao -- este status nao indefere nada por si so."""

    DIVERGENTE = "divergente"
    """A familia declarou que atende, a base nao confirma. Vai para revisao humana.
    NUNCA vira indeferimento automatico."""

    SEM_FONTE = "sem_fonte"
    """Nenhuma base disponivel responde a esta pergunta. Comprovacao manual, como hoje.
    Ver o campo `nota` do criterio no config para o motivo especifico."""

    FONTE_INDISPONIVEL = "fonte_indisponivel"
    """A fonte existe mas falhou nesta consulta (extrato vencido, servico fora).
    Falha aberta: o site pede o documento e o motor tenta de novo depois."""


class AcaoNecessaria(str, Enum):
    """O que o site deve pedir ao usuario para este criterio."""

    NENHUMA = "nenhuma"
    ANEXAR_DOCUMENTO = "anexar_documento"
    REVISAO_MANUAL = "revisao_manual"


class Sujeito(str, Enum):
    """Sobre quem o criterio pergunta. Determina se o resultado se repete entre
    irmaos (familia) ou e proprio de cada inscricao (crianca)."""

    FAMILIA = "familia"
    CRIANCA = "crianca"


class Fonte(BaseModel):
    """Proveniencia de uma validacao. Obrigatoria sempre que `status` for VALIDADO,
    NAO_ENCONTRADO ou DIVERGENTE -- ou seja, sempre que uma base foi de fato lida."""

    base: str = Field(description="CADUNICO, RAIS ou SME_INTERNO")
    campo: str | None = Field(default=None, description="Campo consultado, ex.: COD_EST_CADASTRAL_FAM")
    extracao: date = Field(description="Data do extrato usado -- nao a data da consulta")
    regra: str = Field(description="Nome da regra aplicada, ex.: cadunico_inscrita")
    versao_regras: str = Field(description="Versao do conjunto de regras, ex.: v1")


class CriterioValidado(BaseModel):
    """Um criterio da regua, com o que o motor conseguiu apurar sobre ele."""

    perg_id: int = Field(description="Identificador estavel da pergunta no catalogo (QueryC)")
    texto: str = Field(description="Texto da pergunta, para o site nao manter copia propria da regua")
    pontos: int = Field(description="Peso na classificacao naquele ano")
    desempate: bool = Field(description="True quando vale 0 pontos e serve so como desempate")
    sujeito: Sujeito

    status: StatusValidacao
    valor: bool | None = Field(
        default=None,
        description="O que a base diz. None quando nao foi possivel determinar "
                    "(SEM_FONTE, FONTE_INDISPONIVEL).",
    )
    declarado: bool | None = Field(
        default=None,
        description="O que a familia declarou, quando o site informou. Usado para detectar divergencia.",
    )
    fonte: Fonte | None = None
    explicacao: str = Field(description="Frase em portugues, exibivel a familia, dizendo o que houve")
    acao_necessaria: AcaoNecessaria


class Pontuacao(BaseModel):
    """Resumo da pontuacao de uma inscricao. `validada + pendente_comprovacao` nao
    precisa somar `potencial`: pendente conta so o que a familia declarou e ainda
    nao provou."""

    validada: int = Field(description="Pontos ja provados por cruzamento -- entram na classificacao hoje")
    pendente_comprovacao: int = Field(description="Pontos declarados que ainda dependem de documento")
    potencial: int = Field(description="validada + pendente_comprovacao")
    maxima_regua: int = Field(description="Teto de pontos do ano, para o site mostrar proporcao")


class CriancaEntrada(BaseModel):
    """Uma crianca a validar, com o que a familia ja declarou no formulario (se ja declarou)."""

    aluno: str = Field(description="Chave da crianca. Hoje aluno_anon; em producao, CPF/DNV")
    declaracoes: dict[int, bool] = Field(
        default_factory=dict,
        description="perg_id -> resposta da familia. Vazio na primeira chamada, antes do preenchimento.",
    )


class RequisicaoValidacao(BaseModel):
    responsavel: str = Field(description="Chave do responsavel. Hoje responsavel_anon; em producao, CPF")
    ano_processo: int
    criancas: list[CriancaEntrada]


class ResultadoInscricao(BaseModel):
    """Resultado por crianca. Criterios de familia se repetem entre irmaos, de proposito:
    cada crianca tem sua propria posicao na fila e sua propria tela."""

    crianca: str
    criterios: list[CriterioValidado]
    pontuacao: Pontuacao


class RespostaValidacao(BaseModel):
    responsavel: str
    ano_processo: int
    versao_regras: str
    gerado_em: datetime
    trace_id: str = Field(description="Identificador desta consulta, para auditoria e suporte")
    inscricoes: list[ResultadoInscricao]
