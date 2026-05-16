"""
Etapa 1 do pipeline: extrai o PDF do Currículo em Movimento DF para Markdown
usando o Docling. Resultado salvo em data/extracted/curriculo_completo.md.

Uso:
    python pipeline/01_extract_docling.py
    python pipeline/01_extract_docling.py --pdf caminho/custom.pdf
"""

import argparse
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from loguru import logger

# Caminhos padrão relativos à raiz do projeto
RAIZ = Path(__file__).parent.parent
PDF_PADRAO = RAIZ / "data" / "pdf" / "Ensino Fundamental DF.pdf"
SAIDA_PADRAO = RAIZ / "data" / "extracted" / "curriculo_completo.md"
LOG_DIR = RAIZ / "logs"


def configurar_logging() -> None:
    """Configura loguru: console com nível INFO e arquivo de erros."""
    LOG_DIR.mkdir(exist_ok=True)
    # Remove o sink padrão e reconfigura com formato limpo
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
    )
    logger.add(
        LOG_DIR / "extract_docling.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="1 MB",
    )


def construir_conversor() -> DocumentConverter:
    """
    Configura o DocumentConverter do Docling para extração de tabelas e texto.
    Desabilita OCR (PDF tem texto nativo) para acelerar a extração.
    """
    opcoes_pdf = PdfPipelineOptions(
        do_ocr=False,           # PDF tem texto nativo — OCR desnecessário
        do_table_structure=True,  # Essencial para capturar as tabelas de objetivos/conteúdos
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=opcoes_pdf)
        }
    )


def extrair_pdf(caminho_pdf: Path, caminho_saida: Path) -> None:
    """
    Converte o PDF para Markdown e salva no caminho de saída.

    Args:
        caminho_pdf: Caminho para o arquivo PDF de entrada.
        caminho_saida: Caminho para o arquivo Markdown de saída.
    """
    if not caminho_pdf.exists():
        logger.error(f"PDF não encontrado: {caminho_pdf}")
        raise FileNotFoundError(caminho_pdf)

    tamanho_mb = caminho_pdf.stat().st_size / 1_048_576
    logger.info(f"Iniciando extração: {caminho_pdf.name} ({tamanho_mb:.1f} MB)")

    conversor = construir_conversor()

    logger.info("Convertendo PDF → Markdown (pode levar alguns minutos)…")
    resultado = conversor.convert(str(caminho_pdf))

    markdown = resultado.document.export_to_markdown()
    linhas = markdown.count("\n")
    logger.info(f"Conversão concluída: {linhas:,} linhas de Markdown geradas")

    # Garante que o diretório de saída existe
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_saida.write_text(markdown, encoding="utf-8")

    tamanho_saida_kb = caminho_saida.stat().st_size / 1024
    logger.info(f"Salvo em: {caminho_saida} ({tamanho_saida_kb:.0f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai PDF do Currículo DF para Markdown via Docling"
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=PDF_PADRAO,
        help=f"Caminho para o PDF de entrada (padrão: {PDF_PADRAO.name})",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_PADRAO,
        help=f"Caminho para o Markdown de saída (padrão: {SAIDA_PADRAO.name})",
    )
    args = parser.parse_args()

    configurar_logging()
    extrair_pdf(args.pdf, args.saida)
    logger.success("Etapa 1 concluída com sucesso.")


if __name__ == "__main__":
    main()
