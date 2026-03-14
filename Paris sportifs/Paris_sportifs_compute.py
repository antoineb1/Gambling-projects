import pandas as pd
import pathlib
import re

# ------------------------
# Paramètres
# ------------------------
RAW_DIR = "ligue1_data"      # dossier où se trouvent les fichiers F1_xxxx.csv
OUT_DIR = "sortie_data"      # dossier de sortie
OUT_FILE = "ligue1_indice_retour_roi.csv"

SAISONS = None               # ex: ["1516","1617","1718","1819","2021"] ou None pour toutes
MARGE_PAR_DEFAUT = 0.06      # marge moyenne supposée (overround m), O = 1+m

# ------------------------
# Fonctions utilitaires
# ------------------------
def _pick_hda_cols(df: pd.DataFrame):
    """Choisit un triplet H/D/A disponible dans le CSV brut."""
    prefs = [
        ("PSH", "PSD", "PSA"),      # Pinnacle
        ("B365H", "B365D", "B365A"),# Bet365
        ("AvgH", "AvgD", "AvgA"),   # Moyenne
        ("MaxH", "MaxD", "MaxA"),   # Maximum
        ("IWH", "IWD", "IWA"),      # Interwetten
        ("WHH", "WHD", "WHA"),      # William Hill
        ("VCH", "VCD", "VCA"),      # VC
        ("LBH", "LBD", "LBA"),      # Ladbrokes
        ("SBH", "SBD", "SBA"),      # Sportingbet
    ]
    cols = set(df.columns)
    for h,d,a in prefs:
        if h in cols and d in cols and a in cols:
            return h,d,a
    return None, None, None

def build_match_table(raw_dir: str, saisons=None) -> pd.DataFrame:
    """Construit un DataFrame équipe-match avec cote brute et résultat."""
    files = sorted(pathlib.Path(raw_dir).glob("F1_*.csv"))
    if not files:
        raise FileNotFoundError(f"Aucun fichier trouvé dans {raw_dir}/")

    all_rows = []
    for f in files:
        code = re.search(r"F1_(\d{4})\.csv$", f.name)
        code = code.group(1) if code else None
        if saisons is not None and code not in saisons:
            continue

        df = pd.read_csv(f)
        hcol, dcol, acol = _pick_hda_cols(df)
        if hcol is None:
            continue

        tmp = df[["HomeTeam","AwayTeam","FTR",hcol,acol]].copy()
        tmp[hcol] = pd.to_numeric(tmp[hcol], errors="coerce")
        tmp[acol] = pd.to_numeric(tmp[acol], errors="coerce")
        tmp = tmp.dropna()

        # Lignes domicile
        home = pd.DataFrame({
            "season_code": code,
            "team": tmp["HomeTeam"],
            "opponent": tmp["AwayTeam"],
            "terrain": "Domicile",
            "cote": tmp[hcol],
            "result": tmp["FTR"].map(lambda x: "Gagné" if x=="H" else "Perdu")
        })

        # Lignes extérieur
        away = pd.DataFrame({
            "season_code": code,
            "team": tmp["AwayTeam"],
            "opponent": tmp["HomeTeam"],
            "terrain": "Extérieur",
            "cote": tmp[acol],
            "result": tmp["FTR"].map(lambda x: "Gagné" if x=="A" else "Perdu")
        })

        all_rows.append(pd.concat([home,away], ignore_index=True))

    if not all_rows:
        raise ValueError("Aucune donnée exploitable.")

    data = pd.concat(all_rows, ignore_index=True)
    data = data.dropna(subset=["team","cote"])
    data = data[(data["cote"]>=1.01)&(data["cote"]<=200.0)]
    return data

