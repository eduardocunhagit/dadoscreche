"""Infraestrutura compartilhada dos geradores de base sintetica.

Determinismo e requisito, nao conveniencia: a base gerada nao e versionada (grande
demais), entao quem clona o repositorio precisa reproduzi-la byte a byte a partir da
seed do config. Por isso nada aqui usa o estado global de `random` -- cada gerador
recebe um `numpy.random.Generator` derivado de (seed, nome, ano).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parent.parent.parent
DIR_BASES_SME = RAIZ / "Bases IC_ ClassificadoseFila"
DIR_DADOS = RAIZ / "dados"
DIR_CONFIG = Path(__file__).resolve().parent.parent / "config"

#: Coluna presente em toda tabela gerada. Existe para que ninguem, em nenhuma
#: circunstancia, confunda estas bases com RAIS ou CadUnico reais.
COLUNA_MARCADORA = "FONTE_SINTETICA"


def carrega_config(nome: str = "geracao.yaml") -> dict:
    return yaml.safe_load((DIR_CONFIG / nome).read_text(encoding="utf-8"))


def rng(seed: int, *contexto: object) -> np.random.Generator:
    """Gerador independente e reproduzivel para um contexto (ex.: "cadunico", 2025).

    Deriva a semente por hash do contexto em vez de usar contadores, para que
    acrescentar um gerador novo nao desloque as sequencias dos que ja existem.
    """
    marca = "|".join(str(c) for c in contexto).encode("utf-8")
    desvio = int.from_bytes(hashlib.sha256(marca).digest()[:4], "big")
    return np.random.default_rng(seed + desvio)


def lognormal(gen: np.random.Generator, mediana: float, dispersao: float, n: int) -> np.ndarray:
    """Valores positivos com assimetria a direita, como renda e salario."""
    return mediana * np.exp(gen.normal(0.0, dispersao, n))


def escreve(df, caminho: Path, descricao: str) -> Path:
    """Grava uma tabela gerada em Parquet, sempre com a coluna marcadora."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if COLUNA_MARCADORA not in df.columns:
        df = df.copy()
        df[COLUNA_MARCADORA] = True
    df.to_parquet(caminho, index=False)
    print(f"  {caminho.relative_to(RAIZ)}: {len(df):,} linhas  ({descricao})".replace(",", "."))
    return caminho
