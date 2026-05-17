# Roadmap

## Fase 1 — Pipeline de extração (em andamento)

- [x] Análise dos PDFs e mapeamento da estrutura do documento
- [x] Schema JSON formal (`schema/curriculo_schema.json`)
- [x] Estrutura do repositório e ambiente uv
- [x] `01_extract_docling.py` — extração PDF → Markdown (2.762 linhas, 2,1 MB; ~2,5 min)
- [x] `02_parse_structure.py` — Markdown → JSONL (heurísticas) — `--preview` validado em LP (38 chunks, 2 needs_review)
  - [x] Teste de estresse: Língua Portuguesa (chunks aprovados)
  - [x] Processamento completo: 318 chunks, 10 componentes, 5,3% needs_review → `curriculo_parcial.jsonl`
- [x] `03_enrich_llm.py` — enriquecimento LLM (Groq/Llama 3.3 70B): 17/17 needs_review resolvidos → `curriculo_completo.jsonl` (0 needs_review)
- [x] `04_validate.py` — validação do schema e cobertura: 318/318 OK, todos os anos cobertos, 0 needs_review
- [x] `05_publish_hf.py` — publicação no HuggingFace Hub: Parquet + JSONL + dataset card publicados em `walmeidadf/curriculo-ensinofundamental-df`

## Fase 2 — Dataset público

- [x] Data card completo no HuggingFace (descrição, estrutura, licença, citação BibTeX)
- [x] JSONL + Parquet publicados em `walmeidadf/curriculo-ensinofundamental-df`
- [x] README do dataset com exemplos de uso (Python / datasets library)
- [ ] Notebook exploratório (`notebooks/01_exploratory.ipynb`)

## Fase 3 — Interface de busca (HuggingFace Space)

- [x] Gradio Space `walmeidadf/curriculo-ensinofundamental-df` — deploy concluído em https://huggingface.co/spaces/walmeidadf/curriculo-ensinofundamental-df
- [x] Busca por palavra-chave (objetivos + conteúdos) com atualização automática
- [x] Filtros: componente curricular, ciclo, bloco, ano escolar
- [x] Resultado em tabela com objetivos e conteúdos expandíveis (wrap)
- [x] Exportação da seleção em CSV (UTF-8 com BOM para Excel)
- [x] `pipeline/06_gradio_space.py` — script de deploy reutilizável
- [x] Arquivos do Space versionados em `space/` (app.py, requirements.txt, README.md)

## Notas de escopo

- O pipeline é reproduzível: qualquer pessoa que clone o repositório e tenha as chaves de API consegue gerar o dataset do zero.
- O PDF original permanece inalterado em `data/pdf/`.
- Revisão manual dos registros que o LLM não resolver fica fora do escopo automático — serão logados para curadoria humana.
