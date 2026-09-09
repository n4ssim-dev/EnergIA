from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from routes.database import router as database_router
from routes.datastore import router as datastore_router

app = FastAPI()
app.include_router(router=database_router)
app.include_router(router=datastore_router)

@app.get("/health")
def health():
    return {"status": "healthy"}
