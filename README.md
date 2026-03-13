# TrustAgent

TrustAgent is a security and trust monitoring system for AI agents. It helps developers track agent behavior, detect anomalies, and maintain secure AI operations in production.

Go from zero to production-secure in under 30 minutes.

---

## Installation

Install the Python SDK using pip.

```bash
pip install trustagent
```

---

## Quick Start

```python
from trustagent import TrustAgent

# Initialize client
ta = TrustAgent(api_key="your_api_key")

# Register a new agent
agent = ta.register("MyAgent", description="My first agent")

# Log an action performed by the agent
result = agent.log("process_request", {"user": "alice"})

print(result.trust_score)    # 100.0
print(result.is_anomalous)   # False
print(result.status)         # active
```

---

## Authentication

All API calls require your organization API key passed in the `x-api-key` header.

You can get your API key from the TrustAgent dashboard after signing up.

Example header:

```
x-api-key: YOUR_API_KEY
```

Best practices:

* Store your API key as an environment variable
* Never hardcode API keys in your codebase

Example:

```bash
export TRUSTAGENT_API_KEY="your_api_key"
```

---

## SDK Reference

### TrustAgent(api_key)

Initializes the TrustAgent client with your API key.

The client is thread-safe and can be shared across your application.

---

### ta.register(name, description)

Registers a new agent with your organization.

Returns an Agent object containing:

* Unique agent ID
* Ed25519 cryptographic keypair

Each agent registered with TrustAgent is cryptographically unique.

Example:

```python
agent = ta.register("MyAgent", description="My first agent")
```

---

### agent.log(action, payload)

Logs a behavior event for the agent.

You should call this before every significant action your AI agent performs.

Returns an object containing:

* `trust_score`
* `is_anomalous`
* `status`
* `is_safe`
* `reason`

Example:

```python
result = agent.log("process_request", {"user": "alice"})
```

---

### agent.audit_trail()

Retrieves the full behavior history for the agent.

Returns a list of logged events including:

* timestamps
* trust scores
* anomaly results
* reasons

Example:

```python
events = agent.audit_trail()
```

---

### agent.refresh()

Fetch the latest agent state from the API including current trust score and status.

Example:

```python
agent.refresh()
```

---

## REST API

The TrustAgent REST API is available at:

```
https://trustagent-production.up.railway.app
```

Interactive Swagger documentation:

```
https://trustagent-production.up.railway.app/docs
```

---

## Framework Integration Guides

TrustAgent can be integrated with popular AI agent frameworks.

LangChain
Wrap your tools with `agent.log()` calls.

CrewAI
Add TrustAgent logging in crew task callbacks.

AutoGen
Integrate using message interceptor hooks.

OpenAI Agents
Add TrustAgent logging to function call handlers.

---

## Example Architecture

```
AI Agent
   │
   │ agent.log()
   ▼
TrustAgent SDK
   │
   ▼
TrustAgent API
   │
   ▼
Trust Scoring + Anomaly Detection
```

---

## License

© 2026 TrustAgent
