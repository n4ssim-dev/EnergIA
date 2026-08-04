from fastapi import FastAPI

# Importation du fichier routes.py 
from app.api.routes import router

app = FastAPI()

# Ajouter les routes dans main
app.include_router(router)

@app.get("/")
def home():
    return {
        "message": "Microservice Python Fonctionne"
    }
    