def compute_indicators(data: pd.DataFrame, marge=MARGE_PAR_DEFAUT) -> pd.DataFrame:
    """
    Calcule ROI et indicateurs par équipe.
    NOTE: 'cote_retire_marge' = cote * (1+marge) -> on RETIRE la marge du bookmaker (overround O=1+m).
    """
    data["victoire"] = (data["result"]=="Gagné").astype(int)

    # >>> On RETIRE la marge du bookmaker pour obtenir une cote 'fair' approx :
    # Probabilité brute q = 1/c, overround O = 1+m, prob. fair p = q/O, donc cote fair = 1/p = c * O
    data["cote_retire_marge"] = data["cote"] * (1 + marge)

    grp = data.groupby("team")
    nb_matchs = grp["victoire"].count().rename("Nombre_matchs")
    nb_victoires = grp["victoire"].sum().rename("Nombre_victoires")

    # Sommes (brut vs retirée marge)
    somme_cotes_si_victoires = (data["victoire"]*data["cote"]).groupby(data["team"]).sum().rename("Somme_cotes_si_victoires")
    somme_cotes_si_victoires_retire_marge = (data["victoire"]*data["cote_retire_marge"]).groupby(data["team"]).sum().rename("Somme_cotes_si_victoires_retire_marge")

    somme_cotes_toutes = grp["cote"].sum().rename("Somme_cotes_toutes")
    somme_cotes_toutes_retire_marge = grp["cote_retire_marge"].sum().rename("Somme_cotes_toutes_retire_marge")

    # ROI % (brut vs retirée marge)
    roi_pct = ((somme_cotes_si_victoires - nb_matchs) / nb_matchs * 100).rename("ROI_pourcent")
    roi_pct_retire_marge = ((somme_cotes_si_victoires_retire_marge - nb_matchs) / nb_matchs * 100).rename("ROI_pourcent_retire_marge")

    # Assemblage
    tableau = pd.concat([
        nb_matchs, nb_victoires,
        somme_cotes_si_victoires, somme_cotes_si_victoires_retire_marge,
        somme_cotes_toutes, somme_cotes_toutes_retire_marge,
        roi_pct, roi_pct_retire_marge
    ], axis=1).reset_index()

    # Indicateurs dérivés
    tableau["Indice_de_retour"] = tableau["Somme_cotes_si_victoires"] / tableau["Nombre_matchs"]
    tableau["Indice_de_retour_retire_marge"] = tableau["Somme_cotes_si_victoires_retire_marge"] / tableau["Nombre_matchs"]

    tableau["Cote_moyenne_tous_matchs"] = tableau["Somme_cotes_toutes"] / tableau["Nombre_matchs"]
    tableau["Cote_moyenne_tous_matchs_retire_marge"] = tableau["Somme_cotes_toutes_retire_marge"] / tableau["Nombre_matchs"]

    tableau["Taux_de_victoire"] = tableau["Nombre_victoires"] / tableau["Nombre_matchs"]
    tableau["Marge_bookmaker_assumee_%"] = marge * 100

    # Tri par ROI avec marge RETIRÉE (vision "fair")
    tableau = tableau.sort_values(
        ["ROI_pourcent_retire_marge","Indice_de_retour_retire_marge"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return tableau

# ------------------------
# Script principal
# ------------------------
def main():
    # 1) Construire la base match par match
    data = build_match_table(RAW_DIR, saisons=SAISONS)
    print(f"Base construite : {len(data)} lignes équipe-match")

    # 2) Calculer les indicateurs
    tableau = compute_indicators(data, marge=MARGE_PAR_DEFAUT)

    # 3) Sauvegarder dans dossier sortie_data/
    out_path = pathlib.Path(OUT_DIR)
    out_path.mkdir(parents=True, exist_ok=True)
    full_path = out_path / OUT_FILE

    # Utilise ; pour un Excel FR
    tableau.to_csv(full_path, index=False, sep=";", encoding="utf-8")
    print(f"✅ Fichier final écrit : {full_path}")
    print(tableau.head(15).to_string(index=False))

if __name__ == "__main__":
    main()
