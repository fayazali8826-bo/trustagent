"""
TrustAgent SDK Exceptions
"""


class TrustAgentError(Exception):
    """Base exception for all TrustAgent errors."""
    pass


class AuthenticationError(TrustAgentError):
    """Raised when API key is invalid or missing."""
    pass


class AgentNotFoundError(TrustAgentError):
    """Raised when agent ID does not exist."""
    pass


class AnomalyDetectedError(TrustAgentError):
    """
    Raised when an agent behavior is flagged as anomalous.
    Can be used to halt execution when anomalies are detected.

    Example:
        try:
            result = agent.log("send_email", payload={"to": "user@example.com"})
            if result.is_anomalous:
                raise AnomalyDetectedError(f"Anomaly detected for {agent.name}")
        except AnomalyDetectedError as e:
            alert_security_team(str(e))
    """
    pass


class RateLimitError(TrustAgentError):
    """Raised when API rate limit is exceeded."""
    pass


class InsufficientTrustError(TrustAgentError):
    """
    Raised when an agent's trust score is too low to proceed.

    Example:
        if not agent.is_trusted:
            raise InsufficientTrustError(
                f"{agent.name} trust score {agent.trust_score:.1f} is below threshold"
            )
    """
    pass