from fastapi import APIRouter

router = APIRouter(prefix="/datastore")

@router.get("/test")
def health():
    return {"status": "healthy"}