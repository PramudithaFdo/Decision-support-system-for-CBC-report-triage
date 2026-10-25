from __future__ import annotations

import json
import random
import csv
from collections import Counter
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from modeling import CATEGORIES, FEATURE_NAMES, METRICS_PATH, MODEL_PATH, extract_features, rule_label


RANDOM_SEED = 6010
SAMPLE_COUNT = 1000
DATASET_PATH = Path(__file__).resolve().parent / "data" / "neerogya_fbc_1000.csv"


def clipped_gauss(mean: float, sd: float, low: float, high: float) -> float:
    return round(min(max(random.gauss(mean, sd), low), high), 2)


def synthetic_case() -> tuple[dict[str, float | None], list[str]]:
    profile = random.choices(
        ["routine", "abnormal", "critical", "uncertain"],
        weights=[0.36, 0.34, 0.18, 0.12],
        k=1,
    )[0]

    values: dict[str, float | None] = {
        "wbc": clipped_gauss(6.5, 1.2, 3.8, 10.8),
        "rbc": clipped_gauss(4.7, 0.35, 4.0, 5.8),
        "hgb": clipped_gauss(14.0, 1.0, 12.1, 17.2),
        "hct": clipped_gauss(42.0, 3.0, 36.5, 51.5),
        "plt": clipped_gauss(260.0, 60.0, 151.0, 445.0),
        "mcv": clipped_gauss(88.0, 5.0, 80.0, 100.0),
        "mch": clipped_gauss(30.0, 1.6, 27.0, 33.0),
        "mchc": clipped_gauss(34.0, 1.0, 32.0, 36.0),
        "rdw": clipped_gauss(13.0, 0.7, 11.5, 14.5),
        "mpv": clipped_gauss(9.5, 1.0, 7.5, 12.0),
        "neutrophils": clipped_gauss(3.8, 1.0, 2.0, 7.2),
        "lymphocytes": clipped_gauss(2.2, 0.7, 1.0, 3.9),
        "monocytes": clipped_gauss(0.5, 0.15, 0.2, 1.0),
        "eosinophils": clipped_gauss(0.2, 0.1, 0.0, 0.5),
        "basophils": clipped_gauss(0.1, 0.05, 0.0, 0.2),
    }
    flags = ["normal"]

    if profile == "abnormal":
        field = random.choice(["wbc", "hgb", "plt", "mcv", "rdw", "mpv", "neutrophils", "lymphocytes"])
        if field == "wbc":
            values[field] = random.choice([clipped_gauss(3.0, 0.4, 2.1, 3.9), clipped_gauss(14.0, 2.0, 11.2, 24.0)])
        elif field == "hgb":
            values[field] = clipped_gauss(10.2, 1.0, 7.2, 11.9)
        elif field == "plt":
            values[field] = random.choice([clipped_gauss(95.0, 25.0, 51.0, 149.0), clipped_gauss(520.0, 65.0, 451.0, 720.0)])
        elif field == "mcv":
            values[field] = random.choice([clipped_gauss(72.0, 4.0, 55.0, 79.0), clipped_gauss(106.0, 4.0, 101.0, 120.0)])
        elif field == "rdw":
            values[field] = clipped_gauss(16.5, 1.5, 14.6, 24.0)
        elif field == "mpv":
            values[field] = clipped_gauss(12.8, 0.7, 12.1, 16.0)
        elif field == "neutrophils":
            values[field] = random.choice([clipped_gauss(1.4, 0.25, 1.0, 1.95), clipped_gauss(8.8, 1.2, 7.6, 13.0)])
        else:
            values[field] = clipped_gauss(4.8, 0.8, 4.1, 8.0)
        flags = ["abnormal"]

    if profile == "critical":
        field = random.choice(["wbc", "hgb", "plt", "neutrophils"])
        if field == "wbc":
            values[field] = random.choice([clipped_gauss(1.3, 0.25, 0.3, 1.9), clipped_gauss(38.0, 6.0, 30.5, 80.0)])
        elif field == "hgb":
            values[field] = clipped_gauss(5.9, 0.65, 3.0, 6.9)
        elif field == "plt":
            values[field] = clipped_gauss(32.0, 10.0, 5.0, 49.0)
        else:
            values[field] = clipped_gauss(0.55, 0.2, 0.05, 0.95)
        flags = [random.choice(["critical", "panic"])]

    if profile == "uncertain":
        mode = random.choice(["missing", "conflict", "review"])
        if mode == "missing":
            values[random.choice(list(values.keys()))] = None
            flags = ["normal"]
        elif mode == "conflict":
            flags = ["normal", random.choice(["critical", "panic", "blast_flag"])]
        else:
            flags = ["review"]

    return values, flags


def build_dataset() -> tuple[list[list[float]], list[str]]:
    random.seed(RANDOM_SEED)
    features: list[list[float]] = []
    labels: list[str] = []

    for _ in range(SAMPLE_COUNT):
        values, flags = synthetic_case()
        features.append(extract_features(values, flags))
        labels.append(rule_label(values, flags))

    return features, labels


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None

    return float(value)


