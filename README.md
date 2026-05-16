# Currículo em Movimento do DF – Dataset

> Dataset público e curado do **Currículo em Movimento do Distrito Federal – Ensino Fundamental** (Anos Iniciais e Anos Finais), 2ª edição, publicado pela Secretaria de Estado de Educação do Distrito Federal (SEEDF).

[![Licença: MIT](https://img.shields.io/badge/Licença-MIT-blue.svg)](LICENSE)
[![HuggingFace Dataset](https://img.shields.io/badge/🤗%20HuggingFace-Dataset-yellow)](https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)

---

## Sobre

O **Currículo em Movimento do DF** orienta o trabalho pedagógico das escolas públicas do Distrito Federal do 1º ao 9º ano do Ensino Fundamental. O documento de 305 páginas contém tabelas de objetivos de aprendizagem e conteúdos organizados por:

- **Área de conhecimento** (Linguagens, Matemática, Ciências da Natureza, Ciências Humanas, Ensino Religioso)
- **Componente curricular** (Língua Portuguesa, Arte, Educação Física, Matemática etc.)
- **Ciclo e bloco** (2º Ciclo – Anos Iniciais; 3º Ciclo – Anos Finais)
- **Ano escolar** (1º ao 9º Ano)
- **Subeixo** (Oralidade, Leitura e escuta, Escrita/produção de texto, Análise linguística/semiótica etc. — apenas Anos Iniciais)

Este repositório contém o pipeline de extração (PDF → JSONL/Parquet) e o dataset resultante, disponível também no [HuggingFace Hub](https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df).

---

## Estrutura do repositório

```
curriculo-ensinofundamental-df/
├── data/
│   ├── pdf/          # PDFs originais da SEEDF (não modificados)
│   ├── extracted/    # Markdown gerado pelo Docling
│   └── processed/    # JSONL e Parquet finais
├── pipeline/
│   ├── 01_extract_docling.py   # PDF → Markdown
│   ├── 02_parse_structure.py   # Markdown → JSON (heurísticas)
│   ├── 03_enrich_llm.py        # Enriquecimento via Groq/Llama
│   ├── 04_validate.py          # Validação de schema
│   └── 05_publish_hf.py        # Upload para HuggingFace
├── schema/
│   └── curriculo_schema.json   # JSON Schema formal com exemplos
├── docs/
│   ├── architecture.md         # Arquitetura do pipeline
│   ├── roadmap.md              # Roadmap de desenvolvimento
│   └── decisions.md            # Decisões de arquitetura (ADRs)
├── notebooks/
│   └── 01_exploratory.ipynb    # Análise exploratória
├── AGENTS.md                   # Guia para agentes IA
├── pyproject.toml              # Dependências (gerenciadas com uv)
└── .env.example                # Variáveis de ambiente necessárias
```

---

## Schema de cada registro

Cada linha do dataset JSONL segue este schema (resumido):

```json
{
  "id": "uuid4",
  "tipo_registro": "curriculo | apresentacao | referencia",
  "area_conhecimento": "Linguagens",
  "componente_curricular": "Língua Portuguesa",
  "sub_componente": null,
  "subeixo_componente": "Oralidade",
  "etapa": "Ensino Fundamental",
  "ciclo": "2º Ciclo",
  "bloco": "1º Bloco",
  "ano_escolar": "1º Ano",
  "eixos_transversais": ["Educação para a Diversidade", "..."],
  "eixos_integradores": ["Alfabetização", "Letramentos", "Ludicidade"],
  "objetivos": ["• objetivo 1", "• objetivo 2"],
  "conteudos": ["• conteúdo 1", "• conteúdo 2"],
  "texto_livre": null,
  "paginas_pdf": [23, 24],
  "fonte": "Currículo em Movimento do Distrito Federal – Ensino Fundamental, 2ª edição, SEEDF"
}
```

O campo `sub_componente` é usado exclusivamente para Arte (`"Artes Visuais"`, `"Música"`, `"Teatro"`, `"Dança"`).

Schema completo com validações e exemplos em [`schema/curriculo_schema.json`](schema/curriculo_schema.json).

---

## Instalação

Requer **Python 3.11+** e [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone git@github.com:walmeidadf/curriculo-ensinofundamental-df.git
cd curriculo-ensinofundamental-df

# Instalar dependências e criar ambiente virtual
uv sync

# (opcional) incluir dependências de desenvolvimento (Jupyter)
uv sync --group dev

# Copiar e preencher variáveis de ambiente
cp .env.example .env
# edite .env com suas chaves de API
```

---

## Uso do dataset

### Via HuggingFace datasets

```python
from datasets import load_dataset

ds = load_dataset("walmeidadf/curriculo-ensinofundamental-df")

# Filtrar por ano escolar
primeiro_ano = ds["train"].filter(lambda r: r["ano_escolar"] == "1º Ano")

# Filtrar objetivos de Matemática
matematica = ds["train"].filter(
    lambda r: r["componente_curricular"] == "Matemática"
               and r["tipo_registro"] == "curriculo"
)
```

### Via arquivo JSONL local

```python
import json

with open("data/processed/curriculo_final.jsonl") as f:
    registros = [json.loads(linha) for linha in f]

# Filtrar por subeixo
oralidade = [r for r in registros if r["subeixo_componente"] == "Oralidade"]
```

---

## Executar o pipeline

```bash
# Ativar ambiente
source .venv/bin/activate

# Etapa 1 — Extração do PDF (requer ~2 GB de modelos Docling na primeira execução)
python pipeline/01_extract_docling.py

# Etapa 2 — Parsing estruturado (modo teste: só Língua Portuguesa)
python pipeline/02_parse_structure.py --componente "Língua Portuguesa" --preview

# Etapa 2 — Documento completo
python pipeline/02_parse_structure.py

# Etapa 3 — Enriquecimento LLM (requer GROQ_API_KEY no .env)
python pipeline/03_enrich_llm.py

# Etapa 4 — Validação
python pipeline/04_validate.py

# Etapa 5 — Publicação (requer HF_TOKEN no .env)
python pipeline/05_publish_hf.py
```

---

## Fonte e licença

- **Fonte do documento**: [Currículo em Movimento do Distrito Federal – Ensino Fundamental](http://www.educacao.df.gov.br/curriculo-em-movimento-da-educacao-basica-2/), SEEDF, 2ª edição.
- **Licença do pipeline**: [MIT](LICENSE)
- **Licença do dataset**: O conteúdo curricular é de domínio público (documento oficial do Governo do Distrito Federal). O dataset estruturado é licenciado sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## Citação

```bibtex
@dataset{almeida2026curriculodf,
  author    = {Almeida, Wesley},
  title     = {Currículo em Movimento do Distrito Federal – Ensino Fundamental: Dataset Estruturado},
  year      = {2026},
  publisher = {HuggingFace},
  url       = {https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df},
  note      = {Baseado em: SEEDF. Currículo em Movimento do Distrito Federal – Ensino Fundamental. 2ª ed. Brasília: SEEDF, 2018.}
}
```

---

## Contribuição

Issues e PRs são bem-vindos. Para dúvidas sobre o conteúdo pedagógico, consulte o documento original da SEEDF.
