"""
Etapa 4 do pipeline: valida o curriculo_completo.jsonl contra o schema JSON
e gera um relatório de cobertura por componente, ciclo, bloco e ano escolar.

Uso:
    python pipeline/04_validate.py                 # validação completa
    python pipeline/04_validate.py --strict        # inclui erro de paginas_pdf=[0]
"""

import json
import sys
import argparse
from collections import Counter, defaultdict
from pathlib import Path

import jsonschema
from loguru import logger

RAIZ = Path(__file__).parent.parent
JSONL_ENTRADA = RAIZ / "data" / "processed" / "curriculo_completo.jsonl"
SCHEMA_PATH   = RAIZ / "schema" / "curriculo_schema.json"
LOG_DIR       = RAIZ / "logs"

# Cobertura esperada: todos os anos de cada ciclo/bloco
ANOS_2CICLO_B1 = {"1º Ano", "2º Ano", "3º Ano"}
ANOS_2CICLO_B2 = {"4º Ano", "5º Ano"}
ANOS_3CICLO_B1 = {"6º Ano", "7º Ano"}
ANOS_3CICLO_B2 = {"8º Ano", "9º Ano"}

COBERTURA_ESPERADA = {
    ("2º Ciclo", "1º Bloco"): ANOS_2CICLO_B1,
    ("2º Ciclo", "2º Bloco"): ANOS_2CICLO_B2,
    ("3º Ciclo", "1º Bloco"): ANOS_3CICLO_B1,
    ("3º Ciclo", "2º Bloco"): ANOS_3CICLO_B2,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def carregar_chunks(path: Path) -> list[dict]:
    chunks = []
    with path.open(encoding="utf-8") as f:
        for i, linha in enumerate(f, 1):
            linha = linha.strip()
            if linha:
                chunks.append((i, json.loads(linha)))
    return chunks


def eh_erro_paginas_placeholder(erro: jsonschema.ValidationError) -> bool:
    """True se o erro é exclusivamente pelo placeholder paginas_pdf=[0]."""
    path = list(erro.absolute_path)
    return (
        len(path) >= 1
        and path[0] == "paginas_pdf"
        and "minimum" in erro.message
    )


def validar_chunk(chunk: dict, schema: dict, strict: bool) -> list[str]:
    """Retorna lista de mensagens de erro para o chunk."""
    erros = []
    validator = jsonschema.Draft7Validator(schema)
    for erro in sorted(validator.iter_errors(chunk), key=lambda e: list(e.path)):
        if not strict and eh_erro_paginas_placeholder(erro):
            continue
        caminho = " → ".join(str(p) for p in erro.absolute_path) or "(raiz)"
        erros.append(f"{caminho}: {erro.message}")
    return erros


# ---------------------------------------------------------------------------
# Relatório de cobertura
# ---------------------------------------------------------------------------

def relatorio_cobertura(chunks: list[dict]) -> None:
    curriculo = [c for c in chunks if c.get("tipo_registro") == "curriculo"]

    print("\n" + "=" * 60)
    print("RELATÓRIO DE COBERTURA")
    print("=" * 60)

    # Por componente
    comp_count = Counter(c["componente_curricular"] for c in curriculo)
    print(f"\n{'Componente curricular':<45} {'Chunks':>6}")
    print("-" * 52)
    for comp, n in sorted(comp_count.items(), key=lambda x: -x[1]):
        print(f"  {comp:<43} {n:>6}")
    print(f"  {'TOTAL':<43} {sum(comp_count.values()):>6}")

    # Por ciclo/bloco
    print(f"\n{'Ciclo / Bloco':<25} {'Chunks':>6}")
    print("-" * 32)
    cb_count = Counter((c["ciclo"], c["bloco"]) for c in curriculo)
    for (ciclo, bloco), n in sorted(cb_count.items()):
        print(f"  {ciclo} – {bloco:<14} {n:>6}")

    # Cobertura de anos por componente × ciclo/bloco
    print("\n=== Anos cobertos por componente × ciclo/bloco ===")
    comp_cb_anos: dict = defaultdict(set)
    for c in curriculo:
        chave = (c["componente_curricular"], c["ciclo"], c["bloco"])
        comp_cb_anos[chave].add(c["ano_escolar"])

    lacunas = []
    for (ciclo, bloco), anos_esperados in COBERTURA_ESPERADA.items():
        comps_no_bloco = {k[0] for k in comp_cb_anos if k[1] == ciclo and k[2] == bloco}
        for comp in sorted(comps_no_bloco):
            anos_presentes = comp_cb_anos[(comp, ciclo, bloco)]
            faltando = anos_esperados - anos_presentes
            status = "OK" if not faltando else f"FALTA: {sorted(faltando)}"
            marker = "" if not faltando else " ⚠"
            print(f"  {comp:<40} {ciclo} {bloco}: {status}{marker}")
            if faltando:
                lacunas.append((comp, ciclo, bloco, sorted(faltando)))

    if lacunas:
        print(f"\n  ⚠ {len(lacunas)} combinação(ões) com anos faltando")
    else:
        print("\n  ✓ Todos os anos cobertos em todos os componentes")

    # needs_review
    nr = sum(1 for c in chunks if c.get("needs_review"))
    print(f"\n{'needs_review=True':<40} {nr:>6}")
    if nr == 0:
        print("  ✓ Nenhum registro pendente de revisão")
    else:
        print(f"  ⚠ {nr} registro(s) ainda marcado(s) para revisão")

    print("=" * 60 + "\n")


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
        LOG_DIR / "validate.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="5 MB",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida curriculo_completo.jsonl contra o schema e gera relatório de cobertura"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Trata paginas_pdf=[0] como erro (normalmente é aviso — placeholder conhecido)",
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=JSONL_ENTRADA,
        help=f"JSONL a validar (padrão: {JSONL_ENTRADA.name})",
    )
    args = parser.parse_args()

    configurar_logging()

    if not args.entrada.exists():
        logger.error(f"Arquivo não encontrado: {args.entrada}")
        sys.exit(1)
    if not SCHEMA_PATH.exists():
        logger.error(f"Schema não encontrado: {SCHEMA_PATH}")
        sys.exit(1)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    linhas = carregar_chunks(args.entrada)
    logger.info(f"Validando {len(linhas)} registros de {args.entrada.name}")

    erros_totais = 0
    avisos_paginas = 0
    chunks = []

    for num_linha, chunk in linhas:
        chunks.append(chunk)
        erros = validar_chunk(chunk, schema, strict=args.strict)

        # Conta avisos de paginas_pdf separadamente (modo não-strict)
        if not args.strict:
            validator = jsonschema.Draft7Validator(schema)
            for e in validator.iter_errors(chunk):
                if eh_erro_paginas_placeholder(e):
                    avisos_paginas += 1

        if erros:
            erros_totais += len(erros)
            comp = chunk.get("componente_curricular", "?")
            ciclo = chunk.get("ciclo", "?")
            bloco = chunk.get("bloco", "?")
            ano = chunk.get("ano_escolar", "?")
            logger.error(
                f"Linha {num_linha} [{comp} / {ciclo} / {bloco} / {ano}] — "
                f"{len(erros)} erro(s):"
            )
            for msg in erros:
                logger.error(f"  • {msg}")

    relatorio_cobertura(chunks)

    if not args.strict and avisos_paginas > 0:
        logger.warning(
            f"{avisos_paginas} registro(s) com paginas_pdf=[0] (placeholder — use --strict para tratar como erro)"
        )

    if erros_totais == 0:
        logger.success(f"Validação concluída: {len(linhas)} registros OK, 0 erros de schema")
        sys.exit(0)
    else:
        logger.error(f"Validação falhou: {erros_totais} erro(s) de schema encontrado(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
