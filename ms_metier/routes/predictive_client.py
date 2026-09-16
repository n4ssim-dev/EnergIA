import os

import httpx


PREDICTIVE_URL = os.getenv(
    "PREDICTIVE_URL",
    "http://localhost:8005"
)

def recuperer_predictions(date: str, regions: list[str]):

    payload = {
        "date_debut": f"{date}T00:00:00",
        "date_fin": f"{date}T23:30:00",
        "regions": regions,
    }

    reponse = httpx.post(
        f"{PREDICTIVE_URL}/predictions/periode",
        json=payload,
        timeout=60.0,
    )

    reponse.raise_for_status()

    donnees = reponse.json()

    return donnees["predictions"]

# if __name__ == "__main__":

#     predictions = recuperer_predictions(
#         "2026-08-30",
#         ["occitanie"]
#     )

#     print(predictions[:3])