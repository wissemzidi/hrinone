from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_token, current_user, verify_password
from ..database import get_db
from ..ratelimit import limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginOut)
def login(data: schemas.LoginIn, request: Request, db: Session = Depends(get_db)):
    host = request.client.host if request.client else "unknown"
    limit(f"login:{host}", 20, 60)  # slows down password guessing
    limit(f"login-user:{data.email.strip().lower()}", 8, 60)
    user = db.scalar(select(models.User).where(models.User.email == data.email.strip().lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    if user.employee and user.employee.status != "active":
        raise HTTPException(403, "This account is inactive. Contact HR")
    return {"token": create_token(user), "user": user}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user
