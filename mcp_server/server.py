from pathlib import Path
import sys
import httpx
import json


# Chemin vers le dossier fastapi du projet
FASTAPI_DIR = Path(__file__).resolve().parents[1] / "fastapi"

# Permet à Python de trouver graph/ et routes/
sys.path.insert(0, str(FASTAPI_DIR))


# from mcp.server.fastmcp import FastMCP
# from routes.api import get_regions,get_centrales

# from mcp.server.fastmcp import FastMCP
# from routes.analytics import (
#     etat_centrale,
#     centrales_disponibles,
#     consommation_region,
#     region_consommation_max,
#     situation_region,
# )


from fastapi import Depends, FastAPI
app = FastAPI()


#mcp = FastMCP("EnergIA")
# mcp = FastMCP(
#     "EnergIA",
#     host="0.0.0.0",
#     port=8000,
# )

# appel au docker du microservice d'Ollama
OLLAMA_URL = "http://localhost:11434"

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/normaliser")
async def normaliser_question(question: str ):
    print(question)
#verif question non nulle
    if not question:
        raise Exception(
            status_code=400,
            detail="Question manquante"
        )


    prompt = '''
        Tu es le module de normalisation de EnergIA.

        Transforme la question utilisateur en JSON.

        Actions possibles :
        - liste_regions
        - liste_centrales
        - etat_centrale
        - consommation_region
        - production_region
        - simulation

        Format attendu :
        {
        "action": "...",
        "region": null,
        "centrale": null,
        "heure": null
        }

        Question :
        ${question}

        # Réponds uniquement avec le JSON.
        '''

    print(prompt)
    async with httpx.AsyncClient() as client:

        response = await client.post(
            f"http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "question": prompt
            },
            timeout=60
        )
        print(response)

        response.raise_for_status()

        return response.json()


# async def poser_question_energia(question: str):
#     return await normaliser_question(question)

# # @mcp.get()
# def get_regions_mcp() -> dict:
#     """
#     Retourne la liste des régions disponibles dans EnergIA.
#     """
#     return get_regions()

# # @mcp.tool()
# def get_centrales_mcp() -> dict:
#     """
#     Retourne la liste des centrales disponibles dans EnergIA.
#     """
#     return get_centrales()

# # @mcp.tool()
# def get_etat_centrales_mcp() -> dict:
#     """
#     Retourne l'état d'une centrale dans EnergIA.
#     """
#     return get_centrales()

# mcp = FastMCP(
#     "EnergIA",
#     host="0.0.0.0",
#     port=8000,
# )


# @mcp.tool()
# def etat_centrale_mcp(centrale_id: str) -> dict:
#     """
#     Retourne l'état détaillé d'une centrale électrique.

#     Inclut notamment :
#     - disponibilité
#     - puissance installée
#     - puissance actuelle
#     - marge de manoeuvre
#     - puissance minimale de fonctionnement
#     - nombre de réacteurs
#     - état des réacteurs
#     """
#     return etat_centrale(centrale_id)


# @mcp.tool()
# def centrales_disponibles_mcp() -> dict:
#     """
#     Retourne la liste des centrales actuellement disponibles
#     ainsi que le nombre total de centrales.
#     """
#     return centrales_disponibles()


# @mcp.tool()
# def consommation_region_mcp(
#     region_id: str,
#     heure: str,
#     jour_relatif: str = "reference_day",
# ) -> dict:
#     """
#     Retourne la consommation électrique d'une région à une heure donnée.

#     heure peut être donnée sous plusieurs formats :
#     - 19
#     - 19h
#     - 19h00
#     - 19:00

#     jour_relatif permet de sélectionner le jour de référence.
#     """
#     return consommation_region(
#         region_id=region_id,
#         heure=heure,
#         jour_relatif=jour_relatif,
#     )


# @mcp.tool()
# def region_consommation_max_mcp(
#     heure: str,
#     jour_relatif: str = "reference_day",
# ) -> dict:
#     """
#     Retourne la région qui consomme le plus d'électricité
#     à une heure donnée, avec le classement de toutes les régions.
#     """
#     return region_consommation_max(
#         heure=heure,
#         jour_relatif=jour_relatif,
#     )


# @mcp.tool()
# def situation_region_mcp(
#     region_id: str,
#     heure: str,
#     jour_relatif: str = "reference_day",
# ) -> dict:
#     """
#     Retourne la situation énergétique complète d'une région
#     à une heure donnée.

#     Inclut :
#     - consommation
#     - production solaire/éolienne non pilotable
#     - production par filière
#     - capacité installée
#     - solde production-consommation
#     """
#     return situation_region(
#         region_id=region_id,
#         heure=heure,
#         jour_relatif=jour_relatif,
#     )




if __name__ == "__main__":
    # mcp.run(transport="streamable-http")
    pass