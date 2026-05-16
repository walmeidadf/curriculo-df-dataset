"""
Etapa 3 do pipeline: enriquece com LLM os registros com needs_review=True.

Usa Groq / Llama 3.3 70B para preencher o campo ausente (objetivos ou conteúdos)
de cada chunk marcado pelo parser.  A GROQ_API_KEY deve estar em .env.

Uso:
    python pipeline/03_enrich_llm.py                  # processamento completo
    python pipeline/03_enrich_llm.py --dry-run        # imprime prompts sem chamar a API
"""

import json
import os
import re
import sys
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from loguru import logger

load_dotenv()

RAIZ = Path(__file__).parent.parent
JSONL_ENTRADA = RAIZ / "data" / "processed" / "curriculo_parcial.jsonl"
JSONL_SAIDA   = RAIZ / "data" / "processed" / "curriculo_completo.jsonl"
LOG_DIR       = RAIZ / "logs"
MANUAL_LOG    = LOG_DIR / "manual_review.jsonl"

MODELO = "llama-3.3-70b-versatile"
# Pausa entre chamadas para respeitar rate limits do plano free do Groq
PAUSA_ENTRE_CHAMADAS = 1.5  # segundos

SISTEMA = """
Você é um especialista em currículo escolar do Distrito Federal (Brasil).
Você trabalha com o "Currículo em Movimento do Distrito Federal – Ensino Fundamental, 2ª edição, SEEDF".

Dado um registro de currículo com um campo ausente, complete-o com base:
1. no conteúdo já presente no registro
2. nos exemplos de chunks completos do mesmo componente, ciclo e bloco

Responda APENAS com um objeto JSON com o campo solicitado. Nenhum texto adicional.
Exemplos de resposta válida:
  {"objetivos": ["Identificar o uso do número em suas diferentes funções sociais.", "Contar e comparar quantidades até 99."]}
  {"conteudos": ["Funções do número: indicador de quantidade, posição, código e medida", "Leitura e escrita numérica até 99"]}

Regras:
- Use português formal do Brasil
- Siga o estilo dos exemplos (frases curtas, verbos no infinitivo para objetivos)
- Típico: 2 a 6 itens por campo
- Não invente competências fora do nível escolar indicado
""".strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def carregar_chunks(path: Path) -> list[dict]:
    chunks = []
    with path.open(encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                chunks.append(json.loads(linha))
    return chunks


def salvar_chunks(chunks: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def logar_falha(chunk: dict, motivo: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    registro = {"id": chunk["id"], "motivo": motivo, **chunk}
    with MANUAL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def chunks_exemplos(todos: list[dict], alvo: dict, n: int = 3) -> list[dict]:
    """Retorna até n chunks completos do mesmo componente, ciclo e bloco como exemplos."""
    return [
        c for c in todos
        if (
            not c.get("needs_review")
            and c["componente_curricular"] == alvo["componente_curricular"]
            and c["ciclo"] == alvo["ciclo"]
            and c["bloco"] == alvo["bloco"]
            and c["id"] != alvo["id"]
        )
    ][:n]


def formatar_chunk_para_prompt(c: dict) -> str:
    """Serializa um chunk de exemplo de forma legível para o prompt."""
    obj = c.get("objetivos") or []
    con = c.get("conteudos") or []
    linhas = [
        f"Ano: {c.get('ano_escolar')} | Subeixo: {c.get('subeixo_componente') or 'N/A'}",
        f"Objetivos: {json.dumps(obj, ensure_ascii=False)}",
        f"Conteúdos: {json.dumps(con, ensure_ascii=False)}",
    ]
    return "\n".join(linhas)


def construir_prompt(alvo: dict, exemplos: list[dict]) -> str:
    campo_ausente = "conteudos" if not alvo.get("conteudos") else "objetivos"
    campo_presente = "objetivos" if campo_ausente == "conteudos" else "conteudos"

    linhas_exemplos = "\n\n".join(
        f"[Exemplo {i+1}]\n{formatar_chunk_para_prompt(e)}"
        for i, e in enumerate(exemplos)
    )

    return f"""Componente: {alvo['componente_curricular']}
Ciclo: {alvo['ciclo']} | Bloco: {alvo['bloco']} | Ano: {alvo.get('ano_escolar')}
Subeixo: {alvo.get('subeixo_componente') or 'N/A'}

{campo_presente.capitalize()} presentes:
{json.dumps(alvo.get(campo_presente) or [], ensure_ascii=False)}

Exemplos do mesmo componente/ciclo/bloco:
{linhas_exemplos if linhas_exemplos else 'Nenhum exemplo disponível.'}

Complete o campo "{campo_ausente}" ausente deste registro. Responda apenas em JSON."""


def extrair_json(resposta: str) -> dict | None:
    """Extrai o primeiro objeto JSON da resposta do LLM."""
    # Tenta JSON direto
    texto = resposta.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # Tenta extrair bloco de código markdown
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Tenta encontrar qualquer objeto JSON na resposta
    match = re.search(r"\{.*?\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def validar_campo(dados: dict, campo: str) -> list[str] | None:
    """Valida que o campo retornado é uma lista de strings não-vazia."""
    valor = dados.get(campo)
    if not isinstance(valor, list) or not valor:
        return None
    if not all(isinstance(item, str) and item.strip() for item in valor):
        return None
    return [item.strip() for item in valor]


# ---------------------------------------------------------------------------
# Enriquecimento via Groq
# ---------------------------------------------------------------------------

def enriquecer_chunk(
    cliente: Groq,
    alvo: dict,
    todos: list[dict],
    dry_run: bool = False,
) -> dict | None:
    """
    Chama o LLM para preencher o campo ausente.
    Retorna o chunk atualizado ou None em caso de falha.
    """
    campo_ausente = "conteudos" if not alvo.get("conteudos") else "objetivos"
    exemplos = chunks_exemplos(todos, alvo)
    prompt = construir_prompt(alvo, exemplos)

    if dry_run:
        logger.info(f"[DRY-RUN] {alvo['id']} — campo ausente: {campo_ausente}")
        logger.info(f"Prompt:\n{prompt}\n")
        return None

    try:
        resposta = cliente.chat.completions.create(
            model=MODELO,
            messages=[
                {"role": "system", "content": SISTEMA},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        texto_resposta = resposta.choices[0].message.content
        logger.debug(f"Resposta do LLM para {alvo['id']}: {texto_resposta[:200]}")

    except Exception as e:
        logger.error(f"Erro na chamada Groq para {alvo['id']}: {e}")
        logar_falha(alvo, f"erro_api: {e}")
        return None

    dados = extrair_json(texto_resposta)
    if dados is None:
        logger.warning(f"JSON inválido na resposta para {alvo['id']}: {texto_resposta[:200]}")
        logar_falha(alvo, f"json_invalido: {texto_resposta[:200]}")
        return None

    itens = validar_campo(dados, campo_ausente)
    if itens is None:
        logger.warning(f"Campo '{campo_ausente}' inválido na resposta para {alvo['id']}")
        logar_falha(alvo, f"campo_invalido: {dados}")
        return None

    # Atualiza o chunk
    chunk_atualizado = dict(alvo)
    chunk_atualizado[campo_ausente] = itens
    chunk_atualizado["needs_review"] = False
    return chunk_atualizado


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
        LOG_DIR / "enrich_llm.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="5 MB",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enriquece com LLM os registros needs_review=True do curriculo_parcial.jsonl"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime os prompts sem chamar a API",
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=JSONL_ENTRADA,
        help=f"JSONL de entrada (padrão: {JSONL_ENTRADA.name})",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=JSONL_SAIDA,
        help=f"JSONL de saída (padrão: {JSONL_SAIDA.name})",
    )
    args = parser.parse_args()

    configurar_logging()

    if not args.entrada.exists():
        logger.error(f"Arquivo de entrada não encontrado: {args.entrada}")
        sys.exit(1)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key and not args.dry_run:
        logger.error("GROQ_API_KEY não encontrada. Crie um .env com a chave.")
        sys.exit(1)

    todos = carregar_chunks(args.entrada)
    pendentes = [c for c in todos if c.get("needs_review")]
    logger.info(f"Carregados {len(todos)} chunks — {len(pendentes)} com needs_review=True")

    if not pendentes:
        logger.info("Nenhum registro pendente. Copiando entrada para saída.")
        salvar_chunks(todos, args.saida)
        return

    cliente = Groq(api_key=api_key) if not args.dry_run else None

    resultados = list(todos)  # cópia mutável indexada pelo id
    idx_por_id = {c["id"]: i for i, c in enumerate(resultados)}

    n_ok = 0
    n_falha = 0
    for chunk in pendentes:
        campo_ausente = "conteudos" if not chunk.get("conteudos") else "objetivos"
        logger.info(
            f"Enriquecendo [{chunk['componente_curricular']} / {chunk['ciclo']} / "
            f"{chunk['bloco']} / {chunk.get('ano_escolar')}] — falta: {campo_ausente}"
        )

        atualizado = enriquecer_chunk(cliente, chunk, todos, dry_run=args.dry_run)

        if atualizado is not None:
            resultados[idx_por_id[chunk["id"]]] = atualizado
            n_ok += 1
            logger.success(f"  → enriquecido com {len(atualizado[campo_ausente])} itens")
        else:
            n_falha += 1
            logger.warning(f"  → falhou — mantido em needs_review=True")

        if not args.dry_run:
            time.sleep(PAUSA_ENTRE_CHAMADAS)

    if not args.dry_run:
        salvar_chunks(resultados, args.saida)
        total_nr = sum(1 for c in resultados if c.get("needs_review"))
        logger.success(
            f"Salvo: {args.saida} ({len(resultados)} registros) — "
            f"{n_ok} enriquecidos, {n_falha} falhas, {total_nr} ainda needs_review"
        )
    else:
        logger.info(f"[DRY-RUN] {len(pendentes)} prompts exibidos. Nenhum arquivo salvo.")


if __name__ == "__main__":
    main()
