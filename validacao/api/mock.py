"""Servidor mock do motor de validacao.

Existe para a parte 1 (site) ser desenvolvida antes de as bases existirem. Responde
no formato definitivo do contrato (`validacao.motor.modelos`), com dados inventados.

Determinismo: a resposta depende so de (responsavel, ano, perg_id) via hash estavel,
entao a mesma chave devolve sempre o mesmo resultado -- da para guardar um caso de
teste e voltar nele. Nao usa random.

Chaves reservadas para forcar cenarios na tela:

    responsavel_TESTE_TUDO       todos os criterios cobertos vem VALIDADO
    responsavel_TESTE_NADA       todos vem NAO_ENCONTRADO
    responsavel_TESTE_DIVERGE    todos os cobertos vem DIVERGENTE (revisao manual)
    responsavel_TESTE_FORA       a fonte CADUNICO vem FONTE_INDISPONIVEL

Subir com:  uvicorn validacao.api.mock:app --reload --port 8000
Documentacao interativa em http://localhost:8000/docs
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException

from validacao.motor.modelos import (
    AcaoNecessaria,
    CriterioValidado,
    Fonte,
    Pontuacao,
    RequisicaoValidacao,
    ResultadoInscricao,
    RespostaValidacao,
    StatusValidacao,
    Sujeito,
)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
EXTRACAO_FICTICIA = date(2025, 11, 30)

app = FastAPI(
    title="Motor de validacao de criterios da fila de creche (MOCK)",
    description=__doc__,
    version="0.1.0-mock",
)


def carrega_regua(ano: int) -> dict:
    caminho = CONFIG_DIR / f"criterios_{ano}.yaml"
    if not caminho.exists():
        disponiveis = sorted(p.stem.split("_")[-1] for p in CONFIG_DIR.glob("criterios_*.yaml"))
        raise HTTPException(404, f"Sem regua para {ano}. Anos disponiveis: {', '.join(disponiveis)}")
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def _sorteio(*partes: object) -> float:
    """Pseudo-aleatorio estavel em [0, 1) a partir das partes. Sem random: a mesma
    entrada devolve sempre o mesmo numero, entre execucoes e entre maquinas."""
    semente = "|".join(str(p) for p in partes).encode("utf-8")
    return int.from_bytes(hashlib.sha256(semente).digest()[:8], "big") / 2**64


def _resolve(crit: dict, responsavel: str, crianca: str, ano: int,
             declarado: bool | None) -> tuple[StatusValidacao, bool | None]:
    """Decide status e valor. Reproduz as proporcoes que a base real sugere: o
    CadUnico cobre cerca de metade da fila, e a maioria de quem declara de fato atende."""
    if crit["cobertura"] != "valida":
        return StatusValidacao.SEM_FONTE, None

    if responsavel == "responsavel_TESTE_FORA" and crit["fonte"] == "CADUNICO":
        return StatusValidacao.FONTE_INDISPONIVEL, None
    if responsavel == "responsavel_TESTE_TUDO":
        return StatusValidacao.VALIDADO, True
    if responsavel == "responsavel_TESTE_NADA":
        return StatusValidacao.NAO_ENCONTRADO, False
    if responsavel == "responsavel_TESTE_DIVERGE":
        return StatusValidacao.DIVERGENTE, False

    chave = crianca if crit["sujeito"] == Sujeito.CRIANCA.value else responsavel
    valor = _sorteio(chave, ano, crit["perg_id"]) < 0.45

    if valor:
        return StatusValidacao.VALIDADO, True
    if declarado is True:
        return StatusValidacao.DIVERGENTE, False
    return StatusValidacao.NAO_ENCONTRADO, False


def _explica(crit: dict, status: StatusValidacao) -> tuple[str, AcaoNecessaria]:
    nome = crit["fonte"] or "nenhuma base"
    if status is StatusValidacao.VALIDADO:
        return (f"Confirmado automaticamente em {nome}. Nao e preciso anexar documento.",
                AcaoNecessaria.NENHUMA)
    if status is StatusValidacao.NAO_ENCONTRADO:
        return (f"Consultamos {nome} e nao localizamos este criterio. Se voce atende, "
                "podera comprova-lo normalmente.", AcaoNecessaria.ANEXAR_DOCUMENTO)
    if status is StatusValidacao.DIVERGENTE:
        return ("Voce declarou que atende, mas nao localizamos confirmacao na base. "
                "Sua declaracao foi mantida e sera analisada por uma pessoa -- voce nao "
                "perde a pontuacao por causa disto.", AcaoNecessaria.REVISAO_MANUAL)
    if status is StatusValidacao.FONTE_INDISPONIVEL:
        return (f"A consulta a {nome} falhou agora. Anexe o documento; vamos tentar de novo "
                "automaticamente.", AcaoNecessaria.ANEXAR_DOCUMENTO)
    return ("Nao existe base publica que comprove este criterio. A comprovacao segue manual.",
            AcaoNecessaria.ANEXAR_DOCUMENTO)


@app.post("/v1/validacao", response_model=RespostaValidacao)
def validar(req: RequisicaoValidacao) -> RespostaValidacao:
    regua = carrega_regua(req.ano_processo)
    teto = sum(c["pontos"] for c in regua["criterios"])
    inscricoes = []

    for entrada in req.criancas:
        criterios, validados, pendentes = [], 0, 0
        for crit in regua["criterios"]:
            declarado = entrada.declaracoes.get(crit["perg_id"])
            status, valor = _resolve(crit, req.responsavel, entrada.aluno,
                                     req.ano_processo, declarado)
            explicacao, acao = _explica(crit, status)

            leu_base = status in (StatusValidacao.VALIDADO, StatusValidacao.NAO_ENCONTRADO,
                                  StatusValidacao.DIVERGENTE)
            criterios.append(CriterioValidado(
                perg_id=crit["perg_id"], texto=crit["texto"], pontos=crit["pontos"],
                desempate=crit["desempate"], sujeito=Sujeito(crit["sujeito"]),
                status=status, valor=valor, declarado=declarado,
                fonte=Fonte(base=crit["fonte"], campo=crit["campo"],
                            extracao=EXTRACAO_FICTICIA, regra=crit["regra"],
                            versao_regras=regua["versao_regras"]) if leu_base else None,
                explicacao=explicacao, acao_necessaria=acao,
            ))

            if status is StatusValidacao.VALIDADO:
                validados += crit["pontos"]
            elif declarado is True:
                pendentes += crit["pontos"]

        inscricoes.append(ResultadoInscricao(
            crianca=entrada.aluno, criterios=criterios,
            pontuacao=Pontuacao(validada=validados, pendente_comprovacao=pendentes,
                                potencial=validados + pendentes, maxima_regua=teto),
        ))

    return RespostaValidacao(
        responsavel=req.responsavel, ano_processo=req.ano_processo,
        versao_regras=regua["versao_regras"],
        gerado_em=datetime.now(timezone.utc),
        trace_id="mock-" + hashlib.sha256(
            f"{req.responsavel}|{req.ano_processo}".encode()).hexdigest()[:12],
        inscricoes=inscricoes,
    )


@app.get("/v1/regua/{ano}")
def regua(ano: int) -> dict:
    """A regua daquele ano, com cobertura por criterio. Util para o site montar a tela
    de criterios sem precisar chamar a validacao."""
    return carrega_regua(ano)


@app.get("/health")
def health() -> dict:
    anos = sorted(int(p.stem.split("_")[-1]) for p in CONFIG_DIR.glob("criterios_*.yaml"))
    return {"status": "ok", "modo": "mock", "anos_disponiveis": anos}
