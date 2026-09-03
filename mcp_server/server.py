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

if __name__ == "__main__":
    # mcp.run(transport="streamable-http")
    pass