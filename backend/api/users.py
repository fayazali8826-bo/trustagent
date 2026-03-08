from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, Organization
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import uuid
import secrets

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

SECRET_KEY = os.getenv("SECRET_KEY", "trustagent-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    company: str = ""


class UserLogin(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None


@router.post("/register")
@limiter.limit("5/minute")
def register_user(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    try:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=data.email,
            name=data.name,
            company=data.company,
            password_hash=hash_password(data.password),
        )
        db.add(user)
        db.flush()

        api_key = secrets.token_urlsafe(32)
        org_id = str(uuid.uuid4())
        org = Organization(
            id=org_id,
            name=data.company if data.company else data.name,
            api_key=api_key,
            owner_id=user_id
        )
        db.add(org)
        db.commit()

        token = create_token({"sub": user_id})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user.email,
                "name": user.name,
                "company": user.company,
            },
            "api_key": api_key,
            "message": "Account created successfully!"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
@limiter.limit("10/minute")
def login_user(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        org = db.query(Organization).filter(
            Organization.owner_id == user.id
        ).first()

        token = create_token({"sub": user.id})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "company": user.company,
            },
            "api_key": org.api_key if org else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    org = db.query(Organization).filter(
        Organization.owner_id == user.id
    ).first()

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "company": user.company,
        "api_key": org.api_key if org else None,
        "created_at": user.created_at
    }