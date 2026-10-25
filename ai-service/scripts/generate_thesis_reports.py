"""Generate comprehensive thesis-ready reports from a trained FBC triage model.

Produces Markdown reports and CSV artifacts suitable for direct inclusion in
an MSc thesis chapter covering ML model evaluation.

Reports generated:
  1. Model Performance Report (Markdown)
  2. Dataset Summary Report (Markdown)
  3. Feature Importance Report (Markdown)
  4. Cross-Validation Report (Markdown)
  5. Raw CSV exports for all key metrics

Usage:
    cd ai-service
    python scripts/generate_thesis_reports.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import label_binarize

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from modeling import CATEGORIES, FEATURE_NAMES, METRICS_PATH, MODEL_PATH  # noqa: E402
from train_model import DATASET_PATH, build_clinical_dataset, RANDOM_SEED  # noqa: E402

REPORTS_DIR = _project_root / "reports"


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def load_metrics() -> dict:
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"No metrics file found at {METRICS_PATH}. Run train_model.py first.")


def load_trained_model():
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    raise FileNotFoundError(f"No model file found at {MODEL_PATH}. Run train_model.py first.")


# ---------------------------------------------------------------------------
# 1. Model Performance Report
# ---------------------------------------------------------------------------
def generate_model_performance_report(metrics: dict, out_dir: Path) -> None:
    cm = metrics["confusion_matrix"]
    labels = cm["labels"]
    matrix = cm["matrix"]
    cr = metrics.get("classification_report", {})
    spec = metrics.get("specificity", {})
    roc_auc = metrics.get("roc_auc_per_class", {})

    lines = [
        "# Model Performance Report",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "> **Laboratory Source**: Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka",
        "> **Dataset**: Clinical Complete Blood Count (CBC/FBC) Dataset (1,000 records)",
        "> **Study Scope**: Clinical Decision Support System for CBC Report Triage (MSc Research Project)",
        "",
        "## 1. Overall Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Accuracy** | {metrics.get('accuracy', 'N/A')} |",
        f"| **Macro F1-Score** | {metrics.get('macro_f1', 'N/A')} |",
        f"| **Macro ROC-AUC** | {metrics.get('macro_roc_auc', 'N/A')} |",
        f"| **Coverage** | {metrics.get('coverage', 'N/A')} |",
        f"| **Deferral Rate** | {metrics.get('deferral_rate', 'N/A')} |",
        f"| **Accepted Error Rate** | {metrics.get('accepted_error_rate', 'N/A')} |",
        f"| **Expected Calibration Error** | {metrics.get('expected_calibration_error', 'N/A')} |",
        f"| **Dataset Size** | {metrics.get('sample_count', 'N/A')} |",
        f"| **Test Split** | 25% ({int(metrics.get('sample_count', 0) * 0.25)} samples) |",
        f"| **Model Type** | {metrics.get('model_type', 'N/A')} |",
        f"| **Random Seed** | {metrics.get('random_seed', 'N/A')} |",
        "",
        "## 2. Per-Class Classification Metrics",
        "",
        "| Class | Precision | Recall | F1-Score | Specificity | ROC-AUC | Support |",
        "|-------|-----------|--------|----------|-------------|---------|---------|",
    ]

    for label in labels:
        class_cr = cr.get(label, {})
        p = round(class_cr.get("precision", 0), 4) if isinstance(class_cr.get("precision"), (int, float)) else "N/A"
        rec = round(class_cr.get("recall", 0), 4) if isinstance(class_cr.get("recall"), (int, float)) else "N/A"
        f1 = round(class_cr.get("f1-score", 0), 4) if isinstance(class_cr.get("f1-score"), (int, float)) else "N/A"
        s = spec.get(label, "N/A")
        auc = roc_auc.get(label, "N/A")
        sup = class_cr.get("support", "N/A")
        if isinstance(sup, float):
            sup = int(sup)
        lines.append(f"| {label} | {p} | {rec} | {f1} | {s} | {auc} | {sup} |")

    # Macro/weighted averages
    for avg_key in ["macro avg", "weighted avg"]:
        avg = cr.get(avg_key, {})
        if avg:
            p = round(avg.get("precision", 0), 4) if isinstance(avg.get("precision"), (int, float)) else "N/A"
            rec = round(avg.get("recall", 0), 4) if isinstance(avg.get("recall"), (int, float)) else "N/A"
            f1 = round(avg.get("f1-score", 0), 4) if isinstance(avg.get("f1-score"), (int, float)) else "N/A"
            lines.append(
                f"| **{avg_key.title()}** | {p} | "
                f"{rec} | {f1} | — | — | "
                f"{int(avg.get('support', 0))} |"
            )

    lines.extend([
        "",
        "## 3. Confusion Matrix",
        "",
        "Rows = Actual class, Columns = Predicted class.",
        "",
    ])

    # Header
    header = "| | " + " | ".join(f"**{l}**" for l in labels) + " |"
    separator = "|---|" + "|".join(["---"] * len(labels)) + "|"
    lines.append(header)
    lines.append(separator)

    for i, row_label in enumerate(labels):
        row_values = " | ".join(str(v) for v in matrix[i])
        lines.append(f"| **{row_label}** | {row_values} |")

    lines.extend([
        "",
        "## 4. Decision Support Thresholds",
        "",
        "| Threshold | Value | Description |",
        "|-----------|-------|-------------|",
        "| Confidence threshold | 0.55 | Predictions below this are deferred to manual review |",
        f"| Deferral rate | {metrics.get('deferral_rate', 'N/A')} | Proportion of test samples deferred |",
        f"| Accepted error rate | {metrics.get('accepted_error_rate', 'N/A')} | Error rate among accepted predictions |",
        "",
        "---",
        "",
        "*This report was auto-generated by `generate_thesis_reports.py` for MSc research documentation.*",
    ])

    report_path = out_dir / "model_performance_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {report_path.name}")

    # Also export classification report as CSV
    csv_path = out_dir / "classification_report.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "precision", "recall", "f1_score", "specificity", "roc_auc", "support"])
        for label in labels:
            class_cr = cr.get(label, {})
            writer.writerow([
                label,
                class_cr.get("precision", ""),
                class_cr.get("recall", ""),
                class_cr.get("f1-score", ""),
                spec.get(label, ""),
                roc_auc.get(label, ""),
                int(class_cr.get("support", 0)),
            ])
    print(f"  ✓ {csv_path.name}")

    # Export confusion matrix as CSV
    cm_csv_path = out_dir / "confusion_matrix.csv"
    with cm_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["actual_class"] + labels)
        for i, row_label in enumerate(labels):
            writer.writerow([row_label] + matrix[i])
    print(f"  ✓ {cm_csv_path.name}")


# ---------------------------------------------------------------------------
# 2. Dataset Summary Report
# ---------------------------------------------------------------------------
def generate_dataset_summary_report(metrics: dict, out_dir: Path) -> None:
    dist = metrics.get("class_distribution", {})
    total = sum(dist.values())

    lines = [
        "# Dataset Summary Report",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Dataset Overview",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| **Laboratory Name** | {metrics.get('laboratory', 'Neerogya Health Care (PVT) Ltd')} |",
        f"| **Location** | {metrics.get('location', 'Polonnaruwa, Sri Lanka')} |",
        f"| **Dataset Name** | {metrics.get('dataset_name', 'Neerogya Health Care (PVT) Ltd CBC Clinical Dataset')} |",
        f"| **Total Records** | {total} |",
        f"| **Real Clinical Data** | {metrics.get('real_patient_data', True)} |",
        f"| **Source Notice** | {metrics.get('source_notice', 'Clinical laboratory FBC dataset collected from Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka.')} |",
        "",
        "## 2. Class Distribution",
        "",
        "| Triage Category | Count | Percentage |",
        "|-----------------|-------|------------|",
    ]

    for label in CATEGORIES:
        count = dist.get(label, 0)
        pct = round(count / total * 100, 1) if total else 0
        lines.append(f"| {label} | {count} | {pct}% |")

    lines.append(f"| **Total** | **{total}** | **100%** |")

    # Feature statistics from the CSV
    lines.extend([
        "",
        "## 3. Feature Statistics (per class)",
        "",
    ])

    clinical_dataset = build_clinical_dataset()
    if clinical_dataset is not None:
        features, labels_list, _ = clinical_dataset
        feature_arr = np.array(features)
        numeric_features = FEATURE_NAMES[:15]  # First 15 are numeric CBC values

        # Overall statistics table
        lines.extend([
            "### 3.1 Overall Feature Statistics",
            "",
            "| Feature | Mean | Std | Min | Max |",
            "|---------|------|-----|-----|-----|",
        ])

        stats_rows = []
        for i, name in enumerate(numeric_features):
            col = feature_arr[:, i]
            stats_rows.append({
                "feature": name,
                "mean": round(float(np.mean(col)), 2),
                "std": round(float(np.std(col)), 2),
                "min": round(float(np.min(col)), 2),
                "max": round(float(np.max(col)), 2),
            })
            lines.append(
                f"| {name.upper()} | {stats_rows[-1]['mean']} | {stats_rows[-1]['std']} | "
                f"{stats_rows[-1]['min']} | {stats_rows[-1]['max']} |"
            )

        # Per-class statistics
        lines.extend([
            "",
            "### 3.2 Feature Statistics by Triage Category",
            "",
        ])

        for category in CATEGORIES:
            indices = [i for i, lbl in enumerate(labels_list) if lbl == category]
            if not indices:
                continue
            subset = feature_arr[indices]
            lines.extend([
                f"#### {category} (n={len(indices)})",
                "",
                "| Feature | Mean | Std | Min | Max |",
                "|---------|------|-----|-----|-----|",
            ])
            for i, name in enumerate(numeric_features):
                col = subset[:, i]
                lines.append(
                    f"| {name.upper()} | {round(float(np.mean(col)), 2)} | "
                    f"{round(float(np.std(col)), 2)} | {round(float(np.min(col)), 2)} | "
                    f"{round(float(np.max(col)), 2)} |"
                )
            lines.append("")

        # Export statistics CSV
        csv_path = out_dir / "dataset_statistics.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["feature", "class", "mean", "std", "min", "max", "count"])
            for category in CATEGORIES:
                indices = [i for i, lbl in enumerate(labels_list) if lbl == category]
                if not indices:
                    continue
                subset = feature_arr[indices]
                for i, name in enumerate(numeric_features):
                    col = subset[:, i]
                    writer.writerow([
                        name, category,
                        round(float(np.mean(col)), 4),
                        round(float(np.std(col)), 4),
                        round(float(np.min(col)), 4),
                        round(float(np.max(col)), 4),
                        len(indices),
                    ])
        print(f"  ✓ {csv_path.name}")

    # Missing value analysis
    lines.extend([
        "",
        "## 4. Missing Value Summary",
        "",
    ])

    if DATASET_PATH.exists():
        import csv as csv_mod
        with DATASET_PATH.open(newline="", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            missing_counts: dict[str, int] = {}
            total_rows = 0
            for row in reader:
                total_rows += 1
                for field in ["wbc", "rbc", "hgb", "hct", "plt", "mcv", "mch", "mchc", "rdw", "mpv",
                              "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]:
                    if not row.get(field) or row[field].strip() == "":
                        missing_counts[field] = missing_counts.get(field, 0) + 1

        lines.extend([
            "| Feature | Missing Count | Missing % |",
            "|---------|--------------|-----------|",
        ])
        for field in ["wbc", "rbc", "hgb", "hct", "plt", "mcv", "mch", "mchc", "rdw", "mpv",
                       "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]:
            mc = missing_counts.get(field, 0)
            pct = round(mc / total_rows * 100, 1) if total_rows else 0
            lines.append(f"| {field.upper()} | {mc} | {pct}% |")

    lines.extend([
        "",
        "---",
        "",
        "*This report was auto-generated by `generate_thesis_reports.py` for MSc research documentation.*",
    ])

    report_path = out_dir / "dataset_summary_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {report_path.name}")


# ---------------------------------------------------------------------------
# 3. Feature Importance Report
# ---------------------------------------------------------------------------
def generate_feature_importance_report(out_dir: Path) -> None:
    bundle = load_trained_model()
    pipeline = bundle["pipeline"]
    clf = pipeline.named_steps["classifier"]

    importances = clf.feature_importances_
    sorted_indices = np.argsort(importances)[::-1]

    lines = [
        "# Feature Importance Report",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Random Forest Feature Importances (Gini Importance)",
        "",
        "Features are ranked by their contribution to reducing impurity across all",
        "decision trees in the ensemble.",
        "",
        "| Rank | Feature | Importance | Cumulative |",
        "|------|---------|------------|------------|",
    ]

    cumulative = 0.0
    csv_rows = []
    for rank, idx in enumerate(sorted_indices, 1):
        name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feature_{idx}"
        imp = round(float(importances[idx]), 4)
        cumulative += imp
        lines.append(f"| {rank} | {name} | {imp} | {round(cumulative, 4)} |")
        csv_rows.append({"rank": rank, "feature": name, "importance": imp, "cumulative": round(cumulative, 4)})

    lines.extend([
        "",
        "## Key Observations",
        "",
        f"- **Top-3 features** account for {round(sum(importances[sorted_indices[:3]]) * 100, 1)}% of total importance",
        f"- **Top-5 features** account for {round(sum(importances[sorted_indices[:5]]) * 100, 1)}% of total importance",
        f"- **Top-10 features** account for {round(sum(importances[sorted_indices[:10]]) * 100, 1)}% of total importance",
        f"- **Total features**: {len(FEATURE_NAMES)}",
        "",
        "## Interpretation Notes",
        "",
        "- Binary flag features (flag_normal, flag_critical, etc.) capture analyzer annotations",
        "- High importance of flag features indicates the model relies on both numeric CBC values",
        "  and analyzer interpretations for triage decisions",
        "- `missing_count` importance reflects the model's ability to handle incomplete reports",
        "",
        "---",
        "",
        "*This report was auto-generated by `generate_thesis_reports.py` for MSc research documentation.*",
    ])

    report_path = out_dir / "feature_importance_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {report_path.name}")

    # CSV export
    csv_path = out_dir / "feature_importances.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "feature", "importance", "cumulative"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  ✓ {csv_path.name}")


# ---------------------------------------------------------------------------
# 4. Cross-Validation Report
# ---------------------------------------------------------------------------
def generate_cross_validation_report(out_dir: Path) -> None:
    clinical_dataset = build_clinical_dataset()
    if clinical_dataset is None:
        print("  ✗ Cannot generate cross-validation report: no clinical dataset found.")
        return

    features, labels, _ = clinical_dataset
    X = np.array(features)
    y = np.array(labels)

    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

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

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    scoring = {
        "accuracy": "accuracy",
        "f1_macro": "f1_macro",
        "precision_macro": "precision_macro",
        "recall_macro": "recall_macro",
    }

    cv_results = cross_validate(pipeline, X, y, cv=cv, scoring=scoring, return_train_score=True)

    lines = [
        "# Cross-Validation Report",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 5-Fold Stratified Cross-Validation Results",
        "",
        f"- **Model**: RandomForestClassifier (n_estimators=160, max_depth=10, class_weight=balanced)",
        f"- **Dataset Size**: {len(y)} samples",
        f"- **CV Strategy**: 5-fold stratified",
        f"- **Random Seed**: {RANDOM_SEED}",
        "",
        "### Test Set Performance (across 5 folds)",
        "",
        "| Metric | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Mean ± Std |",
        "|--------|--------|--------|--------|--------|--------|------------|",
    ]

    csv_rows = []
    for metric_key, display_name in [
        ("test_accuracy", "Accuracy"),
        ("test_f1_macro", "Macro F1"),
        ("test_precision_macro", "Macro Precision"),
        ("test_recall_macro", "Macro Recall"),
    ]:
        scores = cv_results[metric_key]
        fold_strs = " | ".join(f"{s:.4f}" for s in scores)
        mean_std = f"{np.mean(scores):.4f} ± {np.std(scores):.4f}"
        lines.append(f"| **{display_name}** | {fold_strs} | {mean_std} |")

        for fold_idx, score in enumerate(scores, 1):
            csv_rows.append({
                "metric": display_name,
                "fold": fold_idx,
                "score": round(float(score), 4),
                "set": "test",
            })

    lines.extend([
        "",
        "### Training Set Performance (across 5 folds)",
        "",
        "| Metric | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Mean ± Std |",
        "|--------|--------|--------|--------|--------|--------|------------|",
    ])

    for metric_key, display_name in [
        ("train_accuracy", "Accuracy"),
        ("train_f1_macro", "Macro F1"),
        ("train_precision_macro", "Macro Precision"),
        ("train_recall_macro", "Macro Recall"),
    ]:
        scores = cv_results[metric_key]
        fold_strs = " | ".join(f"{s:.4f}" for s in scores)
        mean_std = f"{np.mean(scores):.4f} ± {np.std(scores):.4f}"
        lines.append(f"| **{display_name}** | {fold_strs} | {mean_std} |")

        for fold_idx, score in enumerate(scores, 1):
            csv_rows.append({
                "metric": display_name,
                "fold": fold_idx,
                "score": round(float(score), 4),
                "set": "train",
            })

    # Overfitting analysis
    train_acc = np.mean(cv_results["train_accuracy"])
    test_acc = np.mean(cv_results["test_accuracy"])
    gap = train_acc - test_acc

    lines.extend([
        "",
        "### Overfitting Analysis",
        "",
        f"- **Train-Test Accuracy Gap**: {gap:.4f}",
    ])

    if gap < 0.05:
        lines.append("- **Assessment**: Minimal overfitting detected. Model generalises well.")
    elif gap < 0.10:
        lines.append("- **Assessment**: Moderate gap; acceptable for clinical triage decision support.")
    else:
        lines.append("- **Assessment**: Significant gap suggesting overfitting. Consider regularisation.")

    lines.extend([
        "",
        "---",
        "",
        "*This report was auto-generated by `generate_thesis_reports.py` for MSc research documentation.*",
    ])

    report_path = out_dir / "cross_validation_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {report_path.name}")

    # CSV export
    csv_path = out_dir / "cross_validation_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "set", "fold", "score"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  ✓ {csv_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("FBC Triage Model — Thesis Report Generator")
    print("=" * 60)
    print()

    out_dir = ensure_reports_dir()
    print(f"Output directory: {out_dir}")
    print()

    metrics = load_metrics()

    print("Generating reports...")
    print()

    print("[1/4] Model Performance Report")
    generate_model_performance_report(metrics, out_dir)
    print()

    print("[2/4] Dataset Summary Report")
    generate_dataset_summary_report(metrics, out_dir)
    print()

    print("[3/4] Feature Importance Report")
    generate_feature_importance_report(out_dir)
    print()

    print("[4/4] Cross-Validation Report")
    generate_cross_validation_report(out_dir)
    print()

    print("=" * 60)
    print(f"All reports generated in: {out_dir}")
    print("=" * 60)

    # List all generated files
    generated = sorted(out_dir.iterdir())
    print(f"\nGenerated {len(generated)} files:")
    for f in generated:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
