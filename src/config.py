"""Caminhos do projeto, resolvidos a partir da raiz do repositório.

Use sempre estas constantes em vez de caminhos absolutos, para que o código
rode igual em qualquer máquina ou no Google Colab (após clonar o repositório).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
REFERENCE_DIR = DATA_DIR / "reference"
PROCESSED_DIR = DATA_DIR / "processed"  # gerado pelo pipeline; não versionado
EXTERNAL_DIR = DATA_DIR / "external"    # bases públicas do IBGE (src/enrichment/ibge.py); versionado
OUTPUTS_DIR = ROOT / "outputs"            # tabelas-base do pipeline consumidas pelo dashboard

CAGED_PARQUET = RAW_DIR / "Novo_Caged_MOV_Limpo.parquet"
CAGED_CSV = RAW_DIR / "Novo_Caged_MOV_Limpo.csv"  # opcional (Google Drive); não versionado
MUNICIPIOS_CSV = REFERENCE_DIR / "Municipios_SC_limpo.csv"
DICIONARIO_XLSX = REFERENCE_DIR / "Dicionario_de_dados.xlsx"
COORDS_PARQUET = REFERENCE_DIR / "municipios_sc_coords.parquet"
