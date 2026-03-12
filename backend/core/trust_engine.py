import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
import json
import math

class TrustEngine:
    """
    Advanced behavioral ML engine for agent trust scoring.

    Detects:
    - Unusual time-of-day activity
    - Payload size spikes
    - Request frequency explosions
    - New unknown action types
    - Large financial amounts
    - Rapid sequential actions
    - Off-hours activity
    - Error rate increases
    - Action sequence anomalies
    - Cross-feature combined anomalies
    """

    # High risk actions that always get extra scrutiny
    HIGH_RISK_ACTIONS = {
        "delete", "drop", "truncate", "remove",
        "send_funds", "transfer_money", "wire_transfer", "process_payment",
        "export_data", "download_all", "bulk_export",
        "create_admin", "grant_permissions", "escalate_privileges",
        "external_call", "webhook", "send_email_bulk",
        "override", "bypass", "disable_security",
        "execute_command", "run_script", "shell_exec"
    }

    # Actions that are low risk
    LOW_RISK_ACTIONS = {
        "read", "get", "list", "view", "fetch",
        "search", "query", "ping", "health_check",
        "log", "monitor", "report"
    }

    def __init__(self):
        self.models: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.baselines: Dict[str, dict] = {}

        # Per-agent behavioral memory
        self.action_history: Dict[str, List[dict]] = defaultdict(list)
        self.action_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.hourly_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.recent_timestamps: Dict[str, List[float]] = defaultdict(list)
        self.known_actions: Dict[str, set] = defaultdict(set)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_counts: Dict[str, int] = defaultdict(int)

    # ── FEATURE EXTRACTION ──────────────────────────────────────────────────

    def extract_features(self, behavior_logs: List[Dict]) -> np.ndarray:
        """Extract rich ML features from a list of behavior logs."""
        if not behavior_logs:
            return np.array([])

        features = []
        for i, log in enumerate(behavior_logs):
            feature_vec = self._extract_single_features(
                action=log.get("action", log.get("action_type", "")),
                payload=log.get("payload", {}),
                hour=log.get("hour", 12),
                agent_id=None,
                log_index=i,
                total_logs=len(behavior_logs)
            )
            features.append(feature_vec)

        return np.array(features)

    def _extract_single_features(
        self,
        action: str,
        payload: dict,
        hour: int,
        agent_id: Optional[str],
        log_index: int = 0,
        total_logs: int = 1
    ) -> List[float]:
        """
        Extract 15 behavioral features from a single action.

        Features:
        1.  hour_of_day          — 0-23, off-hours = suspicious
        2.  is_off_hours         — 1 if outside 6am-10pm
        3.  is_weekend_hour      — proxy for weekend (hour 0-5)
        4.  action_risk_score    — 0=low risk, 1=high risk
        5.  is_new_action        — never seen before for this agent
        6.  payload_size         — bytes in payload JSON
        7.  payload_size_log     — log scale to reduce outlier impact
        8.  payload_depth        — nesting depth of payload
        9.  payload_key_count    — number of keys in payload
        10. has_large_number     — payload contains number > 10000
        11. has_external_url     — payload contains http/url
        12. frequency_last_min   — how many calls in last 60 seconds
        13. frequency_spike      — current freq vs baseline freq
        14. action_repeat_rate   — how often this exact action repeats
        15. error_rate           — proportion of recent errors
        """

        # 1-3. Time features
        hour_of_day = float(hour)
        is_off_hours = 1.0 if (hour < 6 or hour > 22) else 0.0
        is_late_night = 1.0 if (hour >= 0 and hour <= 4) else 0.0

        # 4-5. Action risk features
        action_lower = action.lower()
        action_risk = self._get_action_risk(action_lower)
        is_new_action = 0.0
        if agent_id:
            is_new_action = 0.0 if action in self.known_actions[agent_id] else 1.0

        # 6-9. Payload features
        payload_str = json.dumps(payload) if payload else "{}"
        payload_size = float(len(payload_str))
        payload_size_log = float(math.log1p(payload_size))
        payload_depth = float(self._get_dict_depth(payload))
        payload_key_count = float(len(payload.keys()) if isinstance(payload, dict) else 0)

        # 10-11. Payload content features
        has_large_number = float(self._has_large_number(payload))
        has_external_url = float(self._has_external_url(payload_str))

        # 12-13. Frequency features
        frequency_last_min = 0.0
        frequency_spike = 0.0
        if agent_id:
            now = datetime.utcnow().timestamp()
            recent = [t for t in self.recent_timestamps[agent_id] if now - t < 60]
            frequency_last_min = float(len(recent))

            # Compare to baseline frequency
            baseline_freq = self.baselines.get(agent_id, {}).get("avg_freq_per_min", 1.0)
            if baseline_freq > 0:
                frequency_spike = min(10.0, frequency_last_min / max(baseline_freq, 0.1))

        # 14. Action repeat rate
        action_repeat_rate = 0.0
        if agent_id:
            total = max(self.total_counts[agent_id], 1)
            action_count = self.action_counts[agent_id].get(action, 0)
            action_repeat_rate = float(action_count / total)

        # 15. Error rate
        error_rate = 0.0
        if agent_id:
            total = max(self.total_counts[agent_id], 1)
            error_rate = float(self.error_counts[agent_id] / total)

        return [
            hour_of_day,
            is_off_hours,
            is_late_night,
            action_risk,
            is_new_action,
            payload_size,
            payload_size_log,
            payload_depth,
            payload_key_count,
            has_large_number,
            has_external_url,
            frequency_last_min,
            frequency_spike,
            action_repeat_rate,
            error_rate,
        ]

    def _get_action_risk(self, action: str) -> float:
        """Score action risk 0.0 (safe) to 1.0 (dangerous)."""
        for high_risk in self.HIGH_RISK_ACTIONS:
            if high_risk in action:
                return 1.0
        for low_risk in self.LOW_RISK_ACTIONS:
            if low_risk in action:
                return 0.0
        return 0.3  # unknown = moderate risk

    def _get_dict_depth(self, d, depth=0) -> int:
        """Get nesting depth of a dict."""
        if not isinstance(d, dict) or not d:
            return depth
        return max(self._get_dict_depth(v, depth + 1) for v in d.values())

    def _has_large_number(self, payload: dict) -> bool:
        """Check if payload contains suspiciously large numbers."""
        if not isinstance(payload, dict):
            return False
        payload_str = json.dumps(payload)
        import re
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', payload_str)
        return any(float(n) > 10000 for n in numbers)

    def _has_external_url(self, payload_str: str) -> bool:
        """Check if payload contains external URLs."""
        return "http://" in payload_str or "https://" in payload_str

    # ── TRAINING ────────────────────────────────────────────────────────────

    def train_baseline(self, agent_id: str, behavior_logs: List[Dict]):
        """Train Isolation Forest on agent's normal behavior patterns."""
        features = self.extract_features(behavior_logs)

        if len(features) < 10:
            self.baselines[agent_id] = {
                "trained": False,
                "samples": len(features),
                "needs_more": 10 - len(features)
            }
            return

        # Calculate baseline statistics
        avg_freq = len(behavior_logs) / max(1, len(set(
            log.get("hour", 12) for log in behavior_logs
        )))

        self.baselines[agent_id] = {
            "trained": True,
            "samples": len(features),
            "avg_freq_per_min": avg_freq,
            "avg_payload_size": float(np.mean([f[5] for f in features])),
            "std_payload_size": float(np.std([f[5] for f in features])),
            "common_hours": list(set(int(f[0]) for f in features)),
        }

        # Scale features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        self.scalers[agent_id] = scaler

        # Train Isolation Forest
        # contamination=0.05 means we expect ~5% of behaviors to be anomalous
        model = IsolationForest(
            contamination=0.05,
            n_estimators=100,
            max_samples="auto",
            random_state=42,
            n_jobs=-1
        )
        model.fit(features_scaled)
        self.models[agent_id] = model

    # ── SCORING ─────────────────────────────────────────────────────────────

    def score_behavior(self, agent_id: str, action: str, payload: dict) -> Dict:
        """
        Score a single behavior. Returns anomaly score + trust impact + reason.

        Always runs rule-based checks first (catches obvious threats even before
        the ML model has enough data). Then runs ML scoring on top.
        """
        now = datetime.utcnow()

        # Update behavioral memory
        self._update_memory(agent_id, action, now)

        # Extract features
        features = self._extract_single_features(
            action=action,
            payload=payload,
            hour=now.hour,
            agent_id=agent_id
        )

        # ── RULE-BASED SCORING (always runs) ──
        rule_result = self._apply_rules(agent_id, action, payload, features, now)

        # If rules already flagged a critical threat, return immediately
        if rule_result["severity"] == "critical":
            return {
                "anomaly_score": 0.95,
                "is_anomaly": True,
                "trust_impact": -25.0,
                "reason": " | ".join(rule_result["flags"]) if rule_result["flags"] else "critical_threat",
                "detection_method": "rule_based",
            }

        # ── ML SCORING ──
        ml_result = self._ml_score(agent_id, features)

        # ── COMBINE RULE + ML ──
        final_score = self._combine_scores(rule_result, ml_result)

        # Determine trust impact
        trust_impact = self._calculate_trust_impact(final_score, rule_result, ml_result)

        # Build reason string
        reasons = []
        if rule_result["flags"]:
            reasons.extend(rule_result["flags"])
        if ml_result["is_anomaly"]:
            reasons.append("ml_pattern_anomaly")
        if not reasons:
            reasons.append("normal_behavior")

        return {
            "anomaly_score": float(final_score),
            "is_anomaly": final_score > 0.5,
            "trust_impact": float(trust_impact),
            "reason": " | ".join(reasons),
            "detection_method": "combined" if ml_result["scored"] else "rule_based",
            "rule_flags": rule_result["flags"],
            "ml_score": ml_result.get("score", 0.0),
            "features": {
                "hour": now.hour,
                "is_off_hours": bool(features[1]),
                "action_risk": features[3],
                "is_new_action": bool(features[4]),
                "payload_size": features[5],
                "has_large_number": bool(features[9]),
                "frequency_last_min": features[11],
                "frequency_spike": features[12],
            }
        }

    def _apply_rules(self, agent_id: str, action: str, payload: dict, features: list, now: datetime) -> Dict:
        """
        Apply deterministic rule-based checks.
        These catch obvious threats immediately, even before ML has enough data.
        """
        flags = []
        severity = "none"

        # Rule 1: High risk action at unusual hour
        if features[3] >= 1.0 and features[1] == 1.0:
            flags.append("high_risk_action_off_hours")
            severity = "high"

        # Rule 2: Frequency explosion (>50 calls/minute)
        if features[11] > 50:
            flags.append(f"frequency_explosion_{int(features[11])}_per_min")
            severity = "critical"

        # Rule 3: Very large payload (>100KB)
        if features[5] > 100000:
            flags.append("massive_payload_size")
            severity = "high"

        # Rule 4: Large financial amounts
        if features[9] == 1.0 and features[3] >= 0.5:
            flags.append("large_financial_amount")
            if severity != "critical":
                severity = "high"

        # Rule 5: New action type + high risk
        if features[4] == 1.0 and features[3] >= 1.0:
            flags.append("unknown_high_risk_action")
            if severity not in ("critical", "high"):
                severity = "medium"

        # Rule 6: External URL in payload
        if features[10] == 1.0:
            flags.append("external_url_in_payload")
            if severity == "none":
                severity = "low"

        # Rule 7: Late night high-risk action
        if features[2] == 1.0 and features[3] >= 0.5:
            flags.append("late_night_sensitive_action")
            if severity == "none":
                severity = "medium"

        # Rule 8: Suspicious action keywords
        action_lower = action.lower()
        for keyword in ["drop", "truncate", "delete_all", "wipe", "destroy"]:
            if keyword in action_lower:
                flags.append(f"destructive_keyword_{keyword}")
                severity = "critical"
                break

        return {
            "flags": flags,
            "severity": severity,
            "score": len(flags) * 0.15 if flags else 0.0
        }

    def _ml_score(self, agent_id: str, features: list) -> Dict:
        """Run ML model scoring if model exists for this agent."""
        if agent_id not in self.models:
            return {"scored": False, "is_anomaly": False, "score": 0.0}

        try:
            features_array = np.array([features])
            scaler = self.scalers.get(agent_id)
            if scaler:
                features_array = scaler.transform(features_array)

            model = self.models[agent_id]
            raw_score = model.decision_function(features_array)[0]
            prediction = model.predict(features_array)[0]

            # Normalize: decision_function returns negative for anomalies
            # More negative = more anomalous
            # Convert to 0-1 scale where 1 = most anomalous
            normalized = float(max(0.0, min(1.0, (-raw_score + 0.2) * 1.5)))

            return {
                "scored": True,
                "is_anomaly": prediction == -1,
                "score": normalized,
                "raw_score": float(raw_score)
            }
        except Exception:
            return {"scored": False, "is_anomaly": False, "score": 0.0}

    def _combine_scores(self, rule_result: Dict, ml_result: Dict) -> float:
        """
        Combine rule-based and ML scores into a final anomaly score.
        Rules are weighted 60%, ML 40% when both available.
        """
        rule_score = min(1.0, rule_result.get("score", 0.0))

        if not ml_result["scored"]:
            return rule_score

        ml_score = ml_result.get("score", 0.0)

        # Weight: rules more important (60/40)
        combined = (rule_score * 0.6) + (ml_score * 0.4)

        # Boost if both agree it's an anomaly
        if rule_score > 0.3 and ml_score > 0.5:
            combined = min(1.0, combined * 1.3)

        return float(combined)

    def _calculate_trust_impact(self, anomaly_score: float, rule_result: Dict, ml_result: Dict) -> float:
        """
        Calculate how much to adjust the trust score.
        Positive = trust increases (good behavior)
        Negative = trust decreases (bad behavior)
        """
        severity = rule_result.get("severity", "none")

        if severity == "critical":
            return -30.0
        elif severity == "high":
            return -15.0
        elif severity == "medium":
            return -8.0
        elif severity == "low":
            return -3.0
        elif anomaly_score > 0.7:
            return -12.0
        elif anomaly_score > 0.5:
            return -6.0
        elif anomaly_score > 0.3:
            return -2.0
        else:
            # Good behavior slowly rebuilds trust
            return +0.5

    # ── TRUST SCORE ─────────────────────────────────────────────────────────

    def calculate_trust_score(self, current_score: float, behavior_result: Dict) -> float:
        """Update agent trust score based on behavior result."""
        trust_impact = behavior_result.get("trust_impact", 0.5)
        new_score = current_score + trust_impact

        # Clamp between 0 and 100
        new_score = max(0.0, min(100.0, new_score))

        return round(new_score, 2)

    def get_status(self, trust_score: float) -> str:
        """Convert trust score to human-readable status."""
        if trust_score >= 80:
            return "active"
        elif trust_score >= 50:
            return "warning"
        elif trust_score >= 20:
            return "breach"
        else:
            return "suspended"

    # ── MEMORY ──────────────────────────────────────────────────────────────

    def _update_memory(self, agent_id: str, action: str, now: datetime):
        """Update per-agent behavioral memory for frequency tracking."""
        # Track timestamps for frequency calculation
        now_ts = now.timestamp()
        self.recent_timestamps[agent_id].append(now_ts)

        # Keep only last 5 minutes of timestamps
        cutoff = now_ts - 300
        self.recent_timestamps[agent_id] = [
            t for t in self.recent_timestamps[agent_id] if t > cutoff
        ]

        # Track action counts
        self.action_counts[agent_id][action] += 1
        self.total_counts[agent_id] += 1

        # Track known actions
        self.known_actions[agent_id].add(action)

        # Track hourly distribution
        self.hourly_counts[agent_id][now.hour] += 1

    def mark_error(self, agent_id: str):
        """Call this when an agent action results in an error."""
        self.error_counts[agent_id] += 1

    # ── INSIGHTS ────────────────────────────────────────────────────────────

    def get_agent_insights(self, agent_id: str) -> Dict:
        """
        Return behavioral insights for an agent.
        Used by dashboard to show why trust score changed.
        """
        baseline = self.baselines.get(agent_id, {})
        total = self.total_counts.get(agent_id, 0)
        known = len(self.known_actions.get(agent_id, set()))
        recent_freq = len([
            t for t in self.recent_timestamps.get(agent_id, [])
            if datetime.utcnow().timestamp() - t < 60
        ])

        # Most common hour of activity
        hourly = self.hourly_counts.get(agent_id, {})
        peak_hour = max(hourly, key=hourly.get) if hourly else None

        return {
            "model_trained": baseline.get("trained", False),
            "training_samples": baseline.get("samples", 0),
            "total_actions": total,
            "unique_action_types": known,
            "current_frequency_per_min": recent_freq,
            "baseline_frequency_per_min": baseline.get("avg_freq_per_min", 0),
            "peak_activity_hour": peak_hour,
            "avg_payload_size": baseline.get("avg_payload_size", 0),
        }


# Global singleton instance
trust_engine = TrustEngine()