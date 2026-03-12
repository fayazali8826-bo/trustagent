from trustagent import TrustAgent

ta = TrustAgent(api_key="W90pWspvdiG2VuyJSSWYWO7xbnVsKquU9m8o18YGJd0")
print("Connected:", ta.health())

agent = ta.register("TestBot", description="SDK test")
print(agent)

result = agent.log("send_email", payload={"to": "test@test.com"})
print(f"Trust: {result.trust_score}")
print(f"Anomaly: {result.is_anomalous}")