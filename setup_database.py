import os
import sqlite3
import pandas as pd

# ── 1. Localizar e carregar o arquivo CSV ─────────────
csv_path = "data/lol.csv" if os.path.exists("data/lol.csv") else "lol.csv"

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Arquivo CSV não encontrado em 'data/lol.csv' ou 'lol.csv'")

print(f"✓ Carregando dados de '{csv_path}'...")
df = pd.read_csv(csv_path)

# ── 2. Criar/Garantir colunas calculadas (caso não existam) ──
if "game_duration" in df.columns:
    duration_min = df["game_duration"] / 60.0
    duration_min_safe = duration_min.replace(0, 1)

    if "gold_per_minute" not in df.columns and "gold_earned" in df.columns:
        df["gold_per_minute"] = (df["gold_earned"] / duration_min_safe).round(2)

    if "damage_per_minute" not in df.columns and "total_damage_dealt_to_champions" in df.columns:
        df["damage_per_minute"] = (df["total_damage_dealt_to_champions"] / duration_min_safe).round(2)

if "kda" not in df.columns and all(c in df.columns for c in ["kills", "deaths", "assists"]):
    deaths_safe = df["deaths"].replace(0, 1)
    df["kda"] = ((df["kills"] + df["assists"]) / deaths_safe).round(2)

# ── 3. Selecionar as colunas desejadas ────────────────
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

# Filtrar colunas existentes no dataset
columns_to_export = [col for col in selected_columns if col in df.columns]
df_db = df[columns_to_export]

# ── 4. Criar e popular o banco SQLite ─────────────────
os.makedirs("database", exist_ok=True)
db_path = "database/lol.db"
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

print(f"✓ Banco SQLite criado em '{db_path}'")
print(f"✓ Tabela 'league_matches' populada com {len(df_db)} registros e {len(columns_to_export)} colunas")
