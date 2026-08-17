import os
import sqlite3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# ── Configuração da Página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="League of Legends Dashboard",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Inicialização do Banco de Dados (se não existir) ────────────────────────
def _inicializar_banco_se_necessario(
    db_path: str = "database/lol.db", csv_path: str = "data/lol.csv"
):
    """Gera o banco SQLite a partir do CSV caso ainda não exista (ex: deploy em nuvem)."""
    if os.path.exists(db_path):
        return

    if not os.path.exists(csv_path) and os.path.exists("lol.csv"):
        csv_path = "lol.csv"

    if os.path.exists(csv_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        df = pd.read_csv(csv_path)

        # Cálculo de métricas caso não existam no CSV
        if "game_duration" in df.columns:
            duration_min = df["game_duration"] / 60.0
            duration_min_safe = duration_min.replace(0, 1)

            if "gold_per_minute" not in df.columns and "gold_earned" in df.columns:
                df["gold_per_minute"] = (df["gold_earned"] / duration_min_safe).round(2)

            if (
                "damage_per_minute" not in df.columns
                and "total_damage_dealt_to_champions" in df.columns
            ):
                df["damage_per_minute"] = (
                    df["total_damage_dealt_to_champions"] / duration_min_safe
                ).round(2)

        if "kda" not in df.columns and all(
            c in df.columns for c in ["kills", "deaths", "assists"]
        ):
            deaths_safe = df["deaths"].replace(0, 1)
            df["kda"] = ((df["kills"] + df["assists"]) / deaths_safe).round(2)

        selected_columns = [
            "match_id",
            "game_duration",
            "champion_name",
            "team_position",
            "team_id",
            "win",
            "kills",
            "deaths",
            "assists",
            "kda",
            "kill_participation",
            "gold_earned",
            "gold_per_minute",
            "total_minions_killed",
            "damage_per_minute",
            "total_damage_dealt_to_champions",
            "total_damage_taken",
            "vision_score",
            "wards_killed",
            "dragon_kills",
        ]
        columns_to_export = [col for col in selected_columns if col in df.columns]
        df_db = df[columns_to_export] if columns_to_export else df

        conn = sqlite3.connect(db_path)
        df_db.to_sql(
            "league_matches",
            conn,
            if_exists="replace",
            index=True,
            index_label="id",
            chunksize=1000,
        )
        conn.close()


# ── Funções de Carregamento com Cache ───────────────────────────────────────
@st.cache_data
def carregar_csv(caminho_csv: str = "data/lol.csv") -> pd.DataFrame:
    """Carrega os dados da partida a partir do arquivo CSV."""
    if not os.path.exists(caminho_csv) and os.path.exists("lol.csv"):
        caminho_csv = "lol.csv"

    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(
            f"Arquivo CSV não encontrado em '{caminho_csv}' ou 'lol.csv'"
        )

    df = pd.read_csv(caminho_csv)
    return df


@st.cache_data
def carregar_banco(
    caminho_db: str = "database/lol.db", tabela: str = "league_matches"
) -> pd.DataFrame:
    """Carrega os dados da partida diretamente da tabela no banco de dados SQLite."""
    _inicializar_banco_se_necessario(db_path=caminho_db)

    if not os.path.exists(caminho_db):
        raise FileNotFoundError(f"Banco de dados não encontrado em '{caminho_db}'")

    conn = sqlite3.connect(caminho_db)
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df


# ── Menu lateral ─────────────────────────────────────
st.sidebar.title("League of Legends Dashboard")
st.sidebar.markdown("---")
pagina = st.sidebar.radio("Navegação", ["Início", "Análise Exploratória"])

if pagina == "Início":
    st.title("League of Legends Dashboard")
    st.markdown("""
    Bem-vindo ao **League of Legends Dashboard** — uma aplicação interativa para explorar os dados do jogo League of Legends.
    """)
    st.markdown("---")
    col1 = st.columns(1)
    st.info(
        "Este dashboard permite analisar partidas de League of Legends, explorando estatísticas detalhadas de jogadores, campeões e partidas. Utilize o menu lateral para navegar entre as diferentes seções e descobrir insights valiosos sobre o jogo."
    )
elif pagina == "Análise Exploratória":
    st.title("Análise Exploratória")
    df_csv = carregar_csv()
    tipo = st.selectbox(
        "Escolha o gráfico:",
        [
            "KDA × Vitória",
            "Dano por minuto × Vitória",
            "Desempenho por posição",
        ],
    )
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.set_theme(style="whitegrid")
    if tipo == "KDA × Vitória":
        st.info("Jogadores com KDA maior realmente vencem mais partidas?")
        df_csv["kda_faixa"] = pd.cut(
            df_csv["kda"],
            bins=[0, 1, 2, 3, 5, 10, float("inf")],
            labels=["0-1", "1-2", "2-3", "3-5", "5-10", "10+"],
        )

        taxa_vitoria = (
            df_csv.groupby("kda_faixa", observed=True)["win"].mean().reset_index()
        )

        sns.barplot(data=taxa_vitoria, x="kda_faixa", y="win")

        plt.title("Taxa de vitória por faixa de KDA")
        plt.xlabel("KDA")
        plt.ylabel("Taxa de vitória")
        plt.show()
    elif tipo == "Dano por minuto × Vitória":
        st.info("causar mais dano está relacionado com vencer?")
        df_csv["resultado"] = df_csv["win"].map({False: "Derrota", True: "Vitória"})

        sns.boxplot(data=df_csv, x="resultado", y="damage_per_minute")

        plt.title("Dano por minuto: Vitória vs Derrota")
        plt.xlabel("Resultado")
        plt.ylabel("Dano por minuto")
        plt.show()
    elif tipo == "Desempenho por posição":
        st.info("Qual posição apresenta maior dano médio por minuto")
        dano_posicao = (
            df_csv.groupby("team_position")["damage_per_minute"]
            .mean()
            .sort_values(ascending=False)
            .reset_index()
        )

        sns.barplot(data=dano_posicao, x="team_position", y="damage_per_minute")

        plt.title("Dano médio por minuto por posição")
        plt.xlabel("Posição")
        plt.ylabel("Dano por minuto")
        plt.show()

    st.pyplot(fig)
