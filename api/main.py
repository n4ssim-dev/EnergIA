from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI

from routes.auth import check_password
from routes.dijkstra import router as dijkstra_router
from routes.gateway import router as gateway_router

app = FastAPI()
app.include_router(dijkstra_router, dependencies=[Depends(check_password)])
app.include_router(gateway_router, dependencies=[Depends(check_password)])


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/")
def home():
    return {"message": "Microservice Python Fonctionne"}
