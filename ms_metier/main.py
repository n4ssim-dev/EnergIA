from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI

from routes.api import router as api_router
from routes.auth import check_password
from routes.metier import router as metier_router


app = FastAPI()

app.include_router(router=metier_router, dependencies=[Depends(check_password)])
app.include_router(router=api_router)

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/")
def home():
    return {"message": "Microservice Python Fonctionne"}