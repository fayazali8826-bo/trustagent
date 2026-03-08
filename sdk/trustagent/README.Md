# TrustAgent Python SDK

**Cryptographic identity + behavioral ML trust verification for AI agents.**

```bash
pip install trustagent
```

## Quick Start

```python
from trustagent import TrustAgent

# Initialize with your API key
ta = TrustAgent(api_key="your_api_key_here")

# Register an agent
agent = ta.register("PaymentBot", description="Handles payment processing")
print(agent)  # ✅ PaymentBot | Trust: 100.0 | Status: active

# Log behaviors — ML scores each action in real time
result = agent.log("process_payment", payload={"amount": 100, "currency": "USD"})
print(f"Trust score: {result.trust_score}")
print(f"Anomaly detected: {result.is_anomalous}")

# Check if safe to proceed
if result.is_safe:
    proceed_with_action()
else:
    alert_security_team()
```

## Use Cases

### Multi-Agent Trust Verification
```python
from trustagent import TrustAgent, InsufficientTrustError

ta = TrustAgent(api_key="your_api_key")

# Agent A wants to send a task to Agent B
agent_a = ta.get("agent-a-id")
agent_b = ta.get("agent-b-id")

# Before Agent B acts on Agent A's request, verify trust
agent_a.refresh()
if not agent_a.is_trusted:
    raise InsufficientTrustError(f"{agent_a.name} trust too low: {agent_a.trust_score:.1f}")

# Log the interaction
result = agent_b.log("execute_task_from_agent_a", payload={"task": "send_invoice"})
if result.is_anomalous:
    print(f"⚠ Anomaly detected! Trust dropped to {result.trust_score:.1f}")
```

### LangChain Integration
```python
from langchain.agents import Tool
from trustagent import TrustAgent

ta = TrustAgent(api_key="your_api_key")
agent = ta.register("LangChainAgent")

def trusted_tool_call(action: str) -> str:
    result = agent.log(action)
    if not result.is_safe:
        return f"Action blocked: trust score {result.trust_score:.1f}"
    # proceed with tool call
    return execute_tool(action)

tool = Tool(name="TrustedAction", func=trusted_tool_call, description="Execute with trust verification")
```

### CrewAI Integration
```python
from crewai import Agent as CrewAgent
from trustagent import TrustAgent

ta = TrustAgent(api_key="your_api_key")
trust_agent = ta.register("CrewAIResearcher")

class TrustedCrewAgent(CrewAgent):
    def execute_task(self, task):
        result = trust_agent.log("execute_task", payload={"task": str(task)})
        if result.is_anomalous:
            raise Exception(f"Trust violation detected: {result.trust_score:.1f}")
        return super().execute_task(task)
```

### AutoGen Integration
```python
import autogen
from trustagent import TrustAgent

ta = TrustAgent(api_key="your_api_key")
trust_agent = ta.register("AutoGenAssistant")

class TrustedAssistantAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender):
        trust_agent.log("generate_reply", payload={"message_count": len(messages)})
        return super().generate_reply(messages, sender)
```

## API Reference

### `TrustAgent(api_key, base_url=None)`
Main client class.

| Method | Description |
|--------|-------------|
| `ta.register(name, description)` | Register a new agent |
| `ta.get(agent_id)` | Get existing agent by ID |
| `ta.list()` | List all agents |
| `ta.verify_interaction(sender_id, receiver_id, message, signature)` | Verify agent-to-agent message |
| `ta.health()` | Check API connectivity |

### `Agent`

| Method/Property | Description |
|-----------------|-------------|
| `agent.log(action_type, payload)` | Log behavior, get trust score |
| `agent.audit_trail(limit)` | Get behavior history |
| `agent.refresh()` | Update agent data from API |
| `agent.sign(message)` | Sign message with agent's private key |
| `agent.is_trusted` | True if trust score ≥ 80 |
| `agent.is_suspended` | True if agent is suspended |
| `agent.trust_score` | Current trust score (0-100) |
| `agent.status` | active / warning / breach / suspended |

### `BehaviorResult`

| Property | Description |
|----------|-------------|
| `result.trust_score` | Updated trust score after action |
| `result.is_anomalous` | True if ML flagged as anomaly |
| `result.is_safe` | True if normal and trust ≥ 50 |
| `result.anomaly_score` | Raw anomaly score from ML model |

## Exceptions

```python
from trustagent import (
    TrustAgentError,        # Base exception
    AuthenticationError,    # Invalid API key
    AgentNotFoundError,     # Agent ID not found
    AnomalyDetectedError,   # Behavior flagged as anomaly
    InsufficientTrustError, # Trust score too low
)
```

## Get Your API Key

Sign up free at **https://trustagent-production.up.railway.app**

## License

MIT