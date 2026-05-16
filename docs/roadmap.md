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
- [ ] `04_validate.py` — validação do schema e cobertura
- [ ] `05_publish_hf.py` — publicação no HuggingFace Hub

## Fase 2 — Dataset público

- [ ] Data card completo no HuggingFace (descrição, estrutura, licença)
- [ ] JSONL + Parquet publicados em `walmeidadf/curriculo-ensinofundamental-df`
- [ ] README do dataset com exemplos de uso (Python / datasets library)
- [ ] Notebook exploratório (`notebooks/01_exploratory.ipynb`)

## Fase 3 — Interface de busca (HuggingFace Space)

- [ ] Gradio Space `walmeidadf/curriculo-df-busca`
- [ ] Busca por componente, ciclo, bloco, ano e palavra-chave
- [ ] Filtro por tipo de registro (objetivos / conteúdos)
- [ ] Exportação de seleção em CSV

## Notas de escopo

- O pipeline é reproduzível: qualquer pessoa que clone o repositório e tenha as chaves de API consegue gerar o dataset do zero.
- O PDF original permanece inalterado em `data/pdf/`.
- Revisão manual dos registros que o LLM não resolver fica fora do escopo automático — serão logados para curadoria humana.
