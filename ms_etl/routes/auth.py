import os

from fastapi import Header, HTTPException, status


def check_password(x_password: str | None = Header(default=None)):
    expected = os.getenv("API_PASSWORD", "5")
    if x_password != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect ou absent",
        )
