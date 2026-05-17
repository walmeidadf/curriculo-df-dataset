"""
app.py — Gradio Space: Currículo em Movimento do DF – Busca
Interface de busca para o dataset walmeidadf/curriculo-ensinofundamental-df
"""

import gradio as gr
import pandas as pd
from datasets import load_dataset


def carregar_dados() -> pd.DataFrame:
    """Carrega e filtra apenas os registros de currículo (linhas de tabela)."""
    ds = load_dataset("walmeidadf/curriculo-ensinofundamental-df", split="train")
    df = ds.to_pandas()
    df = df[df["tipo_registro"] == "curriculo"].copy()
    df = df.reset_index(drop=True)
    return df


# Carregado uma vez na inicialização do Space
df_base = carregar_dados()

# Opções dos dropdowns — ordenadas logicamente
COMPONENTES = ["Todos"] + sorted(df_base["componente_curricular"].dropna().unique().tolist())
CICLOS = ["Todos"] + sorted(df_base["ciclo"].dropna().unique().tolist())
BLOCOS = ["Todos"] + sorted(df_base["bloco"].dropna().unique().tolist())
ANOS = ["Todos"] + sorted(
    df_base["ano_escolar"].dropna().unique().tolist(),
    key=lambda x: int(x.split("º")[0]),
)


def formatar_lista(items) -> str:
    """Converte lista de objetivos/conteúdos em texto com bullets."""
    if items is None:
        return ""
    if hasattr(items, "__iter__") and not isinstance(items, str):
        return "\n".join(f"• {item}" for item in items if item)
    return str(items)


def buscar(
    palavra_chave: str,
    componente: str,
    ciclo: str,
    bloco: str,
    ano: str,
) -> tuple[pd.DataFrame, str]:
    """Filtra o dataset e retorna tabela formatada + contagem de resultados."""
    df = df_base.copy()

    if componente != "Todos":
        df = df[df["componente_curricular"] == componente]
    if ciclo != "Todos":
        df = df[df["ciclo"] == ciclo]
    if bloco != "Todos":
        df = df[df["bloco"] == bloco]
    if ano != "Todos":
        df = df[df["ano_escolar"] == ano]

    termo = palavra_chave.strip().lower() if palavra_chave else ""
    if termo:
        def contem(lst):
            if not hasattr(lst, "__iter__") or isinstance(lst, str):
                return False
            return any(termo in (item or "").lower() for item in lst)

        mask = df["objetivos"].apply(contem) | df["conteudos"].apply(contem)
        df = df[mask]

    resultado = pd.DataFrame({
        "Componente": df["componente_curricular"].fillna("—"),
        "Sub-componente": df["sub_componente"].fillna("—"),
        "Ciclo": df["ciclo"].fillna("—"),
        "Bloco": df["bloco"].fillna("—"),
        "Ano": df["ano_escolar"].fillna("—"),
        "Subeixo": df["subeixo_componente"].fillna("—"),
        "Objetivos": df["objetivos"].apply(formatar_lista),
        "Conteúdos": df["conteudos"].apply(formatar_lista),
    })

    contagem = f"**{len(resultado)} registro(s) encontrado(s)**"
    return resultado, contagem


def exportar_csv(
    palavra_chave: str,
    componente: str,
    ciclo: str,
    bloco: str,
    ano: str,
) -> str:
    """Gera CSV com a seleção atual e retorna o caminho para download."""
    resultado, _ = buscar(palavra_chave, componente, ciclo, bloco, ano)
    caminho = "/tmp/curriculo_busca.csv"
    resultado.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho


# Carrega exibição inicial com todos os registros
df_inicial, contagem_inicial = buscar("", "Todos", "Todos", "Todos", "Todos")

with gr.Blocks(title="Currículo em Movimento DF – Busca", theme=gr.themes.Soft()) as app:
    gr.Markdown("""
# 📚 Currículo em Movimento do DF — Busca
**Ensino Fundamental · SEEDF · 2ª edição**

Pesquise objetivos e conteúdos do currículo da rede pública do Distrito Federal.
Fonte: [walmeidadf/curriculo-ensinofundamental-df](https://huggingface.co/datasets/walmeidadf/curriculo-ensinofundamental-df)
""")

    with gr.Row():
        txt_busca = gr.Textbox(
            label="Busca por palavra-chave",
            placeholder="Ex: frações, oralidade, geometria, gêneros textuais...",
            scale=3,
        )
        dd_componente = gr.Dropdown(
            choices=COMPONENTES, value="Todos", label="Componente curricular", scale=2
        )

    with gr.Row():
        dd_ciclo = gr.Dropdown(choices=CICLOS, value="Todos", label="Ciclo", scale=1)
        dd_bloco = gr.Dropdown(choices=BLOCOS, value="Todos", label="Bloco", scale=1)
        dd_ano = gr.Dropdown(choices=ANOS, value="Todos", label="Ano escolar", scale=1)
        btn_buscar = gr.Button("🔍 Buscar", variant="primary", scale=1)

    lbl_contagem = gr.Markdown(contagem_inicial)

    tabela = gr.Dataframe(
        value=df_inicial,
        wrap=True,
        interactive=False,
    )

    with gr.Row():
        btn_exportar = gr.Button("⬇️ Exportar seleção como CSV", variant="secondary")

    arquivo_csv = gr.File(label="Download CSV")

    gr.Markdown("""
---
Dados extraídos do *Currículo em Movimento do Distrito Federal – Ensino Fundamental, 2ª edição*, SEEDF.
[Repositório GitHub](https://github.com/walmeidadf/curriculo-ensinofundamental-df) · Licença MIT
""")

    entradas = [txt_busca, dd_componente, dd_ciclo, dd_bloco, dd_ano]
    saidas_busca = [tabela, lbl_contagem]

    # Busca ao clicar ou pressionar Enter no campo de texto
    btn_buscar.click(buscar, inputs=entradas, outputs=saidas_busca)
    txt_busca.submit(buscar, inputs=entradas, outputs=saidas_busca)

    # Atualização automática ao mudar filtros
    dd_componente.change(buscar, inputs=entradas, outputs=saidas_busca)
    dd_ciclo.change(buscar, inputs=entradas, outputs=saidas_busca)
    dd_bloco.change(buscar, inputs=entradas, outputs=saidas_busca)
    dd_ano.change(buscar, inputs=entradas, outputs=saidas_busca)

    # Exportação CSV
    btn_exportar.click(exportar_csv, inputs=entradas, outputs=arquivo_csv)


if __name__ == "__main__":
    app.launch()
