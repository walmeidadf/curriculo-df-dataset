"""
Etapa 2 do pipeline: converte o Markdown extraído pelo Docling em registros JSONL
seguindo o schema em schema/curriculo_schema.json.

Uso:
    # Modo preview: processa só Língua Portuguesa e imprime 5 chunks de exemplo
    python pipeline/02_parse_structure.py --preview

    # Processamento completo → data/processed/curriculo_parcial.jsonl
    python pipeline/02_parse_structure.py
"""

import re
import json
import uuid
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass, field

from loguru import logger

RAIZ = Path(__file__).parent.parent
MD_ENTRADA = RAIZ / "data" / "extracted" / "curriculo_completo.md"
JSONL_SAIDA = RAIZ / "data" / "processed" / "curriculo_parcial.jsonl"
LOG_DIR = RAIZ / "logs"

FONTE = "Currículo em Movimento do Distrito Federal – Ensino Fundamental, 2ª edição, SEEDF"
ETAPA = "Ensino Fundamental"

# Áreas de conhecimento reconhecidas no heading EIXOS INTEGRADORES (ordem importa: mais longo primeiro)
AREAS_CONHECIMENTO = [
    "CIÊNCIAS DA NATUREZA",
    "CIÊNCIAS HUMANAS",
    "ENSINO RELIGIOSO",
    "LINGUAGENS",
    "MATEMÁTICA",
]

# Normalização dos eixos transversais (o documento tem variações de grafia)
EIXOS_TRANSVERSAIS_CANONICOS = [
    "Educação para a Diversidade",
    "Cidadania e Educação em e para os Direitos Humanos",
    "Educação para a Sustentabilidade",
]

# Normalização dos eixos integradores
EIXOS_INT_2CICLO = ["Alfabetização", "Letramentos", "Ludicidade"]
EIXOS_INT_3CICLO = ["Letramentos", "Ludicidade"]

# Headings de página (rodapé/cabeçalho repetitivo do Docling — ignorar para estado)
HEADINGS_IGNORAR = re.compile(
    r"Currículo em Movimento|Anos Iniciais|Anos Finais|LINGUAGENS\s+LÍNGUA|LINGUAGENS\s+ARTE",
    re.IGNORECASE,
)

# Padrão de ciclo/bloco: pode aparecer inline no heading ou como linha avulsa
RE_CICLO_BLOCO = re.compile(r"(\d)º\s*CICLO\s*-\s*(\d)º\s*BLOCO", re.IGNORECASE)

# Padrão para identificar a linha de cabeçalho de ano de uma tabela
RE_ANO_HEADER = re.compile(r"\d+º\s*ANO", re.IGNORECASE)

# Padrão para identificar célula de tipo OBJ/CON (segunda linha do cabeçalho da tabela)
RE_OBJ_CON = re.compile(r"\b(OBJETIVOS|CONTEÚDOS)\b", re.IGNORECASE)

# Separador de bullets no texto extraído pelo Docling
BULLET = "•"


# ---------------------------------------------------------------------------
# Estado da máquina de estados
# ---------------------------------------------------------------------------

@dataclass
class Estado:
    area_conhecimento: str = None
    componente_curricular: str = None
    sub_componente: str = None
    ciclo: str = None        # "2º Ciclo" | "3º Ciclo"
    bloco: str = None        # "1º Bloco" | "2º Bloco"
    eixos_transversais: list = field(default_factory=list)
    eixos_integradores: list = field(default_factory=list)
    subeixo_atual: str = None   # persiste entre fragmentos de tabela do mesmo bloco
    secao_ativa: bool = False   # True enquanto dentro de uma seção com tabelas

    def copia_contexto(self) -> dict:
        """Retorna snapshot do contexto atual (imutável por chunk)."""
        return {
            "area_conhecimento": self.area_conhecimento,
            "componente_curricular": self.componente_curricular,
            "sub_componente": self.sub_componente,
            "ciclo": self.ciclo,
            "bloco": self.bloco,
            "eixos_transversais": list(self.eixos_transversais),
            "eixos_integradores": list(self.eixos_integradores),
        }


# ---------------------------------------------------------------------------
# Parsing dos headings
# ---------------------------------------------------------------------------

def _normalizar_eixos_transversais(texto: str) -> list[str]:
    """Sempre retorna os 3 eixos canônicos (o texto varia por erros tipográficos)."""
    if "EIXOS TRANSVERSAIS" in texto.upper():
        return list(EIXOS_TRANSVERSAIS_CANONICOS)
    return []


