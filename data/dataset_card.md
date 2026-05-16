---
language:
  - pt
license: mit
pretty_name: "Currículo em Movimento do DF – Ensino Fundamental"
tags:
  - education
  - curriculum
  - brazil
  - distrito-federal
  - nlp
  - structured
  - portuguese
task_categories:
  - text-retrieval
  - text-classification
size_categories:
  - n<1K
dataset_info:
  features:
    - name: id
      dtype: string
    - name: tipo_registro
      dtype: string
    - name: etapa
      dtype: string
    - name: area_conhecimento
      dtype: string
    - name: componente_curricular
      dtype: string
    - name: sub_componente
      dtype: string
    - name: subeixo_componente
      dtype: string
    - name: ciclo
      dtype: string
    - name: bloco
      dtype: string
    - name: ano_escolar
      dtype: string
    - name: eixos_transversais
      sequence: string
    - name: eixos_integradores
      sequence: string
    - name: objetivos
      sequence: string
    - name: conteudos
      sequence: string
    - name: texto_livre
      dtype: string
    - name: needs_review
      dtype: bool
    - name: paginas_pdf
      sequence: int32
    - name: fonte
      dtype: string
  splits:
    - name: train
      num_examples: 318
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train-*.parquet
---

# Currículo em Movimento do DF – Ensino Fundamental

Dataset estruturado do **Currículo em Movimento do Distrito Federal – Ensino Fundamental** (2ª edição, SEEDF), extraído automaticamente de um PDF de 305 páginas e publicado como recurso aberto para professoras, pesquisadores e desenvolvedores de NLP/EdTech.

## Sobre o documento fonte

O *Currículo em Movimento do DF* é o documento oficial que orienta o trabalho pedagógico das escolas públicas do Distrito Federal do 1º ao 9º ano do Ensino Fundamental. Publicado pela **Secretaria de Estado de Educação do Distrito Federal (SEEDF)**, ele organiza objetivos de aprendizagem e conteúdos por:

- **Área de conhecimento** — Linguagens, Matemática, Ciências da Natureza, Ciências Humanas, Ensino Religioso
- **Componente curricular** — Língua Portuguesa, Arte (Artes Visuais, Música, Teatro, Dança), Educação Física, Matemática, Ciências da Natureza, História, Geografia, Língua Estrangeira, Ensino Religioso
- **Ciclo e bloco** — 2º Ciclo (Anos Iniciais, 1º–5º ano) e 3º Ciclo (Anos Finais, 6º–9º ano)
- **Subeixo** — Oralidade, Leitura e escuta, Escrita/produção de texto, Análise linguística/semiótica, Números, Geometria etc. (presentes no 2º Ciclo)

## Estatísticas do dataset

| Indicador | Valor |
|-----------|-------|
| Total de registros | 318 |
| Componentes curriculares | 10 |
| Anos escolares cobertos | 1º ao 9º Ano |
| 2º Ciclo (Anos Iniciais) | 153 registros |
| 3º Ciclo (Anos Finais) | 165 registros |
| Cobertura | 100% dos anos em todos os componentes |
| `needs_review` no dataset final | 0 |

## Estrutura dos dados

Cada registro representa uma linha da tabela curricular — combinação única de componente, ciclo, bloco, ano escolar e subeixo.

### Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string (UUID) | Identificador único imutável do registro |
| `tipo_registro` | string | `"curriculo"` neste dataset |
| `etapa` | string | Fixo: `"Ensino Fundamental"` |
| `area_conhecimento` | string | Ex: `"Linguagens"`, `"Matemática"` |
| `componente_curricular` | string | Ex: `"Língua Portuguesa"`, `"Arte"` |
| `sub_componente` | string \| `""` | Apenas para Arte: `"Artes Visuais"`, `"Música"`, `"Teatro"`, `"Dança"` |
| `subeixo_componente` | string \| `""` | Subeixo do 2º Ciclo; vazio no 3º Ciclo |
| `ciclo` | string | `"2º Ciclo"` (Anos Iniciais) ou `"3º Ciclo"` (Anos Finais) |
| `bloco` | string | `"1º Bloco"` ou `"2º Bloco"` |
| `ano_escolar` | string | Ex: `"1º Ano"`, `"6º Ano"` |
| `eixos_transversais` | list[string] | Os três eixos transversais do documento |
| `eixos_integradores` | list[string] | Eixos integradores do ciclo (2 ou 3 itens) |
| `objetivos` | list[string] | Objetivos de aprendizagem (coluna OBJETIVOS da tabela) |
| `conteudos` | list[string] | Conteúdos (coluna CONTEÚDOS da tabela) |
| `texto_livre` | string \| `""` | Vazio para registros do tipo `curriculo` |
| `needs_review` | bool | Sempre `false` neste dataset público |
| `paginas_pdf` | list[int] | Página(s) do PDF; `[0]` é placeholder (extração Markdown não preserva paginação) |
| `fonte` | string | Citação completa do documento fonte |

