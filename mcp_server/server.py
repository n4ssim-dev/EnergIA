from pathlib import Path
import sys

# Chemin vers le dossier fastapi du projet
FASTAPI_DIR = Path(__file__).resolve().parents[1] / "fastapi"

# Permet à Python de trouver graph/ et routes/
sys.path.insert(0, str(FASTAPI_DIR))

from mcp.server.fastmcp import FastMCP
from routes.api import get_regions,get_centrales


mcp = FastMCP("EnergIA")


@mcp.tool()
def get_regions_mcp() -> dict:
    """
    Retourne la liste des régions disponibles dans EnergIA.
    """
    return get_regions()

@mcp.tool()
def get_centrales_mcp() -> dict:
    """
    Retourne la liste des centrales disponibles dans EnergIA.
    """
    return get_centrales()

@mcp.tool()
def get_etat_centrales_mcp() -> dict:
    """
    Retourne l'état d'une centrale dans EnergIA.
    """
    return get_centrales()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")