import streamlit as st
import pandas as pd
import google.generativeai as genai
import psycopg2
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# --- 1. Configurações Iniciais ---
st.set_page_config(layout="wide", page_title="Chat SQL de Arrecadação")
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("Chave da API do Google não encontrada.")
    st.stop()
genai.configure(api_key=api_key)

# --- 2. Conexão com o Banco de Dados ---
@st.cache_resource
def get_db_engine():
    try:
        db_url = "postgresql+psycopg2://user:password@postgres:5432/meubanco"
        engine = create_engine(db_url)
        with engine.connect() as connection:
            pass
        return engine
    except Exception as e:
        st.error(f"Não foi possível conectar ao banco de dados: {e}")
        return None

engine = get_db_engine()
if engine is None:
    st.stop()
else:
    st.toast("🚀 Conexão com o banco de dados estabelecida!")

# --- Função para Carregar Nomes de Receitas ---
@st.cache_data
def carregar_df_receitas(_engine):
    try:
        with _engine.connect() as connection:
            query = "SELECT nome_receita FROM dados_mario GROUP BY nome_receita ORDER BY nome_receita;"
            return pd.read_sql_query(text(query), connection)
    except Exception as e:
        st.sidebar.error("Tabela 'dados_mario' não encontrada. Recarregue os dados no PgAdmin.")
        return pd.DataFrame({'nome_receita': []})

# --- 3. Sidebar ---
st.sidebar.title("Filtros e Opções")
df_receitas = carregar_df_receitas(engine)

receitas_selecionadas = st.sidebar.multiselect(
    label="Filtre por uma ou mais receitas",
    options=df_receitas['nome_receita'].tolist(),
    placeholder="Pesquise uma receita..."
)
with st.sidebar.expander("Ver/Pesquisar todos os nomes de receitas"):
    st.dataframe(df_receitas, use_container_width=True, hide_index=True)


# --- 4. Lógica do Agente LLM (Prompts Atualizados) ---
sql_table_schema = "CREATE TABLE dados_mario (ano INTEGER, mes TEXT, nome_receita TEXT, arrecadado NUMERIC);"

PROMPT_GERADOR_SQL = f"""
Você é um especialista em PostgreSQL. Sua única tarefa é gerar UMA CONSULTA SQL a partir da pergunta do usuário.
REGRAS:
- Sua resposta DEVE SER APENAS o código SQL puro. Não inclua "```sql" ou explicações.
- Para calcular a MEDIANA da coluna 'arrecadado', use a função `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY arrecadado)`.
- Schema da Tabela `dados_mario`: {sql_table_schema}
"""

PROMPT_GERADOR_GRAFICO = """
Você é um especialista em visualização de dados com Python e matplotlib.
Sua tarefa é EXCLUSIVAMENTE gerar um código Python para plotar um gráfico a partir de um DataFrame chamado `df_resultado`.
REGRAS CRÍTICAS:
- Sua resposta DEVE SER APENAS o código Python puro. NÃO inclua "```python" ou explicações.
- O gráfico DEVE ser salvo como `grafico_gerado.png`.
- NÃO use `plt.show()`.
"""

# --- 5. Interface Principal do Chat ---
st.title("🤖 Chat com Banco de Dados e Gráficos")
st.info("Peça totais, médias, medianas e também gráficos de barras!")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- CORREÇÃO DO BUG AQUI ---
# Exibição do histórico com verificação se o arquivo de imagem existe
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("query"):
            with st.expander("Ver consulta SQL"):
                st.code(message["query"], language="sql")
        if message.get("dataframe"):
            st.dataframe(pd.DataFrame(message["dataframe"]), use_container_width=True, hide_index=True)
        # SÓ TENTA EXIBIR A IMAGEM SE A CHAVE EXISTIR E O ARQUIVO TAMBÉM
        if message.get("image") and os.path.exists(message["image"]):
            st.image(message["image"])

if prompt_usuario := st.chat_input("Qual o total arrecadado por ano?"):
    st.session_state.messages.append({"role": "user", "content": prompt_usuario})
    with st.chat_message("user"):
        st.markdown(prompt_usuario)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                # ETAPA 1: Gerar e Executar SQL
                contexto_filtro = f"Contexto de filtro: Receitas selecionadas: {receitas_selecionadas if receitas_selecionadas else 'Nenhuma'}.\n"
                prompt_sql_completo = contexto_filtro + f"Pergunta: {prompt_usuario}"

                model_sql = genai.GenerativeModel('gemini-1.5-flash', system_instruction=PROMPT_GERADOR_SQL)
                response_sql = model_sql.generate_content(prompt_sql_completo)
                sql_query = response_sql.text.strip().replace("```sql", "").replace("```", "")

                with engine.connect() as connection:
                    df_resultado = pd.read_sql_query(text(sql_query), connection)

                mensagem_resposta = f"**Resultado para:** '{prompt_usuario}'"
                if receitas_selecionadas:
                     mensagem_resposta += f"\n\n*Filtro aplicado para: {', '.join(receitas_selecionadas)}*"

                st.markdown(mensagem_resposta)
                st.dataframe(df_resultado, use_container_width=True, hide_index=True)

                msg_assistente = {
                    "role": "assistant",
                    "content": mensagem_resposta,
                    "query": sql_query,
                    "dataframe": df_resultado.to_dict('records')
                }

                # Limpa gráfico antigo para garantir que não exibiremos um gráfico obsoleto
                if os.path.exists('grafico_gerado.png'):
                    os.remove('grafico_gerado.png')

                # ETAPA 2: Gerar Gráfico se solicitado
                palavras_chave_grafico = ['gráfico', 'grafico', 'plotar', 'plot', 'barras', 'visualizar', 'desenhar']
                if any(palavra in prompt_usuario.lower() for palavra in palavras_chave_grafico):
                    with st.spinner("Criando visualização..."):
                        df_info_para_prompt = f"O DataFrame `df_resultado` para plotar tem as colunas: {df_resultado.columns.tolist()}. Gere o código para o gráfico."
                        prompt_grafico_completo = f"{df_info_para_prompt}\n\nInstrução: {prompt_usuario}"

                        model_grafico = genai.GenerativeModel('gemini-1.5-flash', system_instruction=PROMPT_GERADOR_GRAFICO)
                        response_grafico = model_grafico.generate_content(prompt_grafico_completo)
                        codigo_grafico = response_grafico.text.strip().replace("```python", "").replace("```", "")

                        local_scope = {"df_resultado": df_resultado, "plt": plt, "mtick": mtick}
                        exec(codigo_grafico, {}, local_scope)

                        if os.path.exists('grafico_gerado.png'):
                            st.image('grafico_gerado.png')
                            msg_assistente["image"] = 'grafico_gerado.png'

                st.session_state.messages.append(msg_assistente)

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"Desculpe, ocorreu um erro: {e}"})