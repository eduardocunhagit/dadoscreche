"""Normalização determinística de textos e identificadores."""

import re
import unicodedata

import pandas as pd


NULL_STRINGS = {"", "NULL", "NAN", "NONE", "<NA>"}


def normalize_text(values: pd.Series) -> pd.Series:
    """Retorna texto em maiúsculas, sem acentos e com espaços canônicos."""

    def clean(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = re.sub(r"\s+", " ", str(value).strip())
        if text.upper() in NULL_STRINGS:
            return pd.NA
        text = unicodedata.normalize("NFKD", text)
        return "".join(char for char in text if not unicodedata.combining(char)).upper()

    return values.map(clean).astype("string")


def normalize_code(values: pd.Series, width: int | None = None) -> pd.Series:
    """Preserva códigos como texto e remove apenas artefatos de planilha."""

    def clean(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = re.sub(r"\s+", "", str(value).strip())
        if text.upper() in NULL_STRINGS:
            return pd.NA
        if re.fullmatch(r"\d+\.0+", text):
            text = text.split(".", maxsplit=1)[0]
        return text.zfill(width) if width and text.isdigit() else text

    return values.map(clean).astype("string")