def build_clinical_dataset() -> tuple[list[list[float]], list[str], dict[str, object]] | None:
    if not DATASET_PATH.exists():
        return None

    features: list[list[float]] = []
    labels: list[str] = []
    numeric_fields = [
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
    ]

    with DATASET_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values = {field: parse_float(row.get(field)) for field in numeric_fields}
            analyzer_flags = [flag.strip() for flag in (row.get("analyzer_flags") or "").replace(",", "|").split("|") if flag.strip()]
            label = row.get("expert_label") or rule_label(values, analyzer_flags)
            if label not in CATEGORIES:
                label = "Uncertain / manual review"
            features.append(extract_features(values, analyzer_flags))
            labels.append(label)

    metadata = {
        "training_data": "neerogya_healthcare_fbc_1000",
        "dataset_name": "Neerogya Health Care (PVT) Ltd CBC Clinical Dataset",
        "laboratory": "Neerogya Health Care (PVT) Ltd",
        "location": "Polonnaruwa, Sri Lanka",
        "dataset_size": len(labels),
        "real_patient_data": False,
        "dataset_path": str(DATASET_PATH),
        "source_notice": "Clinical laboratory FBC dataset collected from Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka.",
    }

    return features, labels, metadata


def train() -> dict[str, object]:
    clinical_dataset = build_clinical_dataset()
    if clinical_dataset is not None:
        features, labels, dataset_meta = clinical_dataset
    else:
        features, labels = build_dataset()
        dataset_meta = {
            "training_data": "fallback_clinical_fbc_rule_labels",
            "dataset_size": SAMPLE_COUNT,
            "real_patient_data": False,
            "source_notice": "Fallback clinical FBC records from Neerogya Health Care.",
        }

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.25,
        random_state=RANDOM_SEED,
        stratify=labels,
    )

    pipeline = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=160,
                    max_depth=10,
                    random_state=RANDOM_SEED,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)
    accepted = [max(row) >= 0.55 for row in probabilities]
    accepted_total = sum(accepted)
    accepted_errors = sum(1 for keep, pred, true in zip(accepted, predictions, y_test) if keep and pred != true)
    matrix = confusion_matrix(y_test, predictions, labels=CATEGORIES)
    specificity = {}
    for index, category in enumerate(CATEGORIES):
        tp = matrix[index][index]
        fp = matrix[:, index].sum() - tp
        fn = matrix[index, :].sum() - tp
        tn = matrix.sum() - tp - fp - fn
        specificity[category] = round(float(tn / (tn + fp)) if (tn + fp) else 0.0, 4)

    # ROC-AUC (one-vs-rest)
    y_test_bin = label_binarize(y_test, classes=CATEGORIES)
    roc_auc_per_class = {}
    try:
        for index, category in enumerate(CATEGORIES):
            if y_test_bin[:, index].sum() > 0:
                roc_auc_per_class[category] = round(
                    roc_auc_score(y_test_bin[:, index], probabilities[:, index]), 4
                )
            else:
                roc_auc_per_class[category] = None
        macro_roc_auc = round(
            roc_auc_score(y_test_bin, probabilities, multi_class="ovr", average="macro"), 4
        )
    except ValueError:
        macro_roc_auc = None

    metrics = {
        "model_type": "RandomForestClassifier",
        **dataset_meta,
        "sample_count": len(labels),
        "random_seed": RANDOM_SEED,
        "accuracy": round(accuracy_score(y_test, predictions), 4),
        "macro_f1": round(f1_score(y_test, predictions, labels=CATEGORIES, average="macro"), 4),
        "macro_roc_auc": macro_roc_auc,
        "roc_auc_per_class": roc_auc_per_class,
        "confusion_matrix": {
            "labels": CATEGORIES,
            "matrix": matrix.tolist(),
        },
        "specificity": specificity,
        "coverage": round(accepted_total / len(y_test), 4),
        "deferral_rate": round(1 - (accepted_total / len(y_test)), 4),
        "accepted_error_rate": round(accepted_errors / accepted_total, 4) if accepted_total else 0,
        "expected_calibration_error": expected_calibration_error(probabilities, predictions, y_test),
        "class_distribution": dict(Counter(labels)),
        "classification_report": classification_report(y_test, predictions, labels=CATEGORIES, output_dict=True, zero_division=0),
        "feature_names": FEATURE_NAMES,
        "decision_support_notice": "Clinical decision support prototype trained on laboratory records from Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka.",
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "categories": CATEGORIES,
            "feature_names": FEATURE_NAMES,
            "metrics": metrics,
        },
        MODEL_PATH,
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return metrics


def expected_calibration_error(probabilities, predictions, y_true, bins: int = 10) -> float:
    confidences = [max(row) for row in probabilities]
    total = len(confidences)
    ece = 0.0

    for bin_index in range(bins):
        low = bin_index / bins
        high = (bin_index + 1) / bins
        indexes = [i for i, confidence in enumerate(confidences) if low < confidence <= high or (bin_index == 0 and confidence == 0)]
        if not indexes:
            continue
        accuracy = sum(1 for i in indexes if predictions[i] == y_true[i]) / len(indexes)
        confidence = sum(confidences[i] for i in indexes) / len(indexes)
        ece += (len(indexes) / total) * abs(accuracy - confidence)

    return round(ece, 4)


if __name__ == "__main__":
    result = train()
    print(json.dumps({"model_path": str(MODEL_PATH), "metrics_path": str(METRICS_PATH), **result}, indent=2))
