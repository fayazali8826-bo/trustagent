from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    agents = relationship("Agent", back_populates="organization")

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"))
    public_key = Column(Text, nullable=False)
    capabilities = Column(JSON, default=list)
    trust_score = Column(Float, default=100.0)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    organization = relationship("Organization", back_populates="agents")
    behaviors = relationship("BehaviorLog", back_populates="agent")
    interactions = relationship("AgentInteraction", back_populates="sender")

class BehaviorLog(Base):
    __tablename__ = "behavior_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"))
    action = Column(String, nullable=False)
    payload_hash = Column(String)
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, default=dict)
    agent = relationship("Agent", back_populates="behaviors")

class AgentInteraction(Base):
    __tablename__ = "agent_interactions"
    id = Column(String, primary_key=True, default=generate_uuid)
    sender_id = Column(String, ForeignKey("agents.id"))
    receiver_id = Column(String)
    message_hash = Column(String, nullable=False)
    signature = Column(Text, nullable=False)
    is_verified = Column(Boolean, default=False)
    trust_score_at_time = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    payload = Column(JSON, default=dict)
    sender = relationship("Agent", back_populates="interactions")