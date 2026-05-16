# Decisões de Arquitetura (ADRs)

## ADR-001 — Docling como extrator de PDF

**Data:** 2026-05-16  
**Status:** Aceito

**Contexto:** O documento tem 305 páginas com tabelas multi-coluna que cruzam páginas, texto corrido e referências bibliográficas. Precisamos de um extrator que preserve a estrutura de tabelas.

**Decisão:** Usar [Docling](https://github.com/DS4SD/docling) (IBM) para converter PDF → Markdown. O Docling usa modelos de layout para reconstruir tabelas mesmo quando cruzam páginas.

**Alternativas descartadas:**
- `pdfplumber` / `pymupdf` — bom para texto corrido, mas frágil para tabelas multi-coluna que cruzam páginas
- `camelot` — bom para tabelas simples, mas não lida bem com células mescladas e layout de múltiplas colunas de anos

**Consequências:** Dependência de modelo de ML (~1–2 GB de download na primeira execução do Docling). O Markdown gerado pode ter imperfeições nas quebras de página que o parser precisa tratar.

---

## ADR-002 — Extração em dois estágios (heurística + LLM)

**Data:** 2026-05-16  
**Status:** Aceito

**Contexto:** Aplicar LLM a todo o documento seria caro e lento. Mas heurísticas puras podem falhar em casos ambíguos (células assimétricas, quebras de página no meio de subeixo).

**Decisão:** Abordagem híbrida:
1. Estágio 1: heurísticas Python puras (meta: > 80% dos registros)
2. Estágio 2: LLM via Groq free tier somente para registros `needs_review=True`

**Consequências:** O estágio 2 depende de uma chave de API externa. Registros que o LLM não resolver ficam em `logs/manual_review.jsonl` para curadoria humana.

---

## ADR-003 — Groq / Llama 3.3 70B para enriquecimento

**Data:** 2026-05-16  
**Status:** Aceito

**Contexto:** Precisamos de um LLM capaz de seguir instruções estruturadas (output JSON) com bom entendimento de português.

**Decisão:** Usar `llama-3.3-70b-versatile` via Groq API (free tier). O Groq oferece inferência rápida e o Llama 3.3 70B tem boa performance em português.

**Alternativas:**
- Claude via Anthropic API — mais preciso, mas com custo e sem free tier para este volume
- OpenAI GPT-4o — similar, com custo
- Ollama local — sem custo mas requer hardware adequado

---

## ADR-004 — `sub_componente` como campo separado para Arte

**Data:** 2026-05-16  
**Status:** Aceito

**Contexto:** Arte se divide em Artes Visuais, Música, Teatro e Dança, cada uma com tabela própria. O campo `subeixo_componente` é reservado para subeixos de conteúdo (Oralidade, Geometria etc.), não para sub-divisões do componente.

**Decisão:** Adicionar campo `sub_componente: string | null` ao schema. Para Arte: `componente_curricular = "Arte"`, `sub_componente = "Artes Visuais"`. Para todos os demais componentes: `sub_componente = null`.

**Consequências:** Permite filtrar registros por `componente_curricular = "Arte"` (todos os sub-componentes) ou por `sub_componente = "Artes Visuais"` especificamente.

---

## ADR-005 — Dados de extração commitados no repositório

**Data:** 2026-05-16  
**Status:** Aceito

**Contexto:** Os dados extraídos (`data/extracted/`, `data/processed/`) são artefatos reproduzíveis pelo pipeline, mas commitá-los facilita o uso imediato sem rodar o pipeline completo.

**Decisão:** Rastrear `data/extracted/` e `data/processed/` no git. O `.gitignore` não exclui essas pastas. O dataset final também vai para o HuggingFace Hub.

**Consequências:** O repositório pode crescer com o tempo. Se os arquivos Parquet ficarem grandes (> 50 MB), avaliar uso de Git LFS.

---

## ADR-006 — uv para gerenciamento do ambiente Python

**Data:** 2026-05-16  
**Status:** Aceito

**Contexto:** Precisamos de um ambiente reproduzível e rápido de instalar.

**Decisão:** Usar [uv](https://github.com/astral-sh/uv) com `pyproject.toml` como fonte de verdade das dependências. O arquivo `uv.lock` (gerado por `uv sync`) é commitado para garantir reprodutibilidade exata.

**Setup:**
```bash
uv sync          # cria .venv e instala dependências
uv sync --group dev   # inclui jupyter/ipykernel
source .venv/bin/activate
```
