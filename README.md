# Currículo em Movimento do DF – Dataset

> Dataset público e curado do **Currículo em Movimento do Distrito Federal – Ensino Fundamental** (Anos Iniciais e Anos Finais), 2ª edição, publicado pela Secretaria de Estado de Educação do Distrito Federal (SEEDF).

[![Licença: MIT](https://img.shields.io/badge/Licença-MIT-blue.svg)](LICENSE)
[![HuggingFace Dataset](https://img.shields.io/badge/🤗%20Dataset-walmeidadf/curriculo--ensinofundamental--df-yellow)](https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df)
[![HuggingFace Space](https://img.shields.io/badge/🤗%20Space-busca%20interativa-orange)](https://huggingface.co/spaces/walmeidadf/curriculo-ensinofundamental-df)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)

---

## Sobre

O **Currículo em Movimento do DF** orienta o trabalho pedagógico das escolas públicas do Distrito Federal do 1º ao 9º ano do Ensino Fundamental. O documento de 305 páginas contém tabelas de objetivos de aprendizagem e conteúdos organizados por:

- **Área de conhecimento** (Linguagens, Matemática, Ciências da Natureza, Ciências Humanas, Ensino Religioso)
- **Componente curricular** (Língua Portuguesa, Arte, Educação Física, Matemática etc.)
- **Ciclo e bloco** (2º Ciclo – Anos Iniciais; 3º Ciclo – Anos Finais)
- **Ano escolar** (1º ao 9º Ano)
- **Subeixo** (Oralidade, Leitura e escuta, Escrita/produção de texto, Análise linguística/semiótica etc. — apenas Anos Iniciais)

Este repositório contém o pipeline completo de extração (PDF → JSONL/Parquet), o dataset resultante publicado no HuggingFace Hub e uma interface de busca interativa via Gradio Space.

---

## Acesso rápido

| Recurso | Link |
|---------|------|
| Dataset (Parquet + JSONL) | [huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df](https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df) |
| Interface de busca | [huggingface.co/spaces/walmeidadf/curriculo-ensinofundamental-df](https://huggingface.co/spaces/walmeidadf/curriculo-ensinofundamental-df) |

---

## Estrutura do repositório

```
curriculo-ensinofundamental-df/
├── data/
│   ├── pdf/
│   │   └── Ensino Fundamental DF.pdf    # PDF original da SEEDF (305 pág., 12 MB)
│   ├── extracted/
│   │   └── curriculo_completo.md        # Markdown gerado pelo Docling (~2,1 MB)
│   ├── processed/
│   │   └── curriculo_completo.jsonl     # Dataset final (318 registros, 0 needs_review)
│   └── dataset_card.md                  # Fonte do README publicado no HuggingFace
├── pipeline/
│   ├── 01_extract_docling.py            # PDF → Markdown
│   ├── 02_parse_structure.py            # Markdown → JSONL (heurísticas)
│   ├── 03_enrich_llm.py                 # Enriquecimento via Groq/Llama 3.3 70B
│   ├── 04_validate.py                   # Validação de schema e cobertura
│   ├── 05_publish_hf.py                 # Upload dataset para HuggingFace Hub
│   └── 06_gradio_space.py               # Deploy do Gradio Space
├── space/
│   ├── app.py                           # Código do Gradio Space
│   ├── requirements.txt                 # Dependências do Space
│   └── README.md                        # Metadados do Space (YAML front matter)
├── schema/
│   └── curriculo_schema.json            # JSON Schema formal com exemplos
├── docs/
│   ├── architecture.md                  # Arquitetura do pipeline
│   ├── roadmap.md                       # Roadmap de desenvolvimento
│   └── decisions.md                     # Decisões de arquitetura (ADRs)
├── AGENTS.md                            # Guia para agentes IA
├── pyproject.toml                       # Dependências (gerenciadas com uv)
├── uv.lock                              # Lock file para reprodutibilidade exata
└── .env.example                         # Variáveis de ambiente necessárias
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
  "objetivos": ["item 1", "item 2"],
  "conteudos": ["item 1", "item 2"],
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

with open("data/processed/curriculo_completo.jsonl") as f:
    registros = [json.loads(linha) for linha in f]

# Filtrar por subeixo
oralidade = [r for r in registros if r["subeixo_componente"] == "Oralidade"]
```

---

## Executar o pipeline

O pipeline é reproduzível: a partir do PDF original, qualquer pessoa com as chaves de API consegue gerar o dataset do zero.

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

# Etapa 4 — Validação de schema e cobertura
python pipeline/04_validate.py

# Etapa 5 — Publicação do dataset (requer HF_TOKEN no .env)
python pipeline/05_publish_hf.py

# Etapa 6 — Deploy do Gradio Space (requer HF_TOKEN no .env)
python pipeline/06_gradio_space.py
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
