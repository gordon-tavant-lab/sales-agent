"""Domain profiles: pillar weight priors + metric trees + normalization targets.

Shared by the deterministic chain. Domain-agnostic by design; degrades into fintech.
Targets are the value at which a metric's normalized subscore reaches ~1.0 (saturation).
Direction "-" means lower-is-better (normalizer inverts). Rates are already in [0,1].

Edit here to add a domain or tune a vertical. Keep keys in sync with references/schema.md.
"""
from typing import Dict, Any

# Each pillar metric: (target, direction) where direction in {"+","-","rate"}.
# "rate": already in [0,1], used directly (or x/target if target<1 given).
PROFILES: Dict[str, Dict[str, Any]] = {
    "fintech": {
        "weights": {"adoption": 0.30, "sentiment": 0.20, "revenue": 0.35, "competitive": 0.15},
        "metric_targets": {
            "adoption": {"mau": (50000, "+"), "wau": (25000, "+"), "new_signups": (6000, "+"),
                         "activation_rate": (1.0, "rate"), "retention_d30": (1.0, "rate")},
            "sentiment": {"nps": (60, "+"), "review_avg": (5.0, "+"), "social_mentions": (1500, "+"),
                          "sentiment_score": (1.0, "rate")},
            "revenue": {"mrr": (200000, "+"), "arpu": (60, "+"), "paid_conversion": (1.0, "rate"),
                        "churn_rate": (0.02, "-")},
            "competitive": {"share_of_voice": (1.0, "rate"), "win_rate": (1.0, "rate"),
                            "category_rank": (1, "-")},
        },
    },
    "saas": {
        "weights": {"adoption": 0.35, "sentiment": 0.15, "revenue": 0.35, "competitive": 0.15},
        "metric_targets": {
            "adoption": {"mau": (40000, "+"), "wau": (20000, "+"), "new_signups": (5000, "+"),
                         "activation_rate": (1.0, "rate"), "retention_d30": (1.0, "rate")},
            "sentiment": {"nps": (50, "+"), "review_avg": (5.0, "+"), "social_mentions": (1000, "+"),
                          "sentiment_score": (1.0, "rate")},
            "revenue": {"mrr": (250000, "+"), "arpu": (80, "+"), "paid_conversion": (1.0, "rate"),
                        "churn_rate": (0.03, "-")},
            "competitive": {"share_of_voice": (1.0, "rate"), "win_rate": (1.0, "rate"),
                            "category_rank": (1, "-")},
        },
    },
    "marketplace": {
        "weights": {"adoption": 0.40, "sentiment": 0.20, "revenue": 0.25, "competitive": 0.15},
        "metric_targets": {
            "adoption": {"mau": (100000, "+"), "wau": (50000, "+"), "new_signups": (12000, "+"),
                         "activation_rate": (1.0, "rate"), "retention_d30": (1.0, "rate")},
            "sentiment": {"nps": (45, "+"), "review_avg": (5.0, "+"), "social_mentions": (3000, "+"),
                          "sentiment_score": (1.0, "rate")},
            "revenue": {"mrr": (300000, "+"), "arpu": (25, "+"), "paid_conversion": (1.0, "rate"),
                        "churn_rate": (0.05, "-")},
            "competitive": {"share_of_voice": (1.0, "rate"), "win_rate": (1.0, "rate"),
                            "category_rank": (1, "-")},
        },
    },
    "media": {
        "weights": {"adoption": 0.40, "sentiment": 0.30, "revenue": 0.15, "competitive": 0.15},
        "metric_targets": {
            "adoption": {"mau": (200000, "+"), "wau": (100000, "+"), "new_signups": (20000, "+"),
                         "activation_rate": (1.0, "rate"), "retention_d30": (1.0, "rate")},
            "sentiment": {"nps": (40, "+"), "review_avg": (5.0, "+"), "social_mentions": (8000, "+"),
                          "sentiment_score": (1.0, "rate")},
            "revenue": {"mrr": (150000, "+"), "arpu": (10, "+"), "paid_conversion": (1.0, "rate"),
                        "churn_rate": (0.06, "-")},
            "competitive": {"share_of_voice": (1.0, "rate"), "win_rate": (1.0, "rate"),
                            "category_rank": (1, "-")},
        },
    },
    "enterprise-b2b": {
        "weights": {"adoption": 0.25, "sentiment": 0.15, "revenue": 0.40, "competitive": 0.20},
        "metric_targets": {
            "adoption": {"mau": (10000, "+"), "wau": (5000, "+"), "new_signups": (800, "+"),
                         "activation_rate": (1.0, "rate"), "retention_d30": (1.0, "rate")},
            "sentiment": {"nps": (55, "+"), "review_avg": (5.0, "+"), "social_mentions": (400, "+"),
                          "sentiment_score": (1.0, "rate")},
            "revenue": {"mrr": (500000, "+"), "arpu": (2000, "+"), "paid_conversion": (1.0, "rate"),
                        "churn_rate": (0.015, "-")},
            "competitive": {"share_of_voice": (1.0, "rate"), "win_rate": (1.0, "rate"),
                            "category_rank": (1, "-")},
        },
    },
}

PILLARS = ["adoption", "sentiment", "revenue", "competitive"]
# Health metrics watched by the Goodhart guard (pillar, metric_key).
HEALTH_METRICS = [("sentiment", "sentiment_score"), ("adoption", "retention_d30")]


def get_profile(name: str) -> Dict[str, Any]:
    if name not in PROFILES:
        raise ValueError(
            "unknown domain_profile '{}'; known: {}".format(name, ", ".join(sorted(PROFILES)))
        )
    return PROFILES[name]
