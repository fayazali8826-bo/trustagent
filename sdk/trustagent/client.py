"""
TrustAgent Client — main entry point for the SDK.
"""

import requests
from typing import Optional, Dict, Any
from .agent import Agent
from .exceptions import TrustAgentError, AuthenticationError, AgentNotFoundError


class TrustAgent:
    """
    TrustAgent client for managing agent trust verification.

    Usage:
        from trustagent import TrustAgent

        ta = TrustAgent(api_key="your_api_key")

        # Register an agent
        agent = ta.register("PaymentBot", description="Handles payments")

        # Log a behavior and get trust score
        result = agent.log("process_payment", payload={"amount": 100})
        print(f"Trust score: {result.trust_score}")
    """

    BASE_URL = "https://trustagent-production.up.railway.app"

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise AuthenticationError("API key is required.")

        self.api_key = api_key
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "trustagent-python/0.1.0"
        })

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated API request."""
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.ConnectionError:
            raise TrustAgentError("Could not connect to TrustAgent API. Check your internet connection.")
        except requests.Timeout:
            raise TrustAgentError("Request timed out. Try again.")

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key. Check your credentials.")
        if response.status_code == 404:
            raise AgentNotFoundError("Agent not found.")
        if response.status_code == 429:
            raise TrustAgentError("Rate limit exceeded. Slow down requests.")
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise TrustAgentError(f"API error {response.status_code}: {detail}")

        return response.json()

    def register(self, name: str, description: str = "") -> "Agent":
        """
        Register a new agent in the trust network.

        Args:
            name: Agent name (e.g. "PaymentBot")
            description: What this agent does

        Returns:
            Agent instance ready to log behaviors
        """
        data = self._request("POST", "/api/agents/register", json={
            "name": name,
            "description": description,
            "capabilities": []
        })
        return Agent(client=self, data=data)

    def get(self, agent_id: str) -> "Agent":
        """
        Get an existing agent by ID.

        Args:
            agent_id: The agent's UUID

        Returns:
            Agent instance
        """
        data = self._request("GET", f"/api/agents/{agent_id}")
        return Agent(client=self, data=data)

    def list(self):
        """
        List all agents in your organization.

        Returns:
            List of Agent instances
        """
        data = self._request("GET", "/api/agents/list")
        return [Agent(client=self, data=a) for a in data]

    def verify_interaction(self, sender_id: str, receiver_id: str, message: str, signature: str) -> bool:
        """
        Cryptographically verify an agent-to-agent interaction.

        Args:
            sender_id: ID of the agent that sent the message
            receiver_id: ID of the agent receiving the message
            message: The message content
            signature: Cryptographic signature from sender

        Returns:
            True if interaction is verified and safe to proceed
        """
        data = self._request("POST", "/api/agents/verify-interaction", json={
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message,
            "signature": signature
        })
        return data.get("verified", False)

    def health(self) -> bool:
        """Check if the TrustAgent API is reachable."""
        try:
            data = self._request("GET", "/health")
            return data.get("status") == "healthy"
        except Exception:
            return False