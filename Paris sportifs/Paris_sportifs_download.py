import requests
import io
import pandas as pd
import pathlib
import time
import datetime as dt

# -----------------------------
# Fonctions utilitaires
# -----------------------------

def current_completed_season_end_year(today=None) -> int:
    """Retourne l'année de fin de la dernière saison terminée (Europe)."""
    if today is None:
        today = dt.date.today()
    year = today.year
    month = today.month
    # On considère que la saison se termine en mai/juin -> si on est en sept 2025, la saison 24/25 est finie -> 2025
    return year if month >= 8 else year

def season_codes_last_n(n: int, end_year: int):
    """Construit les codes 'YYZZ' pour football-data (ex: 1516, 2425)."""
    codes = []
    for k in range(n):
        zz = end_year - k
        yy = zz - 1
        code = f"{str(yy)[-2:]}{str(zz)[-2:]}"
        codes.append(code)
    return list(reversed(codes))

def fetch_and_save(season_code: str, out_dir="ligue1_data"):
    """Télécharge le CSV Ligue 1 pour la saison donnée et sauvegarde localement."""
    url = f"https://www.football-data.co.uk/mmz4281/{season_code}/F1.csv"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = f"{out_dir}/F1_{season_code}.csv"
    df.to_csv(out_path, index=False)
    print(f"✅ Saison {season_code} téléchargée et sauvegardée dans {out_path}")

# -----------------------------
# Script principal
# -----------------------------
if __name__ == "__main__":
    end_year = current_completed_season_end_year()
    seasons = season_codes_last_n(10, end_year)
    print("Saisons téléchargées :", seasons)

    for code in seasons:
        try:
            fetch_and_save(code)
            time.sleep(1)  # petite pause pour éviter de spammer le site
        except Exception as e:
            print(f"❌ Erreur sur saison {code} : {e}")
