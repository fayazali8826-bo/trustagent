import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
from typing import List, Dict
import json

class TrustEngine:

    def __init__(self):
        self.models = {}  # per-agent ML models
        self.baselines = {}  # per-agent behavior baselines

    def extract_features(self, behavior_logs: List[Dict]) -> np.ndarray:
        """Extract ML features from behavior logs"""
        if not behavior_logs:
            return np.array([])

        features = []
        for log in behavior_logs:
            hour = log.get("hour", 12)
            action_hash = hash(log.get("action", "")) % 1000
            anomaly_score = log.get("anomaly_score", 0.0)
            payload_size = log.get("payload_size", 0)
            features.append([hour, action_hash, anomaly_score, payload_size])

        return np.array(features)

    def train_baseline(self, agent_id: str, behavior_logs: List[Dict]):
        """Train isolation forest on agent's normal behavior"""
        features = self.extract_features(behavior_logs)

        if len(features) < 10:
            self.baselines[agent_id] = {"trained": False, "samples": len(features)}
            return

        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(features)
        self.models[agent_id] = model
        self.baselines[agent_id] = {"trained": True, "samples": len(features)}

    def score_behavior(self, agent_id: str, action: str, payload: dict) -> Dict:
        """Score a single behavior event — returns anomaly score + trust impact"""
        features = np.array([[
            datetime.utcnow().hour,
            hash(action) % 1000,
            0.0,
            len(json.dumps(payload))
        ]])

        if agent_id not in self.models:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "trust_impact": 0.0,
                "reason": "baseline_building"
            }

        model = self.models[agent_id]
        score = model.decision_function(features)[0]
        prediction = model.predict(features)[0]
        is_anomaly = prediction == -1
        normalized_score = max(0.0, min(1.0, (score + 0.5) * -1))

        return {
            "anomaly_score": float(normalized_score),
            "is_anomaly": bool(is_anomaly),
            "trust_impact": float(-normalized_score * 10) if is_anomaly else 1.0,
            "reason": "anomaly_detected" if is_anomaly else "normal"
        }

    def calculate_trust_score(self, current_score: float, behavior_result: Dict) -> float:
        """Update agent trust score based on behavior"""
        trust_impact = behavior_result.get("trust_impact", 0.0)

        if behavior_result.get("is_anomaly"):
            new_score = max(0.0, current_score + trust_impact)
        else:
            # Slowly recover trust over time for good behavior
            new_score = min(100.0, current_score + 0.1)

        return round(new_score, 2)

    def get_status(self, trust_score: float) -> str:
        """Convert trust score to status label"""
        if trust_score >= 80:
            return "active"
        elif trust_score >= 50:
            return "warning"
        elif trust_score >= 20:
            return "breach"
        else:
            return "suspended"

# Global instance
trust_engine = TrustEngine()