### Exemplo de registro

```json
{
  "id": "97cd9788-abdf-4787-8146-985b036641f1",
  "tipo_registro": "curriculo",
  "etapa": "Ensino Fundamental",
  "area_conhecimento": "Linguagens",
  "componente_curricular": "Arte",
  "sub_componente": "Artes Visuais",
  "subeixo_componente": "",
  "ciclo": "2º Ciclo",
  "bloco": "1º Bloco",
  "ano_escolar": "1º Ano",
  "eixos_transversais": [
    "Educação para a Diversidade",
    "Cidadania e Educação em e para os Direitos Humanos",
    "Educação para a Sustentabilidade"
  ],
  "eixos_integradores": ["Alfabetização", "Letramentos", "Ludicidade"],
  "objetivos": [
    "Explorar a imaginação, a criatividade e a expressividade a partir de temas e observação do meio ambiente.",
    "Conhecer diferentes cores e experimentar materiais e suportes diversos da natureza."
  ],
  "conteudos": [
    "Desenho, pintura, colagem, escultura, modelagem e construções a partir de vivências relacionadas às questões ambientais",
    "Cores e formas presentes na fauna e na flora do Cerrado"
  ],
  "texto_livre": "",
  "needs_review": false,
  "paginas_pdf": [0],
  "fonte": "Currículo em Movimento do Distrito Federal – Ensino Fundamental, 2ª edição, SEEDF"
}
```

## Como usar

```python
from datasets import load_dataset

ds = load_dataset("walmeidadf/curriculo-ensinofundamental-df")
df = ds["train"].to_pandas()

# Filtrar por componente e ano
lp_1ano = df[
    (df["componente_curricular"] == "Língua Portuguesa") &
    (df["ano_escolar"] == "1º Ano")
]

# Ver objetivos de um registro
for obj in lp_1ano.iloc[0]["objetivos"]:
    print(f"• {obj}")
```

## Pipeline de extração

O dataset foi gerado pelo pipeline disponível no repositório GitHub:

1. **01_extract_docling.py** — PDF → Markdown via [Docling](https://github.com/DS4SD/docling) (sem OCR, com estrutura de tabelas)
2. **02_parse_structure.py** — Markdown → JSONL com máquina de estados (heurísticas de heading, tabela e subeixo)
3. **03_enrich_llm.py** — Enriquecimento dos registros ambíguos via Groq / Llama 3.3 70B
4. **04_validate.py** — Validação contra JSON Schema formal
5. **05_publish_hf.py** — Conversão para Parquet e publicação no HF Hub

O pipeline é reproduzível: qualquer pessoa com as chaves de API pode gerar o dataset do zero a partir do PDF original.

## Limitações conhecidas

- **`paginas_pdf: [0]`** — O export Markdown do Docling não preserva numeração de página. O campo é um placeholder e não deve ser usado para localização no PDF.
- **Registros enriquecidos por LLM** — 17 dos 318 registros (5,3%) tinham objetivos ou conteúdos ausentes após a extração heurística e foram completados por Llama 3.3 70B. Esses registros são fieis ao estilo do documento mas podem diferir pontualmente do texto original.
- **Língua Estrangeira** — O documento usa "Língua Estrangeira" e "Língua Estrangeira 2" sem especificar idiomas. A extração preserva essa nomenclatura.

## Licença e citação

O dataset está licenciado sob **MIT**. O documento fonte é de domínio público (produção da SEEDF/GDF).

Se você usar este dataset em pesquisa, por favor cite:

```bibtex
@dataset{almeida2026curriculo,
  author    = {Almeida, Wesley},
  title     = {Currículo em Movimento do {DF} -- Ensino Fundamental},
  year      = {2026},
  publisher = {HuggingFace},
  url       = {https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df},
  note      = {Dataset estruturado extraído do Currículo em Movimento do Distrito Federal, 2ª edição, SEEDF}
}
```

**Documento fonte:**
> Secretaria de Estado de Educação do Distrito Federal (SEEDF). *Currículo em Movimento do Distrito Federal – Ensino Fundamental*. 2ª edição. Brasília: SEEDF, 2018.
