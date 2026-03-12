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
import uuid

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    capabilities: List[str] = []


class BehaviorEvent(BaseModel):
    action_type: str
    payload: dict = {}


class InteractionRequest(BaseModel):
    sender_id: str
    receiver_id: str
    message: str
    signature: str


@router.post("/register")
def register_agent(
    data: AgentCreate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    keypair = CryptoEngine.generate_keypair()

    agent = Agent(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        organization_id=org.id,
        public_key=keypair["public_key"],
        private_key=keypair["private_key"],
        trust_score=100.0,
        status="active",
        total_actions=0,
        anomaly_count=0
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    return {
        "agent_id": agent.id,
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "trust_score": agent.trust_score,
        "status": agent.status,
        "public_key": keypair["public_key"],
        "private_key": keypair["private_key"],
        "message": "Store private key securely — never share it!"
    }


@router.get("/list")
def list_agents(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    agents = db.query(Agent).filter(
        Agent.organization_id == org.id
    ).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "trust_score": a.trust_score,
            "status": a.status,
            "total_actions": a.total_actions,
            "anomaly_count": a.anomaly_count,
            "last_active": a.last_active,
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
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == org.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    recent_behaviors = db.query(BehaviorLog).filter(
        BehaviorLog.agent_id == agent_id
    ).order_by(BehaviorLog.timestamp.desc()).limit(20).all()

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "trust_score": agent.trust_score,
        "status": agent.status,
        "total_actions": agent.total_actions,
        "anomaly_count": agent.anomaly_count,
        "last_active": agent.last_active,
        "created_at": agent.created_at,
        "recent_behaviors": [
            {
                "action_type": b.action_type,
                "is_anomalous": b.is_anomalous,
                "anomaly_score": b.anomaly_score,
                "trust_score_after": b.trust_score_after,
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
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == org.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Score with ML engine
    result = trust_engine.score_behavior(agent_id, event.action_type, event.payload)

    trust_before = agent.trust_score

    # Log behavior
    log = BehaviorLog(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        action_type=event.action_type,
        payload_hash=CryptoEngine.hash_payload(event.payload),
        trust_score_before=trust_before,
        is_anomalous=result["is_anomaly"],
        anomaly_score=result["anomaly_score"],
        extra_data=json.dumps({"reason": result.get("reason", "")})
    )
    db.add(log)

    # Update trust score
    new_trust = trust_engine.calculate_trust_score(agent.trust_score, result)
    agent.trust_score = new_trust
    agent.trust_score_after = new_trust
    log.trust_score_after = new_trust
    agent.status = trust_engine.get_status(new_trust)
    agent.last_active = datetime.utcnow()
    agent.total_actions = (agent.total_actions or 0) + 1
    if result["is_anomaly"]:
        agent.anomaly_count = (agent.anomaly_count or 0) + 1

    # Retrain ML model every 20 logs
    total_logs = db.query(BehaviorLog).filter(
        BehaviorLog.agent_id == agent_id
    ).count()
    if total_logs > 0 and total_logs % 20 == 0:
        all_logs = db.query(BehaviorLog).filter(
            BehaviorLog.agent_id == agent_id
        ).all()
        logs_data = [
            {
                "hour": l.timestamp.hour,
                "action": l.action_type,
                "anomaly_score": l.anomaly_score or 0,
                "payload_size": 0
            }
            for l in all_logs
        ]
        trust_engine.train_baseline(agent_id, logs_data)

    db.commit()

    return {
        "agent_id": agent_id,
        "action_type": event.action_type,
        "is_anomalous": result["is_anomaly"],
        "anomaly_score": result["anomaly_score"],
        "trust_score_before": trust_before,
        "trust_score": new_trust,
        "status": agent.status,
        "message": result.get("reason", "")
    }


@router.post("/verify-interaction")
def verify_interaction(
    data: InteractionRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    sender = db.query(Agent).filter(
        Agent.id == data.sender_id,
        Agent.organization_id == org.id
    ).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender agent not found")

    if sender.status == "suspended":
        raise HTTPException(status_code=403, detail="Sender agent is suspended")

    is_valid = CryptoEngine.verify_signature(
        sender.public_key,
        data.message,
        data.signature
    )

    interaction = AgentInteraction(
        id=str(uuid.uuid4()),
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        message_hash=CryptoEngine.hash_payload({"message": data.message}),
        signature=data.signature,
        verified=is_valid,
        trust_score_at_time=sender.trust_score
    )
    db.add(interaction)
    db.commit()

    return {
        "verified": is_valid,
        "sender_trust_score": sender.trust_score,
        "sender_status": sender.status,
        "safe_to_proceed": is_valid and sender.trust_score >= 50
    }


@router.get("/{agent_id}/audit-trail")
def get_audit_trail(
    agent_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == org.id
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
                "action_type": b.action_type,
                "payload_hash": b.payload_hash,
                "is_anomalous": b.is_anomalous,
                "anomaly_score": b.anomaly_score,
                "trust_score_before": b.trust_score_before,
                "trust_score_after": b.trust_score_after,
                "timestamp": b.timestamp
            }
            for b in behaviors
        ],
        "interaction_logs": [
            {
                "receiver_id": i.receiver_id,
                "message_hash": i.message_hash,
                "verified": i.verified,
                "trust_score_at_time": i.trust_score_at_time,
                "timestamp": i.timestamp
            }
            for i in interactions
        ]
    }