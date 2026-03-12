from trustagent import TrustAgent

ta = TrustAgent(api_key="W90pWspvdiG2VuyJSSWYWO7xbnVsKquU9m8o18YGJd0")

print("=== TrustAgent ML Engine Test ===\n")

# Register a fresh agent
agent = ta.register("SecurityTestBot", description="ML engine test")
print(f"Agent created: {agent}")
print(f"Initial trust: {agent.trust_score}\n")

# ── Normal behaviors (should stay safe)
print("--- Normal behaviors ---")
for i in range(5):
    result = agent.log("read_database", payload={"table": "users", "limit": 10})
    print(f"read_database → Trust: {result.trust_score} | Anomaly: {result.is_anomalous} | {result.message}")

# ── Suspicious behavior
print("\n--- Suspicious behaviors ---")

result = agent.log("delete_all", payload={"table": "users"})
print(f"delete_all → Trust: {result.trust_score} | Anomaly: {result.is_anomalous} | {result.message}")

result = agent.log("send_funds", payload={"amount": 99999, "to": "unknown_account"})
print(f"send_funds $99999 → Trust: {result.trust_score} | Anomaly: {result.is_anomalous} | {result.message}")

result = agent.log("external_call", payload={"url": "http://suspicious-site.com"})
print(f"external_call → Trust: {result.trust_score} | Anomaly: {result.is_anomalous} | {result.message}")

# ── Frequency explosion
print("\n--- Frequency explosion (10 rapid calls) ---")
for i in range(10):
    result = agent.log("bulk_export", payload={"records": 10000})
print(f"After rapid calls → Trust: {result.trust_score} | Status: {result.status}")

print(f"\nFinal agent status: {agent.refresh()}")