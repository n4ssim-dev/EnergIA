from fastapi import FastAPI

from routes.api import router as api_router
from routes.dijkstra import router as dijkstra_router


app = FastAPI()

app.include_router(router=dijkstra_router)
app.include_router(router=api_router)

@app.get("/health")
def health():
    return {"status": "healthy"}
