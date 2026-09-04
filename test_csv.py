
import pandas as pd

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

CSV_PATH = BASE_DIR /"EnergIA"/"fastapi"/ "data" / "eco2mix-regional-tr.csv"

print(CSV_PATH)
print(CSV_PATH.exists())

df = pd.read_csv(
    CSV_PATH,
    sep=";"
)

colonnes_utiles = [
    "Code INSEE région",
    "Région",
    "Date",
    "Heure",
    "Date - Heure",
    "Consommation (MW)",
    "Thermique (MW)",
    "Nucléaire (MW)",
    "Eolien (MW)",
    "Solaire (MW)",
    "Hydraulique (MW)",
    "Bioénergies (MW)",
    "Ech. physiques (MW)"
]
df = df[colonnes_utiles].copy()

REGIONS_ATTENDUES = {
    "Auvergne-Rhône-Alpes",
    "Bourgogne-Franche-Comté",
    "Bretagne",
    "Centre-Val de Loire",
    "Corse",
    "Grand Est",
    "Hauts-de-France",
    "Île-de-France",
    "Normandie",
    "Nouvelle-Aquitaine",
    "Occitanie",
    "Pays de la Loire",
    "Provence-Alpes-Côte d'Azur"
}

regions_presentes = set(df["Région"].dropna().unique())

regions_manquantes = REGIONS_ATTENDUES - regions_presentes

print("Régions manquantes :", regions_manquantes)

# print(df.head())

# df["Date - Heure"] = pd.to_datetime(
#     df["Date - Heure"],
#     errors="coerce"
# )

# print(df["Date - Heure"].dtype)

# df_occitanie = df[
#     df["Région"] == "Occitanie"
# ].copy()

# print(df_occitanie.head())
# print(len(df_occitanie))

# jour = pd.to_datetime("2026-07-01").date()

# df_jour = df_occitanie[
#     df_occitanie["Date - Heure"].dt.date == jour
# ].copy()

# print(df_jour)
# print("Nombre de lignes :", len(df_jour))

# df_jour = df_jour.sort_values("Date - Heure")

# print(
#     df_jour[
#         [
#             "Date - Heure",
#             "Consommation (MW)",
#             "Nucléaire (MW)",
#             "Eolien (MW)",
#             "Solaire (MW)"
#         ]
#     ]
# )

# regions_codes = (
#     df[["Code INSEE région", "Région"]]
#     .drop_duplicates()
#     .sort_values("Code INSEE région")
# )

# print(regions_codes)
# print("Nombre de régions :", len(regions_codes))

# jour = pd.to_datetime("2026-07-01").date()

# df_jour_france = df[
#     df["Date - Heure"].dt.date == jour
# ]

# nombre_lignes_par_region = (
#     df_jour_france
#     .groupby("Région")
#     .size()
#     .sort_index()
# )

# print(nombre_lignes_par_region)

# if len(nombre_lignes_par_region) == 13 and (nombre_lignes_par_region == 96).all():
#     print("OK : 13 régions avec 96 pas de 15 minutes")
# else:
#     print("Attention : données manquantes")
#     print(nombre_lignes_par_region)

