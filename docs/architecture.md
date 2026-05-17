# Arquitetura do Pipeline

## Visão geral

```
data/pdf/                          data/extracted/               data/processed/
Ensino Fundamental DF.pdf  ──►  curriculo_completo.md  ──►  curriculo_completo.jsonl
                                                                      │
                                                          (needs_review=True → Groq)
                                                                      │
                                                               Validação (04)
                                                                      │
                                                         HuggingFace Hub (05)
                                                         ├── dataset.jsonl
                                                         └── dataset.parquet
                                                                      │
                                                         Gradio Space (06)
                                                         └── busca interativa
```

## Scripts do pipeline

| Script | Entrada | Saída | Tecnologia |
|--------|---------|-------|------------|
| `pipeline/01_extract_docling.py` | PDF original (12 MB) | `data/extracted/curriculo_completo.md` | Docling |
| `pipeline/02_parse_structure.py` | Markdown extraído | `data/processed/curriculo_completo.jsonl` | Python (regex + state machine) |
| `pipeline/03_enrich_llm.py` | Registros com `needs_review=True` | Registros corrigidos no JSONL | Groq / Llama 3.3 70B |
| `pipeline/04_validate.py` | JSONL completo | Relatório de cobertura + JSONL limpo | jsonschema |
| `pipeline/05_publish_hf.py` | JSONL validado | Dataset no HuggingFace Hub | datasets + huggingface_hub |
| `pipeline/06_gradio_space.py` | `space/` (app.py, requirements.txt, README.md) | Gradio Space no HuggingFace | huggingface_hub |

## Estratégia de extração em dois estágios

### Estágio 1 — Heurísticas Python puras (`02_parse_structure.py`)
Meta: cobrir > 80% dos registros de forma determinística.

1. **Detecção de contexto** — máquina de estados que rastreia:
   - Área de conhecimento atual
   - Componente curricular (e sub-componente para Arte)
   - Ciclo e bloco (deduzidos do header da tabela)
   - Subeixo atual (somente 2º Ciclo)
   - Eixos transversais e integradores (herdados do header)

2. **Identificação de padrão de tabela**:
   - **Padrão A (2º Ciclo)** — 3 colunas de anos (1º Bloco) ou 2 (2º Bloco); subeixos em negrito dentro das células
   - **Padrão B (3º Ciclo)** — 2 colunas de anos; um único cabeçalho de subeixo combinado; `subeixo_componente = null`

3. **Tratamento de sub-bullets** — itens com marcador `o` são concatenados ao item-pai como texto adicional, não como entrada separada no array.

4. **Células vazias** — chunk não é gerado se a célula de objetivos ou conteúdos está vazia.

5. **Flag `needs_review`** — ativada quando:
   - Alinhamento de colunas é incerto após quebra de página
   - Subeixo não identificado explicitamente
   - Número de colunas não bate com o padrão esperado

### Estágio 2 — LLM via Groq (`03_enrich_llm.py`)
Processa apenas registros com `needs_review=True`.

- Envia o trecho de Markdown bruto + contexto (área, componente, ciclo, bloco, ano)
- Recebe JSON estruturado conforme o schema
- Valida o output contra `schema/curriculo_schema.json` antes de aceitar
- Casos que o LLM não resolve são logados em `logs/manual_review.jsonl`

## Estrutura de dados

Ver [`schema/curriculo_schema.json`](../schema/curriculo_schema.json) para o schema formal e exemplos completos.

### Hierarquia do documento

```
Etapa: Ensino Fundamental
└── Área de Conhecimento
    └── Componente Curricular
        └── [Sub-componente]   ← somente Arte (Artes Visuais, Música, Teatro, Dança)
            └── Ciclo (2º ou 3º)
                └── Bloco (1º ou 2º)
                    └── Ano Escolar (1º–9º)
                        └── Subeixo  ← somente 2º Ciclo
                            └── Objetivos[] + Conteúdos[]
```

### Dois padrões de tabela

**Padrão A – 2º Ciclo (Anos Iniciais)**
```
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│           1º ANO             │           2º ANO             │           3º ANO             │
│  OBJETIVOS    │  CONTEÚDOS   │  OBJETIVOS    │  CONTEÚDOS   │  OBJETIVOS    │  CONTEÚDOS   │
├───────────────┼──────────────┼───────────────┼──────────────┼───────────────┼──────────────┤
│ **Oralidade** │**Oralidade** │ **Oralidade** │**Oralidade** │ **Oralidade** │**Oralidade** │
│ • item        │ • item       │ • item        │ • item       │ • item        │ • item       │
│ (continua...) │              │               │              │               │              │
├───────────────┼──────────────┼───────────────┼──────────────┼───────────────┼──────────────┤
│ **Leitura...**│**Leitura...* │ ...           │ ...          │ ...           │ ...          │
└───────────────┴──────────────┴───────────────┴──────────────┴───────────────┴──────────────┘
```
- 1º Bloco: 3 anos (6 colunas); 2º Bloco: 2 anos (4 colunas)
- Subeixos em negrito como cabeçalho de seção dentro de cada célula
- Tabelas continuam por múltiplas páginas sem repetir o label do subeixo

**Padrão B – 3º Ciclo (Anos Finais)**
```
┌───────────────────────────────────────┬───────────────────────────────────────┐
│              6º ANO                   │              7º ANO                   │
│  OBJETIVOS          │  CONTEÚDOS      │  OBJETIVOS          │  CONTEÚDOS      │
├─────────────────────┼─────────────────┼─────────────────────┼─────────────────┤
│ Oralidade, leitura/ │ • item          │ Oralidade, leitura/ │ • item          │
│ escuta, escrita/    │ • item          │ escuta, escrita/    │ • item          │
│ produção textual e  │                 │ produção textual e  │                 │
│ análise linguíst... │                 │ análise linguíst... │                 │
└─────────────────────┴─────────────────┴─────────────────────┴─────────────────┘
```
- Sempre 2 anos (4 colunas)
- `subeixo_componente = null`

## Ambiente

Gerenciado com **uv**. Ver [README.md](../README.md#instalação) para setup.
