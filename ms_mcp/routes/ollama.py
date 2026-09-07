import json
import os

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

OLLAMA_URL = "http://langage:11434"
OLLAMA_MODEL = "qwen2.5:7b"

MCP_FASTAPI_URL = "http://mcp-fastapi:8003"
API_URL = "http://python-service:8000"
API_PASSWORD = os.getenv("API_PASSWORD", "5")


async def appeler_ollama(prompt: str, *, timeout: float) -> str:
    # Note : le format JSON contraint d'Ollama ("format": "json") force une
    # sortie syntaxiquement valide mais est très lent en inférence CPU
    # (grammaire GBNF). On s'appuie donc uniquement sur le prompt pour
    # obtenir du JSON, avec un parsing tolérant côté appelant.
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_thread": os.cpu_count() or 4},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=timeout,
            )
        response.raise_for_status()
    except httpx.HTTPError as erreur:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de l'appel à Ollama : {erreur}"
        )

    texte = response.json().get("response")

    if not texte:
        raise HTTPException(
            status_code=502,
            detail="Ollama n'a retourné aucune réponse"
        )

    return texte


def tronquer_listes(valeur, max_elements: int = 5):
    """Réduit les listes imbriquées à `max_elements` pour garder un JSON
    valide et léger (plutôt que de tronquer bêtement une chaîne, ce qui
    casse la syntaxe JSON et perturbe le modèle)."""
    if isinstance(valeur, list):
        tronquee = [tronquer_listes(v, max_elements) for v in valeur[:max_elements]]
        if len(valeur) > max_elements:
            tronquee.append(f"... ({len(valeur) - max_elements} éléments non affichés)")
        return tronquee
    if isinstance(valeur, dict):
        return {cle: tronquer_listes(v, max_elements) for cle, v in valeur.items()}
    return valeur


@router.get("/normaliser")
async def normaliser_question(question: str):

    if not question.strip():
        raise HTTPException(status_code=400, detail="Question manquante")

    # --------------------------------------------------
    # 1. Extraction de mots-clés depuis la question
    # --------------------------------------------------

    prompt_mots_cles = f"""
    Tu extrais les mots-clés importants d'une question posée à propos
    du réseau électrique français (centrales, régions, consommation,
    production, simulation, anomalies...).

    Réponds uniquement avec un JSON de la forme :
    {{"mots_cles": ["mot1", "mot2"]}}

    Question : {question}
    """

    texte_mots_cles = await appeler_ollama(prompt_mots_cles, timeout=90)

    try:
        debut, fin = texte_mots_cles.index("{"), texte_mots_cles.rindex("}") + 1
        mots_cles = json.loads(texte_mots_cles[debut:fin]).get("mots_cles", [])
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="La réponse d'Ollama (mots-clés) n'est pas un JSON valide"
        )

    mots_cles = [m.lower().strip() for m in mots_cles if isinstance(m, str) and m.strip()]

    if not mots_cles:
        raise HTTPException(
            status_code=422,
            detail="Aucun mot-clé n'a pu être extrait de la question"
        )

    # --------------------------------------------------
    # 2. Recherche des routes dont la description contient un mot-clé
    # --------------------------------------------------

    async with httpx.AsyncClient() as client:
        routes_response = await client.get(f"{MCP_FASTAPI_URL}/routes", timeout=30)
        routes_response.raise_for_status()
        toutes_les_routes = routes_response.json()["routes"]

    routes_correspondantes = [
        route
        for route in toutes_les_routes
        if route["methode"] == "GET"
        and "{" not in route["chemin"]
        and any(mot in route["description"].lower() for mot in mots_cles)
    ]

    if not routes_correspondantes:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune route ne correspond aux mots-clés {mots_cles}"
        )

    # --------------------------------------------------
    # 3. Appel des routes correspondantes sur l'API EnergIA
    # --------------------------------------------------

    resultats = []

    async with httpx.AsyncClient() as client:
        for route in routes_correspondantes:
            chemin = route["chemin"]

            try:
                reponse = await client.get(
                    f"{API_URL}{chemin}",
                    headers={"x-password": API_PASSWORD},
                    timeout=30,
                )
                try:
                    donnees = reponse.json()
                except ValueError:
                    donnees = reponse.text

                resultats.append({
                    "route": chemin,
                    "status": reponse.status_code,
                    "donnees": donnees,
                })
            except httpx.HTTPError as erreur:
                resultats.append({"route": chemin, "erreur": str(erreur)})

    # --------------------------------------------------
    # 4. Génération d'une réponse en langage naturel
    # --------------------------------------------------

    # On tronque les listes des données de chaque route (et, en filet de
    # sécurité, la chaîne JSON résultante) pour rester dans une taille de
    # prompt raisonnable : le modèle tourne avec une fenêtre de contexte
    # limitée, surtout en inférence CPU, et certains objets (ex: centrales)
    # restent volumineux même réduits à quelques éléments.
    TAILLE_MAX_PAR_ROUTE = 800
    lignes = []
    for r in resultats:
        texte = json.dumps(tronquer_listes(r.get("donnees", r.get("erreur")), max_elements=2), ensure_ascii=False)
        if len(texte) > TAILLE_MAX_PAR_ROUTE:
            texte = texte[:TAILLE_MAX_PAR_ROUTE] + "... (tronqué)"
        lignes.append(f"- {r['route']} : {texte}")
    donnees_texte = "\n".join(lignes)

    prompt_reponse = f"""
    Tu es l'assistant de l'application EnergIA.

    Réponds en français, de façon claire et concise, à la question de
    l'utilisateur en te basant uniquement sur les données JSON fournies
    ci-dessous (éventuellement tronquées). N'invente aucune donnée absente
    de ces données.

    QUESTION : {question}

    DONNÉES :
    {donnees_texte}
    """

    reponse_texte = await appeler_ollama(prompt_reponse, timeout=280)

    return {
        "question": question,
        "mots_cles": mots_cles,
        "routes_utilisees": [r["route"] for r in resultats],
        "reponse": reponse_texte.strip(),
    }
