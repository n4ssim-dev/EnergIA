from fastapi import FastAPI

from routes.dijkstra import router as dijkstra_router

app = FastAPI()

app.include_router(router=dijkstra_router)
