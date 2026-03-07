from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Agent, BehaviorLog, AgentInteraction, Organization
from core.crypto import CryptoEngine
from core.trust_engine import trust_engine
from api.auth import get_current_org
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter()

class AgentCreate(BaseModel):
    name: str
    capabilities: List[str]

class BehaviorEvent(BaseModel):
    action: str
    payload: dict

class InteractionRequest(BaseModel):
    sender_id: str
    receiver_id: str
    message: dict
    signature: str

class AgentResponse(BaseModel):
    id: str
    name: str
    trust_score: float
    status: str
    capabilities: list
    public_key: str
    private_key: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/register")
def register_agent(
    data: AgentCreate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Register a new agent and generate its cryptographic identity"""
    keypair = CryptoEngine.generate_keypair()

    agent = Agent(
        name=data.name,
        org_id=org.id,
        public_key=keypair["public_key"],
        capabilities=data.capabilities,
        trust_score=100.0,
        status="active"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "trust_score": agent.trust_score,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "public_key": keypair["public_key"],
        "private_key": keypair["private_key"],
        "message": "Store private key securely — never share it!"
    }

@router.get("/list")
def list_agents(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """List all agents for an organization"""
    agents = db.query(Agent).filter(Agent.org_id == org.id).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "trust_score": a.trust_score,
            "status": a.status,
            "capabilities": a.capabilities,
            "last_seen": a.last_seen,
            "created_at": a.created_at
        }
        for a in agents
    ]

@router.get("/{agent_id}")
def get_agent(
    agent_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Get a single agent's details and trust score"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.org_id == org.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    recent_behaviors = db.query(BehaviorLog).filter(
        BehaviorLog.agent_id == agent_id
    ).order_by(BehaviorLog.timestamp.desc()).limit(20).all()

    return {
        "id": agent.id,
        "name": agent.name,
        "trust_score": agent.trust_score,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "last_seen": agent.last_seen,
        "recent_behaviors": [
            {
                "action": b.action,
                "is_anomaly": b.is_anomaly,
                "anomaly_score": b.anomaly_score,
                "timestamp": b.timestamp
            }
            for b in recent_behaviors
        ]
    }

@router.post("/{agent_id}/behavior")
def log_behavior(
    agent_id: str,
    event: BehaviorEvent,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Log a behavior event and update trust score in real time"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.org_id == org.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Score the behavior using ML engine
    result = trust_engine.score_behavior(agent_id, event.action, event.payload)

    # Log it
    log = BehaviorLog(
        agent_id=agent_id,
        action=event.action,
        payload_hash=CryptoEngine.hash_payload(event.payload),
        is_anomaly=result["is_anomaly"],
        anomaly_score=result["anomaly_score"],
        metadata={"reason": result["reason"]}
    )
    db.add(log)

    # Update trust score
    new_trust = trust_engine.calculate_trust_score(agent.trust_score, result)
    agent.trust_score = new_trust
    agent.status = trust_engine.get_status(new_trust)
    agent.last_seen = datetime.utcnow()

    # Train ML model every 20 behavior logs
    total_logs = db.query(BehaviorLog).filter(BehaviorLog.agent_id == agent_id).count()
    if total_logs % 20 == 0:
        all_logs = db.query(BehaviorLog).filter(
            BehaviorLog.agent_id == agent_id
        ).all()
        logs_data = [
            {
                "hour": l.timestamp.hour,
                "action": l.action,
                "anomaly_score": l.anomaly_score,
                "payload_size": 0
            }
            for l in all_logs
        ]
        trust_engine.train_baseline(agent_id, logs_data)

    db.commit()

    return {
        "agent_id": agent_id,
        "action": event.action,
        "is_anomaly": result["is_anomaly"],
        "anomaly_score": result["anomaly_score"],
        "new_trust_score": new_trust,
        "status": agent.status,
        "reason": result["reason"]
    }

@router.post("/verify-interaction")
def verify_interaction(
    data: InteractionRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Verify a signed message between two agents"""
    sender = db.query(Agent).filter(
        Agent.id == data.sender_id,
        Agent.org_id == org.id
    ).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender agent not found")

    if sender.status == "suspended":
        raise HTTPException(status_code=403, detail="Sender agent is suspended")

    # Verify cryptographic signature
    is_valid = CryptoEngine.verify_signature(
        sender.public_key,
        data.message,
        data.signature
    )

    # Log the interaction
    interaction = AgentInteraction(
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        message_hash=CryptoEngine.hash_payload(data.message),
        signature=data.signature,
        is_verified=is_valid,
        trust_score_at_time=sender.trust_score
    )
    db.add(interaction)
    db.commit()

    return {
        "is_verified": is_valid,
        "sender_trust_score": sender.trust_score,
        "sender_status": sender.status,
        "message_hash": CryptoEngine.hash_payload(data.message),
        "safe_to_proceed": is_valid and sender.trust_score >= 50
    }

@router.get("/{agent_id}/audit-trail")
def get_audit_trail(
    agent_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Get full tamper-proof audit trail for an agent"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.org_id == org.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    behaviors = db.query(BehaviorLog).filter(
        BehaviorLog.agent_id == agent_id
    ).order_by(BehaviorLog.timestamp.desc()).limit(100).all()

    interactions = db.query(AgentInteraction).filter(
        AgentInteraction.sender_id == agent_id
    ).order_by(AgentInteraction.timestamp.desc()).limit(100).all()

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "current_trust_score": agent.trust_score,
        "current_status": agent.status,
        "behavior_logs": [
            {
                "action": b.action,
                "payload_hash": b.payload_hash,
                "is_anomaly": b.is_anomaly,
                "anomaly_score": b.anomaly_score,
                "timestamp": b.timestamp
            }
            for b in behaviors
        ],
        "interaction_logs": [
            {
                "receiver_id": i.receiver_id,
                "message_hash": i.message_hash,
                "is_verified": i.is_verified,
                "trust_score_at_time": i.trust_score_at_time,
                "timestamp": i.timestamp
            }
            for i in interactions
        ]
    }