def _extrair_eixos_integradores(texto: str) -> list[str]:
    """Inferee os eixos integradores a partir do texto do heading."""
    texto_up = texto.upper()
    if "ALFABETIZAÇÃO" in texto_up:
        return list(EIXOS_INT_2CICLO)
    return list(EIXOS_INT_3CICLO)


def _extrair_componente_sub(texto_rest: str) -> tuple[str, str | None]:
    """
    Dado o trecho após a área (ex: '- ARTE: ARTES VISUAIS 3º CICLO...'),
    retorna (componente, sub_componente).
    """
    # Remove ciclo/bloco do final para não confundir com componente
    texto_limpo = RE_CICLO_BLOCO.sub("", texto_rest).strip().lstrip("-").strip()

    if ":" in texto_limpo:
        partes = texto_limpo.split(":", 1)
        componente = _titulo(partes[0].strip())
        sub = _titulo(partes[1].strip()) if partes[1].strip() else None
        return componente, sub

    componente = _titulo(texto_limpo) if texto_limpo else None
    return componente, None


def _titulo(texto: str) -> str | None:
    """Converte texto MAIÚSCULO para Title Case com correções pontuais."""
    if not texto:
        return None
    # Capitalização simples e normalização de espaços
    resultado = texto.strip().title()
    # Correções: preposições e artigos não devem ser capitalizados no meio
    for palavra in ["De", "Da", "Do", "Em", "E", "A", "O", "Para", "Com", "Por", "Ou"]:
        resultado = re.sub(rf"(?<=\s){palavra}(?=\s)", palavra.lower(), resultado)
    return resultado


def processar_heading_eixos_int(linha: str, estado: Estado) -> bool:
    """
    Processa um heading de EIXOS INTEGRADORES e atualiza o estado.
    Retorna True se processou com sucesso.
    """
    # Remove o prefixo "## EIXOS INTEGRADORES - "
    texto = re.sub(r"^##\s*EIXOS INTEGRADORES\s*-\s*", "", linha, flags=re.IGNORECASE).strip()

    # Identifica a área de conhecimento (procura o nome mais longo primeiro)
    area_encontrada = None
    idx_area = -1
    for area in AREAS_CONHECIMENTO:
        idx = texto.upper().find(area)
        if idx >= 0:
            area_encontrada = area
            idx_area = idx
            break

    if area_encontrada is None:
        logger.warning(f"Área não identificada no heading: {linha[:80]}")
        estado.needs_review_proximo = True
        return False

    # Texto antes da área = eixos integradores
    ei_texto = texto[:idx_area]
    estado.eixos_integradores = _extrair_eixos_integradores(ei_texto)

    # Área de conhecimento
    estado.area_conhecimento = _titulo(area_encontrada)

    # Texto após a área = "- COMPONENTE[: SUB][ Xº CICLO - Yº BLOCO]"
    texto_pos_area = texto[idx_area + len(area_encontrada):].strip()

    # Extrai ciclo/bloco inline (se presente)
    m_cb = RE_CICLO_BLOCO.search(texto_pos_area)
    if m_cb:
        estado.ciclo = f"{m_cb.group(1)}º Ciclo"
        estado.bloco = f"{m_cb.group(2)}º Bloco"

    # Extrai componente e sub_componente
    componente, sub = _extrair_componente_sub(texto_pos_area)

    # Para áreas que SÃO o próprio componente (Matemática, Ciências da Natureza, Ensino Religioso)
    if area_encontrada in ("MATEMÁTICA", "CIÊNCIAS DA NATUREZA", "ENSINO RELIGIOSO") and not componente:
        componente = _titulo(area_encontrada)

    estado.componente_curricular = componente
    estado.sub_componente = sub
    estado.subeixo_atual = None   # nova seção, reset do subeixo acumulado
    estado.secao_ativa = True

    return True


# ---------------------------------------------------------------------------
# Parsing de células de tabela
# ---------------------------------------------------------------------------

def dividir_linha_tabela(linha: str) -> list[str]:
    """Divide uma linha pipe-separated e retorna lista de células sem espaços extras."""
    partes = linha.split("|")
    # Remove primeira e última (sempre vazias por causa do | inicial e final)
    return [p.strip() for p in partes[1:-1]]


