"""
06_gradio_space.py — Deploy do Gradio Space no HuggingFace Hub

Empacota os arquivos em space/ (app.py, requirements.txt, README.md)
e faz upload para o Space walmeidadf/curriculo-ensinofundamental-df.

Uso:
    python pipeline/06_gradio_space.py

Requer HF_TOKEN no .env com permissão de escrita no Space.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi, SpaceInfo
from loguru import logger

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
SPACE_ID = "walmeidadf/curriculo-ensinofundamental-df"
SPACE_DIR = Path(__file__).parent.parent / "space"
ARQUIVOS = ["app.py", "requirements.txt", "README.md"]


def verificar_arquivos() -> bool:
    """Verifica se todos os arquivos do Space existem localmente."""
    faltando = [f for f in ARQUIVOS if not (SPACE_DIR / f).exists()]
    if faltando:
        logger.error(f"Arquivos ausentes em space/: {faltando}")
        return False
    return True


def verificar_space(api: HfApi) -> bool:
    """Verifica se o Space existe no HuggingFace Hub."""
    try:
        info: SpaceInfo = api.space_info(SPACE_ID)
        logger.info(f"Space encontrado: {info.id} (sdk={info.sdk})")
        return True
    except Exception as e:
        logger.error(f"Space {SPACE_ID} não encontrado: {e}")
        logger.info("Crie o Space manualmente em huggingface.co/new-space antes de rodar este script.")
        return False


def fazer_upload(api: HfApi) -> None:
    """Faz upload de todos os arquivos do Space para o Hub."""
    for nome in ARQUIVOS:
        caminho = SPACE_DIR / nome
        logger.info(f"Enviando {nome}...")
        api.upload_file(
            path_or_fileobj=str(caminho),
            path_in_repo=nome,
            repo_id=SPACE_ID,
            repo_type="space",
            commit_message=f"chore: atualiza {nome}",
        )
        logger.success(f"  ✓ {nome}")


def main() -> None:
    if not HF_TOKEN:
        logger.error("HF_TOKEN não encontrado no .env")
        sys.exit(1)

    if not verificar_arquivos():
        sys.exit(1)

    api = HfApi(token=HF_TOKEN)

    if not verificar_space(api):
        sys.exit(1)

    logger.info(f"Iniciando deploy para {SPACE_ID}...")
    fazer_upload(api)

    url_space = f"https://huggingface.co/spaces/{SPACE_ID}"
    logger.success(f"Deploy concluído! Space disponível em: {url_space}")


if __name__ == "__main__":
    main()
