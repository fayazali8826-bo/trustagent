from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    company = Column(String, default="")
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    organizations = relationship("Organization", back_populates="owner")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    agents = relationship("Agent", back_populates="organization")
    owner = relationship("User", back_populates="organizations")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    public_key = Column(Text, nullable=True)
    private_key = Column(Text, nullable=True)
    trust_score = Column(Float, default=100.0)
    status = Column(String, default="active")   # active, warning, breach, suspended
    total_actions = Column(Integer, default=0)
    anomaly_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="agents")
    behavior_logs = relationship("BehaviorLog", back_populates="agent")
    sent_interactions = relationship(
        "AgentInteraction",
        foreign_keys="AgentInteraction.sender_id",
        back_populates="sender"
    )
    received_interactions = relationship(
        "AgentInteraction",
        foreign_keys="AgentInteraction.receiver_id",
        back_populates="receiver"
    )


class BehaviorLog(Base):
    __tablename__ = "behavior_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    action_type = Column(String, nullable=False)
    payload_hash = Column(String, nullable=True)
    trust_score_before = Column(Float, nullable=True)
    trust_score_after = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    is_anomalous = Column(Boolean, default=False)
    extra_data = Column(Text, nullable=True)   # JSON string for additional metadata
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="behavior_logs")


class AgentInteraction(Base):
    __tablename__ = "agent_interactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    sender_id = Column(String, ForeignKey("agents.id"), nullable=False)
    receiver_id = Column(String, ForeignKey("agents.id"), nullable=False)
    message_hash = Column(String, nullable=True)
    signature = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)
    trust_score_at_time = Column(Float, nullable=True)
    extra_data = Column(Text, nullable=True)   # JSON string for additional metadata
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sender = relationship("Agent", foreign_keys=[sender_id], back_populates="sent_interactions")
    receiver = relationship("Agent", foreign_keys=[receiver_id], back_populates="received_interactions")