from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    PreferencesUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="email_taken")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        language=payload.language,
        theme="dark",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.language is not None:
        user.language = payload.language
    if payload.theme is not None:
        user.theme = payload.theme
    if payload.name is not None:
        user.name = payload.name
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
