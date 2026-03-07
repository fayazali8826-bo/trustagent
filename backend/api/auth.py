from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Organization
from core.crypto import CryptoEngine
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class OrgCreate(BaseModel):
    name: str

class OrgResponse(BaseModel):
    id: str
    name: str
    api_key: str
    message: str

def get_current_org(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    """Validate API key and return organization"""
    org = db.query(Organization).filter(
        Organization.api_key == x_api_key,
        Organization.is_active == True
    ).first()
    if not org:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return org

@router.post("/register", response_model=OrgResponse)
def register_organization(data: OrgCreate, db: Session = Depends(get_db)):
    """Register a new organization and get API key"""
    existing = db.query(Organization).filter(Organization.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization already exists")

    api_key = CryptoEngine.generate_api_key()
    org = Organization(name=data.name, api_key=api_key)
    db.add(org)
    db.commit()
    db.refresh(org)

    return OrgResponse(
        id=org.id,
        name=org.name,
        api_key=api_key,
        message="Save your API key safely — it won't be shown again!"
    )