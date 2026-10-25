from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib


CATEGORIES = [
    "Routine",
    "Abnormal non-critical",
    "Critical / urgent",
    "Uncertain / manual review",
]

FEATURE_NAMES = [
    "wbc",
    "rbc",
    "hgb",
    "hct",
    "plt",
    "mcv",
    "mch",
    "mchc",
    "rdw",
    "mpv",
    "neutrophils",
    "lymphocytes",
    "monocytes",
    "eosinophils",
    "basophils",
    "flag_normal",
    "flag_abnormal",
    "flag_critical",
    "flag_panic",
    "flag_review",
    "flag_conflict",
    "missing_count",
]

MODEL_PATH = Path(__file__).resolve().parent / "models" / "fbc_triage_model.joblib"
METRICS_PATH = Path(__file__).resolve().parent / "models" / "fbc_triage_metrics.json"

DEFAULT_VALUES = {
    "wbc": 6.5,
    "rbc": 4.7,
    "hgb": 14.0,
    "hct": 42.0,
    "plt": 260.0,
    "mcv": 88.0,
    "mch": 30.0,
    "mchc": 34.0,
    "rdw": 13.0,
    "mpv": 9.5,
    "neutrophils": 3.5,
    "lymphocytes": 2.0,
    "monocytes": 0.5,
    "eosinophils": 0.2,
    "basophils": 0.1,
}


def extract_features(values: dict[str, float | None], analyzer_flags: list[str]) -> list[float]:
    flags = {flag.lower() for flag in analyzer_flags}
    missing_count = sum(1 for name in DEFAULT_VALUES if values.get(name) is None)
    flag_conflict = "normal" in flags and bool({"critical", "panic", "blast_flag"} & flags)

    features = []
    for name, default in DEFAULT_VALUES.items():
        features.append(float(values.get(name) if values.get(name) is not None else default))

    features.extend(
        [
            1.0 if "normal" in flags else 0.0,
            1.0 if "abnormal" in flags else 0.0,
            1.0 if "critical" in flags else 0.0,
            1.0 if "panic" in flags else 0.0,
            1.0 if "review" in flags or "manual_review" in flags else 0.0,
            1.0 if flag_conflict else 0.0,
            float(missing_count),
        ]
    )

    return features


def rule_label(values: dict[str, float | None], analyzer_flags: list[str]) -> str:
    missing = [key for key, value in values.items() if value is None]
    flags = {flag.lower() for flag in analyzer_flags}
    conflict = "normal" in flags and bool({"critical", "panic", "blast_flag"} & flags)

    if missing or conflict or "review" in flags or "manual_review" in flags:
        return "Uncertain / manual review"

    if (
        values["wbc"] < 2.0
        or values["wbc"] > 30.0
        or values["hgb"] < 7.0
        or values["plt"] < 50.0
        or values["neutrophils"] < 1.0
        or "critical" in flags
        or "panic" in flags
    ):
        return "Critical / urgent"

    abnormal = (
        values["wbc"] < 4.0
        or values["wbc"] > 11.0
        or values["rbc"] < 4.0
        or values["rbc"] > 5.9
        or values["hgb"] < 12.0
        or values["hgb"] > 17.5
        or values["hct"] < 36.0
        or values["hct"] > 52.0
        or values["plt"] < 150.0
        or values["plt"] > 450.0
        or values["mcv"] < 80.0
        or values["mcv"] > 100.0
        or values["mch"] < 27.0
        or values["mch"] > 33.0
        or values["mchc"] < 32.0
        or values["mchc"] > 36.0
        or values["rdw"] < 11.5
        or values["rdw"] > 14.5
        or values["mpv"] < 7.5
        or values["mpv"] > 12.0
        or values["neutrophils"] < 2.0
        or values["neutrophils"] > 7.5
        or values["lymphocytes"] < 1.0
        or values["lymphocytes"] > 4.0
        or values["monocytes"] < 0.2
        or values["monocytes"] > 1.0
        or values["eosinophils"] < 0.0
        or values["eosinophils"] > 0.5
        or values["basophils"] < 0.0
        or values["basophils"] > 0.2
        or "abnormal" in flags
    )

    return "Abnormal non-critical" if abnormal else "Routine"


def load_model() -> dict[str, Any] | None:
    if not MODEL_PATH.exists():
        return None

    bundle = joblib.load(MODEL_PATH)
    if bundle.get("feature_names") != FEATURE_NAMES:
        return None

    return bundle
