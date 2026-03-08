"""
Agent class — represents a single agent in the trust network.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class BehaviorResult:
    """Result from logging an agent behavior."""
    trust_score: float
    trust_score_before: float
    is_anomalous: bool
    anomaly_score: Optional[float]
    status: str
    action_type: str
    message: str

    @property
    def is_safe(self) -> bool:
        """Returns True if behavior is normal and trust is high."""
        return not self.is_anomalous and self.trust_score >= 50

    def __str__(self):
        flag = "⚠ ANOMALY" if self.is_anomalous else "✓ Normal"
        return f"{flag} | Trust: {self.trust_score:.1f} | Action: {self.action_type}"


class Agent:
    """
    Represents a registered TrustAgent agent.

    Don't instantiate directly — use TrustAgent.register() or TrustAgent.get()
    """

    def __init__(self, client, data: Dict[str, Any]):
        self._client = client
        self._data = data
        self.id: str = data.get("agent_id") or data.get("id", "")
        self.name: str = data.get("name", "")
        self.description: str = data.get("description", "")
        self.trust_score: float = data.get("trust_score", 100.0)
        self.status: str = data.get("status", "active")
        self.total_actions: int = data.get("total_actions", 0)
        self.anomaly_count: int = data.get("anomaly_count", 0)
        self.public_key: Optional[str] = data.get("public_key")
        self.private_key: Optional[str] = data.get("private_key")

    def log(self, action_type: str, payload: Optional[Dict] = None) -> BehaviorResult:
        """
        Log a behavior for this agent and get a trust score update.

        Args:
            action_type: What action the agent performed (e.g. "send_email", "process_payment")
            payload: Optional dict with action details (gets hashed for privacy)

        Returns:
            BehaviorResult with updated trust score and anomaly detection

        Example:
            result = agent.log("send_email", payload={"to": "user@example.com", "subject": "Invoice"})
            if result.is_anomalous:
                alert_security_team()
            print(f"Trust score: {result.trust_score}")
        """
        data = self._client._request(
            "POST",
            f"/api/agents/{self.id}/behavior",
            json={
                "action_type": action_type,
                "payload": payload or {}
            }
        )

        # Update local trust score
        self.trust_score = data.get("trust_score", self.trust_score)
        self.status = data.get("status", self.status)

        return BehaviorResult(
            trust_score=data.get("trust_score", 100.0),
            trust_score_before=data.get("trust_score_before", 100.0),
            is_anomalous=data.get("is_anomalous", False),
            anomaly_score=data.get("anomaly_score"),
            status=data.get("status", "active"),
            action_type=action_type,
            message=data.get("message", "")
        )

    def audit_trail(self, limit: int = 50) -> List[Dict]:
        """
        Get the full audit trail for this agent.

        Args:
            limit: Max number of logs to return

        Returns:
            List of behavior log dicts

        Example:
            logs = agent.audit_trail(limit=100)
            for log in logs:
                print(f"{log['timestamp']}: {log['action_type']} - Trust: {log['trust_score_after']}")
        """
        data = self._client._request("GET", f"/api/agents/{self.id}/audit-trail")
        logs = data.get("behavior_logs", [])
        return logs[:limit]

    def refresh(self) -> "Agent":
        """
        Refresh agent data from the API.

        Returns:
            self (updated)

        Example:
            agent.refresh()
            print(f"Current trust: {agent.trust_score}")
        """
        data = self._client._request("GET", f"/api/agents/{self.id}")
        self._data = data
        self.trust_score = data.get("trust_score", self.trust_score)
        self.status = data.get("status", self.status)
        self.total_actions = data.get("total_actions", self.total_actions)
        self.anomaly_count = data.get("anomaly_count", self.anomaly_count)
        return self

    def sign(self, message: str) -> Optional[str]:
        """
        Sign a message with this agent's private key.

        Args:
            message: Message to sign

        Returns:
            Base64-encoded signature, or None if no private key

        Example:
            signature = agent.sign("process_payment:100")
            # Send signature with message to receiver agent
        """
        if not self.private_key:
            return None
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives.serialization import (
                load_pem_private_key, Encoding, PublicFormat
            )
            import base64
            private_key = load_pem_private_key(
                self.private_key.encode(), password=None
            )
            signature = private_key.sign(message.encode())
            return base64.b64encode(signature).decode()
        except Exception:
            return None

    @property
    def is_trusted(self) -> bool:
        """Returns True if agent has a good trust score (≥ 80)."""
        return self.trust_score >= 80 and self.status == "active"

    @property
    def is_suspended(self) -> bool:
        """Returns True if agent has been suspended due to anomalies."""
        return self.status == "suspended"

    def __repr__(self):
        return f"Agent(id={self.id!r}, name={self.name!r}, trust={self.trust_score:.1f}, status={self.status!r})"

    def __str__(self):
        emoji = "✅" if self.is_trusted else "⚠️" if self.status == "warning" else "🚨"
        return f"{emoji} {self.name} | Trust: {self.trust_score:.1f} | Status: {self.status}"