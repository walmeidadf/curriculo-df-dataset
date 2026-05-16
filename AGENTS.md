# AGENTS.md — Guia para Agentes IA

Este arquivo é a fonte primária de contexto para qualquer agente IA (Claude Code ou outro) que trabalhe neste repositório. Leia-o antes de qualquer ação.

---

## Contexto do projeto

**O que é:** Pipeline de extração e dataset público do *Currículo em Movimento do Distrito Federal – Ensino Fundamental* (2ª ed., SEEDF). O objetivo é transformar um PDF de 305 páginas em um dataset estruturado (JSONL + Parquet) publicado no HuggingFace Hub, e uma interface de busca via Gradio Space.

**Público-alvo do dataset:** professoras e pesquisadores da educação pública do DF e comunidade de desenvolvedores de NLP/EdTech no HuggingFace.

**Repositório git:** `git@github.com:walmeidadf/curriculo-df-dataset.git`  
**Dataset HF:** `walmeidadf/curriculo-em-movimento-df`

---

## Estado atual do projeto

Consulte [`docs/roadmap.md`](docs/roadmap.md) para o estado atualizado de cada etapa.

Resumo rápido (atualizar aqui a cada etapa concluída):

| Etapa | Status |
|-------|--------|
| Análise dos PDFs e schema | ✅ Concluído |
| Estrutura do repositório e ambiente | ✅ Concluído |
| `01_extract_docling.py` | ⏳ Próxima etapa |
| `02_parse_structure.py` | ⏳ Pendente |
| `03_enrich_llm.py` | ⏳ Pendente |
| `04_validate.py` | ⏳ Pendente |
| `05_publish_hf.py` | ⏳ Pendente |

---

## Arquivos críticos para entender antes de agir

| Arquivo | Por que ler |
|---------|-------------|
| `schema/curriculo_schema.json` | Schema formal com validações `if/then` e exemplos reais |
| `docs/architecture.md` | Diagrama do pipeline, dois padrões de tabela (A e B), estratégia de extração |
| `docs/decisions.md` | ADRs — decisões já tomadas (não reabrir sem motivo) |
| `docs/roadmap.md` | O que está feito e o que falta |
| `data/pdf/port-ens-fund.pdf` | Amostra dos PDFs: Língua Portuguesa completa (páginas 17–56) |
| `data/pdf/pagina_exemplo_curriculo.pdf` | Página de Arte: Artes Visuais (Padrão B, 3º Ciclo) |

---

## Regras de trabalho

1. **Leia os PDFs antes de escrever qualquer parser.** A estrutura do Markdown que o Docling gera determina as heurísticas. Não escreva regex com base em suposições.

2. **Não altere o schema sem consultar o usuário.** O schema em `schema/curriculo_schema.json` foi validado contra os PDFs reais. Mudanças têm impacto no pipeline inteiro.

3. **Teste antes de processar o documento todo.** Para o script `02_parse_structure.py`, rode primeiro só em Língua Portuguesa (componente mais complexo) e mostre 3–5 chunks de exemplo para aprovação.

4. **`needs_review = false` no dataset final.** O campo é de controle interno do pipeline. Nunca publique registros com `needs_review = true`.

5. **Variáveis de ambiente em `.env`, nunca no código.** `GROQ_API_KEY` e `HF_TOKEN` ficam no `.env` (que está no `.gitignore`).

6. **Logging estruturado em cada script.** Use `loguru`. Erros de extração vão para `logs/manual_review.jsonl`, não para stdout.

7. **Comentários em português.** O público do código são desenvolvedores brasileiros.

---

## Convenção de commits

Formato: `tipo(escopo): descrição curta em português`

| Tipo | Uso |
|------|-----|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `data` | Adição ou atualização de dados extraídos |
| `docs` | Documentação |
| `refactor` | Refatoração sem mudança de comportamento |
| `test` | Testes |
| `chore` | Configuração, dependências |

Exemplos:
```
feat(pipeline): adiciona 01_extract_docling com suporte a multi-página
data(extracted): adiciona markdown extraído do PDF completo
fix(parser): corrige alinhamento de colunas após quebra de página
```

---

## Prática de atualização do repositório

**Ao concluir com sucesso qualquer etapa do pipeline:**

```bash
# 1. Verificar o que mudou
git status
git diff --stat

# 2. Adicionar arquivos relevantes
git add pipeline/0X_nome_do_script.py
git add data/extracted/   # se gerou Markdown
git add data/processed/   # se gerou JSONL/Parquet
git add docs/roadmap.md   # atualizar o status da etapa concluída

# 3. Commit com mensagem descritiva
git commit -m "feat(pipeline): 0X_nome — descrição do que foi feito e cobertura (ex: 94% sem needs_review)"

# 4. Push
git push origin main
```

**Antes de fazer push**, certifique-se de que:
- [ ] Nenhum arquivo `.env` foi adicionado
- [ ] Nenhum token ou chave de API está no código
- [ ] O script roda do zero em um clone limpo (testado com `uv sync`)
- [ ] O `docs/roadmap.md` está atualizado com o status da etapa

---

## Ambiente

```bash
# Setup inicial
uv sync              # instala dependências e cria .venv
uv sync --group dev  # adiciona Jupyter

# Ativar ambiente
source .venv/bin/activate

# Rodar um script
python pipeline/01_extract_docling.py
```

---

## Observações sobre o documento

- **PDF principal:** `data/pdf/Ensino Fundamental DF.pdf` (12 MB, 305 páginas) — use este no pipeline.
- **PDFs menores em `data/pdf/`:** foram criados para análise prévia — `port-ens-fund.pdf` (LP completa), `pagina_exemplo_curriculo.pdf` (Arte, 1 página).
- **Dois padrões de tabela** são descritos em detalhe em `docs/architecture.md`.
- **Sub-bullets** com marcador `o` existem na seção de Análise linguística/semiótica do 2º Ciclo — devem ser concatenados ao item-pai.
- **Eixos Transversais** aparecem com variações de grafia no documento — normalizar para a forma canônica do schema.
