"""
Etapa 5 do pipeline: publica o dataset no HuggingFace Hub.

Converte curriculo_completo.jsonl → Parquet e faz upload junto com o JSONL
e o dataset card (data/dataset_card.md → README.md no repo HF).

Requer HF_TOKEN e HF_REPO_ID no .env.

Uso:
    python pipeline/05_publish_hf.py             # publicação completa
    python pipeline/05_publish_hf.py --dry-run   # valida sem fazer upload
"""

import json
import os
import sys
import argparse
from pathlib import Path

import pandas as pd
from datasets import Dataset, DatasetInfo, Features, Value, Sequence
from dotenv import load_dotenv
from huggingface_hub import HfApi, DatasetCard
from loguru import logger

load_dotenv()

RAIZ        = Path(__file__).parent.parent
JSONL_PATH  = RAIZ / "data" / "processed" / "curriculo_completo.jsonl"
CARD_PATH   = RAIZ / "data" / "dataset_card.md"
LOG_DIR     = RAIZ / "logs"

# Features do dataset conforme o schema
FEATURES = Features({
    "id":                   Value("string"),
    "tipo_registro":        Value("string"),
    "etapa":                Value("string"),
    "area_conhecimento":    Value("string"),
    "componente_curricular": Value("string"),
    "sub_componente":       Value("string"),
    "subeixo_componente":   Value("string"),
    "ciclo":                Value("string"),
    "bloco":                Value("string"),
    "ano_escolar":          Value("string"),
    "eixos_transversais":   Sequence(Value("string")),
    "eixos_integradores":   Sequence(Value("string")),
    "objetivos":            Sequence(Value("string")),
    "conteudos":            Sequence(Value("string")),
    "texto_livre":          Value("string"),
    "needs_review":         Value("bool"),
    "paginas_pdf":          Sequence(Value("int32")),
    "fonte":                Value("string"),
})

# Campos que aceitam null — substituídos por sentinela vazia antes de converter
CAMPOS_NULLABLE_STR  = ["area_conhecimento", "componente_curricular", "sub_componente",
                         "subeixo_componente", "ciclo", "bloco", "ano_escolar", "texto_livre"]
CAMPOS_NULLABLE_LIST = ["objetivos", "conteudos"]


# ---------------------------------------------------------------------------
# Conversão
# ---------------------------------------------------------------------------

def carregar_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def normalizar_nulls(chunk: dict) -> dict:
    """Substitui None por string/lista vazia nos campos nullable para o Arrow."""
    c = dict(chunk)
    for campo in CAMPOS_NULLABLE_STR:
        if c.get(campo) is None:
            c[campo] = ""
    for campo in CAMPOS_NULLABLE_LIST:
        if c.get(campo) is None:
            c[campo] = []
    return c


def jsonl_para_dataset(chunks: list[dict]) -> Dataset:
    normalizados = [normalizar_nulls(c) for c in chunks]
    df = pd.DataFrame(normalizados)
    # garante a ordem das colunas conforme o schema
    df = df[[col for col in FEATURES.keys() if col in df.columns]]
    return Dataset.from_pandas(df, features=FEATURES)


# ---------------------------------------------------------------------------
# Publicação
# ---------------------------------------------------------------------------

def publicar(repo_id: str, token: str, dry_run: bool) -> None:
    api = HfApi(token=token)

    logger.info(f"Carregando chunks de {JSONL_PATH.name}")
    chunks = carregar_jsonl(JSONL_PATH)
    logger.info(f"  {len(chunks)} registros carregados")

    # Verifica needs_review antes de publicar
    nr = sum(1 for c in chunks if c.get("needs_review"))
    if nr > 0:
        logger.error(f"{nr} registro(s) com needs_review=True — rode 03_enrich_llm.py antes de publicar")
        sys.exit(1)

    logger.info("Convertendo para Dataset HF (Parquet)...")
    ds = jsonl_para_dataset(chunks)
    logger.info(f"  Features: {list(FEATURES.keys())}")
    logger.info(f"  Shape: {ds.shape}")

    if dry_run:
        logger.info(f"[DRY-RUN] Publicaria {len(chunks)} registros em {repo_id}")
        logger.info(f"[DRY-RUN] Dataset card: {CARD_PATH}")
        logger.info("[DRY-RUN] Nenhum upload feito.")
        return

    # Upload do Parquet (split 'train')
    logger.info(f"Fazendo push do dataset para {repo_id}...")
    ds.push_to_hub(
        repo_id=repo_id,
        token=token,
        commit_message="feat(dataset): publica curriculo_completo como Parquet",
        private=False,
    )
    logger.success("  Parquet enviado.")

    # Upload do JSONL como arquivo adicional
    logger.info("Enviando JSONL original...")
    api.upload_file(
        path_or_fileobj=str(JSONL_PATH),
        path_in_repo="data/curriculo_completo.jsonl",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="data: adiciona JSONL original junto ao Parquet",
    )
    logger.success("  JSONL enviado.")

    # Upload do dataset card (README.md)
    if CARD_PATH.exists():
        logger.info("Enviando dataset card (README.md)...")
        card_content = CARD_PATH.read_text(encoding="utf-8")
        card = DatasetCard(card_content)
        card.push_to_hub(repo_id, token=token)
        logger.success("  Dataset card enviado.")
    else:
        logger.warning(f"Dataset card não encontrado em {CARD_PATH} — pule ou crie antes de publicar")

    logger.success(f"Dataset publicado: https://huggingface.co/datasets/{repo_id}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def configurar_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
    )
    logger.add(
        LOG_DIR / "publish_hf.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="5 MB",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica curriculo_completo.jsonl no HuggingFace Hub como Parquet"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida a conversão sem fazer upload",
    )
    args = parser.parse_args()

    configurar_logging()

    token = os.getenv("HF_TOKEN")
    repo_id = os.getenv("HF_REPO_ID")

    if not token:
        logger.error("HF_TOKEN não encontrado no .env")
        sys.exit(1)
    if not repo_id:
        logger.error("HF_REPO_ID não encontrado no .env")
        sys.exit(1)

    if not JSONL_PATH.exists():
        logger.error(f"JSONL não encontrado: {JSONL_PATH}")
        sys.exit(1)

    publicar(repo_id=repo_id, token=token, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
