"""
Stage 2 — Preprocess CSIC 2010 (v2)

Genera features estructuradas desde el CSV crudo del dataset CSIC 2010.
Output: features_v5.parquet (27 features + label)

v1: baseline original (23 features)
v2: + 4 ratio features basadas en FP analysis

Uso:
    python -m src.mlsec.data.preprocess_csic \
        --input data/raw/csic2010/csic_database.csv \
        --output data/processed/csic2010/features_v5.parquet
"""

import argparse
import re
from pathlib import Path

import pandas as pd
import numpy as np

# Patrones regex para features
PCT27_RE = re.compile(r'%27')          # Quote (')
PCT3C_RE = re.compile(r'%3[cC]')        # Less-than (<)
DASHDASH_RE = re.compile(r'--')         # SQL comment
SCRIPT_RE = re.compile(r'<script', re.IGNORECASE)
SELECT_RE = re.compile(r'\bselect\b', re.IGNORECASE)

# Features de URL
URL_FEATURES = [
    'url_length', 'url_param_count', 'url_pct_density',
    'url_path_depth', 'url_query_length', 'url_has_query',
    'url_has_pct27', 'url_has_pct3c', 'url_has_dashdash',
    'url_has_script', 'url_has_select',
]

# Features de content
CONTENT_FEATURES = [
    'content_length', 'content_pct_density', 'content_param_count',
    'content_param_density',
    'content_has_pct27', 'content_has_pct3c', 'content_has_dashdash',
    'content_has_script', 'content_has_select',
]

# Features de ratio (v5 — FP analysis)
RATIO_FEATURES = [
    'url_query_ratio',       # url_query_length / url_length
    'content_url_ratio',     # content_length / url_query_length
    'is_long_post',          # method_is_post AND content_length > 100
    'url_length_get',        # url_length * method_is_get (solo para GETs largos)
]

ALL_FEATURES = (
    ['method_is_get', 'method_is_post', 'method_is_put']
    + URL_FEATURES
    + CONTENT_FEATURES
    + RATIO_FEATURES
)


def build_url_features(df: pd.DataFrame) -> pd.DataFrame:
    """Genera features desde la columna URL."""
    url = df["URL"].fillna("")

    # v1/v2 — features basicas
    df["url_length"] = url.str.len().astype("int32")
    df["url_param_count"] = url.str.count("=").astype("int16")
    df["url_pct_density"] = (url.str.count("%") / url.str.len().clip(lower=1)).astype("float32")

    # v4 — estructura de URL
    url_path = url.str.split("?").str[0]
    url_query = url.str.split("?").str[1].fillna("")
    df["url_path_depth"] = url_path.str.count("/").astype("int16")
    df["url_query_length"] = url_query.str.len().astype("int32")
    df["url_has_query"] = url.str.contains("?", regex=False).astype("int8")

    # Indicadores de texto (percent-encoded)
    indicators = {
        "pct27": "%27",
        "pct3c": "%3C",
        "dashdash": "--",
        "script": "script",
        "select": "SELECT",
    }
    for name, pattern in indicators.items():
        df[f"url_has_{name}"] = url.str.contains(pattern, case=False, regex=False).astype("int8")

    return df


def build_content_features(df: pd.DataFrame) -> pd.DataFrame:
    """Genera features desde la columna content."""
    content = df["content"].fillna("")

    # v1/v2 — features basicas
    df["content_length"] = content.str.len().astype("int32")
    df["content_pct_density"] = (content.str.count("%") / content.str.len().clip(lower=1)).astype("float32")
    df["content_param_count"] = content.str.count("=").astype("int16")

    # v6 — densidad de parametros relativa al tamano del body
    df["content_param_density"] = (
        df["content_param_count"] / df["content_length"].clip(lower=1)
    ).astype("float32")

    # Indicadores de texto en body POST
    indicators = {
        "pct27": "%27",
        "pct3c": "%3C",
        "dashdash": "--",
        "script": "script",
        "select": "SELECT",
    }
    for name, pattern in indicators.items():
        df[f"content_has_{name}"] = content.str.contains(pattern, case=False, regex=False).astype("int8")

    return df


def encode_method(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encoding de Method HTTP."""
    method = df["Method"].str.upper()
    df["method_is_get"] = (method == "GET").astype("int8")
    df["method_is_post"] = (method == "POST").astype("int8")
    df["method_is_put"] = (method == "PUT").astype("int8")
    return df


def build_ratio_features(df: pd.DataFrame) -> pd.DataFrame:
    """Genera features de ratio (v5 — basadas en FP analysis).

    Causa raíz de FP: requests largos (POST con content_length > 50,
    GET con url_length > 100) que el modelo confunde con ataques.

    Las features de ratio capturan 'proporción' no solo magnitud:
    - url_query_ratio: query vs total URL (legítimo = query grande)
    - content_url_ratio: body vs query (ataque = content >> query)
    - is_long_post: flag para POST con body sospechoso
    - url_length_get: interacción largo × método
    """
    # url_query_ratio: qué % de la URL es query string
    df["url_query_ratio"] = (
        df["url_query_length"] / df["url_length"].clip(lower=1)
    ).astype("float32")

    # content_url_ratio: content vs query (ataques tienen content >> query)
    df["content_url_ratio"] = (
        df["content_length"] / df["url_query_length"].clip(lower=1)
    ).astype("float32")

    # is_long_post: POST con body > 100 chars (flag para requests sospechosos)
    df["is_long_post"] = (
        (df["method_is_post"] == 1) & (df["content_length"] > 100)
    ).astype("int8")

    # url_length_get: url_length solo para GETs (0 para POST/PUT)
    # Captura GETs largueros vs POSTs normales
    df["url_length_get"] = (
        df["url_length"] * df["method_is_get"]
    ).astype("int32")

    return df


def process(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera features desde el CSV crudo de CSIC 2010.

    Args:
        df: DataFrame con columnas del CSV original

    Returns:
        DataFrame con features + label
    """
    print(f"Procesando {len(df):,} registros...")

    # Renombrar classification -> label
    df = df.rename(columns={"classification": "label"})
    df["label"] = df["label"].astype("int8")

    # Build features
    df = build_url_features(df)
    df = build_content_features(df)
    df = encode_method(df)
    df = build_ratio_features(df)

    # Seleccionar solo feature columns + label
    result = df[ALL_FEATURES + ["label"]].copy()

    print(f"  Features generadas: {len(ALL_FEATURES)}")
    print(f"  Label dist: {result['label'].value_counts().to_dict()}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Stage 2 — Preprocess CSIC 2010")
    parser.add_argument("--input", required=True, help="Path al CSV crudo")
    parser.add_argument("--output", required=True, help="Path al parquet de output")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        raise FileNotFoundError(input_path)

    print(f"Cargando dataset: {input_path}")
    df = pd.read_csv(input_path)
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")

    # Process
    result = process(df)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)

    print(f"\nFeatures guardadas: {output_path}")
    print(f"  Shape: {result.shape}")
    print(f"  Features: {len(ALL_FEATURES)}")
    print(f"  Label balance: {result['label'].value_counts().to_dict()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())