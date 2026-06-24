from fastapi import APIRouter, Depends, HTTPException, Response, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ..database import get_db
from ..models.models import User, Store
from ..schemas.schemas import UserCreate, UserLogin
from ..deps import create_access_token, get_current_user_optional

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


@router.post("/register")
async def register(
    request: Request,
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
    location: str = Form("Argentina"),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Nombre de usuario ya existe")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or username,
        location=location,
    )
    db.add(user)
    db.flush()

    store = Store(user_id=user.id, name=username)
    db.add(store)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, max_age=604800, samesite="lax")
    return resp


@router.post("/login")
async def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    token = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, max_age=604800, samesite="lax")
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp
