import json

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

OLLAMA_URL = "http://langage:11434"

OLLAMA_MODEL = "qwen2.5:7b"


# --------------------------------------------------
# Données de normalisation
# --------------------------------------------------

REGIONS = {
    "Centre-Val de Loire": 24,
    "Bourgogne-Franche-Comté": 27,
    "Normandie": 28,
    "Hauts-de-France": 32,
    "Grand Est": 44,
    "Pays de la Loire": 52,
    "Bretagne": 53,
    "Nouvelle-Aquitaine": 75,
    "Occitanie": 76,
    "Auvergne-Rhône-Alpes": 84,
    "Provence-Alpes-Côte d'Azur": 93,
    "Corse": 94
}


# --------------------------------------------------
# Normalisation
# --------------------------------------------------

@router.get("/normaliser")
async def normaliser_question(question: str):

    # 1. Vérification de la question
    if not question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question manquante"
        )

    # 2. Récupération dynamique des routes
    async with httpx.AsyncClient() as client:
        routes_response = await client.get(
            "http://mcp-fastapi:8002/routes",
            timeout=30
        )

        routes_response.raise_for_status()
        routes_data = routes_response.json()

    # 3. Construction du texte contenant les routes
    routes_prompt = ""

    for route in routes_data["routes"]:
        routes_prompt += f"""
        - Route : {route["methode"]} {route["chemin"]}
        Description : {route["description"]}
        ID : {route["id"]}
        """


    # 2. Prompt envoyé à Ollama
    prompt = f"""
    Tu es le module d'interprétation des requêtes utilisateur
    de l'application EnergIA.

    Ton rôle n'est PAS de répondre à la question.

    Ton rôle est uniquement de transformer une question en langage naturel
    en une instruction structurée permettant au MCP d'appeler l'API EnergIA.

    Tu dois :

    1. identifier l'intention de l'utilisateur ;
    2. choisir uniquement une route parmi les routes disponibles ;
    3. extraire les paramètres présents dans la question ;
    4. retourner uniquement un JSON valide.


    ROUTES DISPONIBLES

    {routes_prompt}

    NORMALISATION

    REGION :
    Retourne le nom officiel de la région française.

    Exemples :

    "occitanie" -> "Occitanie"
    "OCCITANIE" -> "Occitanie"
    "bretagne" -> "Bretagne"
    "hauts de france" -> "Hauts-de-France"

    N'invente jamais une région.


    HEURE :
    Retourne toujours l'heure au format HH:MM.

    Exemples :

    "8h" -> "08:00"
    "8h30" -> "08:30"
    "18 heures" -> "18:00"


    PUISSANCE :

    Toutes les puissances doivent être exprimées en MW.

    Retourne uniquement une valeur numérique.

    Exemples :

    "500 MW" -> 500
    "1 200 MW" -> 1200
    "1,5 GW" -> 1500


    FORMAT OBLIGATOIRE

{{
    "route_id": null,
    "route": "/nom_route",
    "method": "GET",
    "params": {{}}
}}


    RÈGLES STRICTES

    - "route_id" doit correspondre exactement à l'identifiant de la route choisie dans ROUTES DISPONIBLES.
    - "route" doit correspondre exactement au chemin de cette même route.
    - "method" doit correspondre exactement à sa méthode HTTP.
    - N'invente jamais de route_id, de route ou de méthode.
    - Réponds uniquement avec du JSON valide.
    - Aucun texte avant ou après le JSON.
    - N'invente jamais de route.
    - N'invente jamais de paramètre.
    - N'invente jamais de valeur absente.
    - Respecte exactement les noms des paramètres.
    - Si un paramètre obligatoire est absent, utilise null.


    Si aucune route ne correspond :

    {{
        "route_id": null,
        "route": null,
        "method": null,
        "params": {{}}
    }}


    EXEMPLE 1

    Question utilisateur :
    "Liste-moi toutes les régions disponibles."

    Réponse :

    {{
        "route_id": null,
        "route": "/regions",
        "method": "GET",
        "params": {{}}
    }}

    EXEMPLE 2

    Question utilisateur :
    "Donne-moi les informations de la centrale numéro 12."

    Réponse :

    {{
        "route_id": null,
        "route": "/dijkstra/centrales/{{centrale_id}}",
        "method": "GET",
        "params": {{
            "centrale_id": 12
        }}
    }}

    EXEMPLE 3

    Question utilisateur :
    "Quel est le plus court chemin entre la centrale de Golfech et celle de Tricastin ?"

    Réponse :

    {{
        "route_id": null,
        "route": "/dijkstra/shortest-path",
        "method": "GET",
        "params": {{
            "source": "Golfech",
            "destination": "Tricastin"
        }}
    }}
    
    QUESTION UTILISATEUR

    {question}
    """
    # --------------------------------------------------
    # 3. Appel à Ollama
    # --------------------------------------------------

    try:
        async with httpx.AsyncClient() as client:

            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )

        response.raise_for_status()

    except httpx.HTTPError as erreur:

        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de l'appel à Ollama : {erreur}"
        )

    # --------------------------------------------------
    # 4. Récupération de la réponse Ollama
    # --------------------------------------------------

    ollama_data = response.json()

    texte_json = ollama_data.get("response")

    if not texte_json:

        raise HTTPException(
            status_code=502,
            detail="Ollama n'a retourné aucune réponse"
        )

    # --------------------------------------------------
    # 5. Conversion texte JSON -> dictionnaire Python
    # --------------------------------------------------

    try:

        resultat = json.loads(texte_json)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=502,
            detail="La réponse d'Ollama n'est pas un JSON valide"
        )

    # --------------------------------------------------
    # 6. Récupération des paramètres
    # --------------------------------------------------

    params = resultat.get("params", {})

    # --------------------------------------------------
    # 7. Normalisation déterministe de la région
    # --------------------------------------------------

    region = params.get("region")

    if region is not None:

        region_id = REGIONS.get(region)

        if region_id is None:

            raise HTTPException(
                status_code=400,
                detail=f"Région inconnue : {region}"
            )

        params["region"] = region_id

    # --------------------------------------------------
    # 8. Remise des paramètres normalisés
    # --------------------------------------------------

    resultat["params"] = params

    # --------------------------------------------------
    # 9. Retour au MCP
    # --------------------------------------------------

    return resultat