def detectar_subeixo(texto_celula: str) -> tuple[str | None, str]:
    """
    Analisa o texto de uma célula OBJETIVOS.
    Retorna (subeixo, texto_sem_subeixo).

    O subeixo é o texto antes do primeiro bullet (•), desde que:
    - Comece com letra maiúscula (exclui continuações de frases em minúscula)
    - Não contenha ponto final (exclui fragmentos de frase)
    - Tenha no máximo 120 caracteres (exclui parágrafos)
    """
    if not texto_celula.strip():
        return None, texto_celula

    if BULLET not in texto_celula:
        return None, texto_celula

    idx_bullet = texto_celula.index(BULLET)
    antes = texto_celula[:idx_bullet].strip()
    depois = texto_celula[idx_bullet:]  # mantém o • inicial

    if not antes:
        return None, texto_celula

    # Heurísticas para rejeitar falsos subeixos (continuações de frase)
    if "." in antes:          # fragmentos de frase terminam em ponto
        return None, texto_celula
    if antes[0].islower():    # continuações começam com minúscula
        return None, texto_celula
    if len(antes) > 120:      # parágrafos são muito longos para ser rótulo
        return None, texto_celula

    return antes, depois


def parse_bullets(texto: str) -> list[str]:
    """
    Divide o texto em itens bullet (separados por •).
    Sub-bullets marcados com 'o ' (letra o isolada no início do fragmento após •)
    são concatenados ao item-pai com '; '.
    """
    if not texto.strip():
        return []

    partes = texto.split(BULLET)
    itens = []
    item_atual = None

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue

        # Sub-bullet: o fragmento inteiro começa com 'o <espaço>' — letra o isolada
        # (não confundir com 'o' no meio de palavras como 'o professor', 'ou', 'objetivo')
        sub_match = re.match(r"^o\s+(.+)", parte)
        if sub_match and item_atual is not None:
            item_atual += "; " + sub_match.group(1).strip()
        else:
            if item_atual is not None:
                itens.append(item_atual)
            item_atual = parte

    if item_atual:
        itens.append(item_atual)

    return [i for i in itens if i]


# ---------------------------------------------------------------------------
# Criação de chunks do schema
# ---------------------------------------------------------------------------

def criar_chunk(
    ctx: dict,
    ano_escolar: str,
    subeixo: str | None,
    objetivos: list[str],
    conteudos: list[str],
    needs_review: bool = False,
) -> dict:
    """Cria um registro conforme o schema curriculo_schema.json."""
    # Para 3º Ciclo, subeixo_componente = null (decisão de design)
    subeixo_final = None if ctx["ciclo"] == "3º Ciclo" else subeixo

    # Se objetivos ou conteúdos estão vazios, marca para revisão
    if not objetivos or not conteudos:
        needs_review = True

    return {
        "id": str(uuid.uuid4()),
        "tipo_registro": "curriculo",
        "etapa": ETAPA,
        "area_conhecimento": ctx["area_conhecimento"],
        "componente_curricular": ctx["componente_curricular"],
        "sub_componente": ctx["sub_componente"],
        "ciclo": ctx["ciclo"],
        "bloco": ctx["bloco"],
        "ano_escolar": ano_escolar,
        "subeixo_componente": subeixo_final,
        "eixos_transversais": ctx["eixos_transversais"],
        "eixos_integradores": ctx["eixos_integradores"],
        "objetivos": objetivos if objetivos else None,
        "conteudos": conteudos if conteudos else None,
        "texto_livre": None,
        "needs_review": needs_review,
        "paginas_pdf": [0],  # placeholder: Docling não embute paginação no MD
        "fonte": FONTE,
    }


# ---------------------------------------------------------------------------
# Acumulador de fragmentos de tabela
# ---------------------------------------------------------------------------

@dataclass
class AcumuladorTabela:
    """
    Acumula texto bruto de células OBJETIVOS e CONTEÚDOS por ano,
    enquanto a tabela se estende por múltiplos fragmentos de página.
    """
    anos: list[str] = field(default_factory=list)
    subeixo: str = None
    # ano → texto acumulado
    obj_texto: dict = field(default_factory=dict)
    con_texto: dict = field(default_factory=dict)

    def inicializar_anos(self, anos_unicos: list[str]) -> None:
        """Registra os anos únicos do bloco. Preserva texto já acumulado."""
        # Mantém apenas anos únicos (preservando ordem)
        for ano in anos_unicos:
            if ano not in self.anos:
                self.anos.append(ano)
            if ano not in self.obj_texto:
                self.obj_texto[ano] = ""
                self.con_texto[ano] = ""

    def adicionar_linha(self, cells: list[str], col_map: list[tuple[str, str]]) -> None:
        """
        Adiciona conteúdo de uma linha ao acumulador.
        col_map: lista de (ano, "OBJ"|"CON") para cada coluna da tabela.
        """
        for i, (ano, tipo) in enumerate(col_map):
            if i >= len(cells):
                break
            txt = cells[i].strip()
            if not txt:
                continue
            if tipo == "OBJ":
                self.obj_texto[ano] = (self.obj_texto.get(ano, "") + " " + txt).strip()
            else:
                self.con_texto[ano] = (self.con_texto.get(ano, "") + " " + txt).strip()

    def flush(self, ctx: dict) -> list[dict]:
        """Gera chunks para todos os anos acumulados e limpa o acumulador."""
        chunks = []
        for ano in self.anos:
            obj_raw = self.obj_texto.get(ano, "")
            con_raw = self.con_texto.get(ano, "")

            # Remove o rótulo do subeixo do início do texto (ele já está capturado)
            if self.subeixo and obj_raw.startswith(self.subeixo):
                obj_raw = obj_raw[len(self.subeixo):].strip()
            if self.subeixo and con_raw.startswith(self.subeixo):
                con_raw = con_raw[len(self.subeixo):].strip()

            objetivos = parse_bullets(obj_raw)
            conteudos = parse_bullets(con_raw)

            if not objetivos and not conteudos:
                continue

            chunk = criar_chunk(ctx, ano, self.subeixo, objetivos, conteudos)
            chunks.append(chunk)

        # Limpa para próximo subeixo
        self.obj_texto = {ano: "" for ano in self.anos}
        self.con_texto = {ano: "" for ano in self.anos}
        self.subeixo = None
        return chunks


