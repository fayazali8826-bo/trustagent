"""
TrustAgent Python SDK
Cryptographic identity + behavioral ML trust verification for AI agents.
"""

from .client import TrustAgent
from .agent import Agent
from .exceptions import TrustAgentError, AuthenticationError, AgentNotFoundError, AnomalyDetectedError

__version__ = "0.1.0"
__all__ = ["TrustAgent", "Agent", "TrustAgentError", "AuthenticationError", "AgentNotFoundError", "AnomalyDetectedError"]