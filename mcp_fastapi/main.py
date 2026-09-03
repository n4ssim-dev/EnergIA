from fastapi import FastAPI

from routes.routes import router as routes_router

app = FastAPI()
app.include_router(router=routes_router)

@app.get("/health")
def health():
    return {'status': 'healthy'}

if __name__ == "__main___":
    app.run()