# ---------------------------------------------------------------------------
# Parser principal (linha a linha)
# ---------------------------------------------------------------------------

def _is_header_tabela_anos(linha: str) -> bool:
    """True se a linha é o cabeçalho de anos de uma tabela (ex: | 1º ANO | 1º ANO | ...)."""
    if not linha.startswith("|"):
        return False
    return bool(RE_ANO_HEADER.search(linha))


def _is_separator_tabela(linha: str) -> bool:
    """True se a linha é o separador --- de uma tabela."""
    return bool(re.match(r"^\|[-| ]+\|$", linha.strip()))


def _is_header_obj_con(linha: str) -> bool:
    """True se a linha é a linha de OBJETIVOS/CONTEÚDOS (segunda linha de cabeçalho da tabela)."""
    return linha.startswith("|") and bool(RE_OBJ_CON.search(linha))


def _extrair_header_tabela(linha_anos: str) -> tuple[list[str], list[tuple[str, str]]]:
    """
    A partir da linha de anos, retorna (anos_unicos, col_map).
    col_map: lista de (ano, "OBJ"|"CON") para cada coluna da tabela.
    Cada ano aparece duas vezes no header — coluna par = OBJ, ímpar = CON.
    """
    cells = dividir_linha_tabela(linha_anos)
    anos_unicos: list[str] = []
    col_map: list[tuple[str, str]] = []
    coluna_idx = 0  # conta apenas colunas que têm ano

    for c in cells:
        m = re.search(r"(\d+)º\s*ANO", c, re.IGNORECASE)
        if m:
            ano = f"{m.group(1)}º Ano"
            tipo = "OBJ" if coluna_idx % 2 == 0 else "CON"
            col_map.append((ano, tipo))
            if ano not in anos_unicos:
                anos_unicos.append(ano)
            coluna_idx += 1

    return anos_unicos, col_map


