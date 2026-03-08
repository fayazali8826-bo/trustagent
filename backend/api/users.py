from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from core.crypto import CryptoEngine
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "trustagent-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    company: str = ""

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register")
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=data.email,
        name=data.name,
        company=data.company,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-create their organization
    from database.models import Organization
    api_key = CryptoEngine.generate_api_key()
    org = Organization(
        name=data.company or data.name,
        api_key=api_key,
        owner_id=user.id
    )
    db.add(org)
    db.commit()

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
        "api_key": api_key,
        "message": "Account created successfully!"
    }

@router.post("/login")
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Get their organization
    from database.models import Organization
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

@router.get("/me")
def get_me(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from database.models import Organization
    org = db.query(Organization).filter(
        Organization.owner_id == current_user.id
    ).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "company": current_user.company,
        "api_key": org.api_key if org else None,
        "created_at": current_user.created_at
    }

@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Wrong current password")
    current_user.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "Password changed successfully"}