def parse_markdown(md_path: Path, preview: bool = False) -> list[dict]:
    """
    Lê o Markdown linha a linha com máquina de estados e gera lista de chunks.

    Args:
        md_path: caminho para o arquivo .md gerado pelo Docling.
        preview: se True, processa apenas Língua Portuguesa e retorna no máximo 10 chunks.
    """
    estado = Estado()
    acumulador = AcumuladorTabela()
    chunks: list[dict] = []

    # Contexto da tabela corrente
    tabela_anos: list[str] = []          # anos únicos do bloco atual
    tabela_col_map: list[tuple] = []     # (ano, "OBJ"|"CON") por coluna
    aguardando_separator = False
    aguardando_obj_con = False
    dentro_tabela = False

    linhas = md_path.read_text(encoding="utf-8").splitlines()
    total = len(linhas)
    logger.info(f"Lendo {total} linhas de {md_path.name}")

    def _flush_acumulador() -> list[dict]:
        """Flush do acumulador e geração de chunks."""
        if acumulador.subeixo is None and not any(acumulador.obj_texto.values()):
            return []
        return acumulador.flush(estado.copia_contexto())

    for num_linha, linha in enumerate(linhas, start=1):

        # --- Heading: identifica seção ---
        if linha.startswith("##"):

            # Flush de tabela corrente antes de mudar de seção
            if dentro_tabela:
                novos = _flush_acumulador()
                chunks.extend(novos)
                dentro_tabela = False

            # Ignora headings de página (rodapé/cabeçalho repetitivo do Docling)
            if HEADINGS_IGNORAR.search(linha):
                continue

            # EIXOS TRANSVERSAIS
            if "EIXOS TRANSVERSAIS" in linha.upper():
                estado.eixos_transversais = _normalizar_eixos_transversais(linha)
                continue

            # EIXOS INTEGRADORES (inicia nova seção curricular)
            if "EIXOS INTEGRADORES" in linha.upper():
                novos = _flush_acumulador()
                chunks.extend(novos)
                acumulador = AcumuladorTabela()

                processar_heading_eixos_int(linha, estado)

                # Preview: se mudou de Língua Portuguesa, para
                if preview and estado.componente_curricular not in (None, "Língua Portuguesa"):
                    logger.info("Preview: fim da seção de Língua Portuguesa.")
                    break

                continue

            continue

        # --- Linha avulsa de ciclo/bloco (ex: "2º CICLO - 1º BLOCO") ---
        m_cb = RE_CICLO_BLOCO.match(linha.strip())
        if m_cb:
            estado.ciclo = f"{m_cb.group(1)}º Ciclo"
            estado.bloco = f"{m_cb.group(2)}º Bloco"
            continue

        # --- Linhas de tabela ---
        if linha.startswith("|"):

            # Cabeçalho de anos (primeira linha da tabela)
            if _is_header_tabela_anos(linha):
                tabela_anos, tabela_col_map = _extrair_header_tabela(linha)
                acumulador.inicializar_anos(tabela_anos)
                aguardando_separator = True
                aguardando_obj_con = False
                continue

            # Linha separadora ---
            if aguardando_separator and _is_separator_tabela(linha):
                aguardando_separator = False
                aguardando_obj_con = True
                continue

            # Linha OBJETIVOS/CONTEÚDOS (ignora — a informação já está no header de anos)
            if aguardando_obj_con and _is_header_obj_con(linha):
                aguardando_obj_con = False
                dentro_tabela = True
                continue

            # Linha de dados da tabela
            if dentro_tabela and tabela_col_map:
                cells = dividir_linha_tabela(linha)

                # Detecta novo subeixo na primeira célula OBJETIVOS não-vazia
                novo_subeixo = None
                for i, (ano, tipo) in enumerate(tabela_col_map):
                    if tipo == "OBJ" and i < len(cells) and cells[i].strip():
                        subeixo_celula, _ = detectar_subeixo(cells[i])
                        if subeixo_celula:
                            novo_subeixo = subeixo_celula
                            break

                if novo_subeixo and novo_subeixo != acumulador.subeixo:
                    # Flush do subeixo anterior
                    novos = _flush_acumulador()
                    chunks.extend(novos)
                    acumulador.subeixo = novo_subeixo

                # Adiciona linha ao acumulador
                acumulador.adicionar_linha(cells, tabela_col_map)
                continue

        else:
            # Linha não-tabela: termina um bloco de tabela se havia um em andamento
            if dentro_tabela and not linha.strip():
                # Linha em branco dentro de seção de tabela: aguarda próximo bloco
                aguardando_separator = False
                aguardando_obj_con = False
                continue

    # Flush final
    novos = _flush_acumulador()
    chunks.extend(novos)

    logger.info(f"Total de chunks gerados: {len(chunks)}")
    logger.info(f"  needs_review=True: {sum(1 for c in chunks if c.get('needs_review'))}")
    return chunks


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
        LOG_DIR / "parse_structure.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="5 MB",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converte Markdown do Currículo DF em JSONL estruturado"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Processa apenas Língua Portuguesa e imprime 5 chunks de exemplo (não salva em disco)",
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=MD_ENTRADA,
        help=f"Arquivo Markdown de entrada (padrão: {MD_ENTRADA.name})",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=JSONL_SAIDA,
        help=f"Arquivo JSONL de saída (padrão: {JSONL_SAIDA.name})",
    )
    args = parser.parse_args()

    configurar_logging()

    if not args.entrada.exists():
        logger.error(f"Arquivo de entrada não encontrado: {args.entrada}")
        sys.exit(1)

    chunks = parse_markdown(args.entrada, preview=args.preview)

    if args.preview:
        logger.info("=== PREVIEW: primeiros 5 chunks de Língua Portuguesa ===")
        for i, chunk in enumerate(chunks[:5], 1):
            print(f"\n--- Chunk {i} ---")
            print(json.dumps(chunk, ensure_ascii=False, indent=2))
        print(f"\nTotal de chunks gerados para LP: {len(chunks)}")
        return

    # Salva em disco
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    logger.success(f"Salvo: {args.saida} ({len(chunks)} registros)")


if __name__ == "__main__":
    main()
