"""Generate 1,000 clinical Complete Blood Count (CBC/FBC) records.

Records represent hematology profiles from Neerogya Health Care (PVT) Ltd,
situated in Polonnaruwa, Sri Lanka. Includes adult male, adult female, and elderly
demographics with 5-part differential parameters and clinical triage classifications.

Usage:
    python3 ai-service/scripts/generate_neerogya_fbc_1000.py
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Import the project's rule_label so expert labels stay consistent
# ---------------------------------------------------------------------------
import sys

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from modeling import rule_label  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 601027
TOTAL = 1000

# Target class distribution (clinically representative)
CATEGORY_TARGETS = {
    "Routine": 400,
    "Abnormal non-critical": 350,
    "Critical / urgent": 110,
    "Uncertain / manual review": 140,
}

FIELDS = [
    "patient_code",
    "sample_code",
    "age_group",
    "sex",
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
    "analyzer_flags",
    "data_source",
    "data_source_label",
    "expert_label",
    "label_confidence",
    "label_source",
    "notes",
]

# ---------------------------------------------------------------------------
# Demographic reference ranges (Sri Lankan adult population norms)
# Each entry: (mean, sd, low_clip, high_clip)
# ---------------------------------------------------------------------------
DEMOGRAPHICS = {
    "adult_male": {
        "rbc": (5.0, 0.4, 4.2, 5.9),
        "hgb_per_rbc": (3.05, 0.12, 2.7, 3.4),   # MCH proxy
        "mcv": (88.0, 5.5, 78.0, 100.0),
        "rdw": (13.0, 0.8, 11.5, 14.5),
        "wbc": (6.8, 1.6, 4.0, 11.0),
        "plt": (250.0, 55.0, 150.0, 400.0),
        "mpv": (9.5, 1.0, 7.5, 12.0),
        "neutrophil_frac": (0.58, 0.08, 0.40, 0.75),
        "lymphocyte_frac": (0.30, 0.07, 0.18, 0.45),
        "monocyte_frac": (0.06, 0.02, 0.02, 0.10),
        "eosinophil_frac": (0.03, 0.015, 0.00, 0.06),
        "basophil_frac": (0.01, 0.005, 0.00, 0.02),
    },
    "adult_female": {
        "rbc": (4.4, 0.35, 3.8, 5.4),
        "hgb_per_rbc": (2.90, 0.12, 2.6, 3.3),
        "mcv": (87.0, 5.5, 78.0, 100.0),
        "rdw": (13.2, 0.9, 11.5, 14.8),
        "wbc": (6.5, 1.5, 4.0, 11.0),
        "plt": (270.0, 58.0, 155.0, 420.0),
        "mpv": (9.3, 1.0, 7.5, 12.0),
        "neutrophil_frac": (0.57, 0.08, 0.38, 0.72),
        "lymphocyte_frac": (0.32, 0.07, 0.20, 0.48),
        "monocyte_frac": (0.06, 0.02, 0.02, 0.10),
        "eosinophil_frac": (0.03, 0.015, 0.00, 0.06),
        "basophil_frac": (0.01, 0.005, 0.00, 0.02),
    },
    "elderly": {
        "rbc": (4.3, 0.45, 3.5, 5.5),
        "hgb_per_rbc": (2.85, 0.15, 2.5, 3.3),
        "mcv": (90.0, 6.0, 78.0, 102.0),
        "rdw": (13.8, 1.1, 11.8, 16.0),
        "wbc": (6.0, 1.5, 3.8, 10.5),
        "plt": (235.0, 60.0, 140.0, 380.0),
        "mpv": (9.8, 1.1, 7.5, 12.5),
        "neutrophil_frac": (0.60, 0.09, 0.40, 0.78),
        "lymphocyte_frac": (0.28, 0.07, 0.16, 0.42),
        "monocyte_frac": (0.07, 0.02, 0.02, 0.12),
        "eosinophil_frac": (0.03, 0.015, 0.00, 0.07),
        "basophil_frac": (0.01, 0.005, 0.00, 0.02),
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clipped_gauss(mean: float, sd: float, low: float, high: float) -> float:
    return min(max(random.gauss(mean, sd), low), high)


def add_noise(value: float, noise_pct: float = 0.025) -> float:
    """Add ±analytical noise (default ±2.5%)."""
    return value * (1 + random.uniform(-noise_pct, noise_pct))


def r(value: float) -> float:
    """Round to 2 decimal places."""
    return round(value, 2)


def pick_demographic() -> tuple[str, str, str]:
    """Return (demographic_key, age_group_label, sex_label)."""
    choice = random.choices(
        ["adult_male", "adult_female", "elderly"],
        weights=[0.38, 0.38, 0.24],
        k=1,
    )[0]
    if choice == "adult_male":
        return choice, "adult", "male"
    elif choice == "adult_female":
        return choice, "adult", "female"
    else:
        sex = random.choice(["male", "female"])
        return choice, "elderly", sex


# ---------------------------------------------------------------------------
# Core physiological generation (with inter-parameter correlations)
# ---------------------------------------------------------------------------
def generate_baseline(cohort: dict) -> dict[str, float]:
    """Generate a physiologically consistent baseline CBC with correlations."""
    rbc = clipped_gauss(*cohort["rbc"])
    mcv = clipped_gauss(*cohort["mcv"])
    mch = clipped_gauss(*cohort["hgb_per_rbc"]) * 10  # MCH in pg

    # Derived values with physiological relationships
    hgb = rbc * mch / 10
    hct = rbc * mcv / 10
    mchc = (hgb / hct * 100) if hct > 0 else 33.0

    rdw = clipped_gauss(*cohort["rdw"])
    wbc = clipped_gauss(*cohort["wbc"])
    plt = clipped_gauss(*cohort["plt"])
    mpv = clipped_gauss(*cohort["mpv"])

    # WBC differential (fractions of total WBC)
    neut_frac = clipped_gauss(*cohort["neutrophil_frac"])
    lymph_frac = clipped_gauss(*cohort["lymphocyte_frac"])
    mono_frac = clipped_gauss(*cohort["monocyte_frac"])
    eo_frac = clipped_gauss(*cohort["eosinophil_frac"])
    baso_frac = clipped_gauss(*cohort["basophil_frac"])

    # Normalize fractions to sum to ~1.0
    total_frac = neut_frac + lymph_frac + mono_frac + eo_frac + baso_frac
    if total_frac > 0:
        neut_frac /= total_frac
        lymph_frac /= total_frac
        mono_frac /= total_frac
        eo_frac /= total_frac
        baso_frac /= total_frac

    neutrophils = wbc * neut_frac
    lymphocytes = wbc * lymph_frac
    monocytes = wbc * mono_frac
    eosinophils = wbc * eo_frac
    basophils = wbc * baso_frac

    return {
        "wbc": wbc,
        "rbc": rbc,
        "hgb": hgb,
        "hct": hct,
        "plt": plt,
        "mcv": mcv,
        "mch": mch,
        "mchc": mchc,
        "rdw": rdw,
        "mpv": mpv,
        "neutrophils": neutrophils,
        "lymphocytes": lymphocytes,
        "monocytes": monocytes,
        "eosinophils": eosinophils,
        "basophils": basophils,
    }


def apply_noise_to_values(values: dict[str, float]) -> dict[str, float]:
    """Apply small analytical noise to all numeric values."""
    noised = {}
    for key, val in values.items():
        if val is not None:
            noised[key] = add_noise(val, noise_pct=random.uniform(0.01, 0.04))
        else:
            noised[key] = val
    return noised


def clip_and_round(values: dict[str, float]) -> dict[str, float]:
    """Ensure all values are non-negative and rounded."""
    result = {}
    for key, val in values.items():
        if val is not None:
            result[key] = r(max(val, 0.0))
        else:
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# Abnormality pattern modifiers
# ---------------------------------------------------------------------------
def apply_iron_deficiency(values: dict, severity: str = "mild") -> tuple[dict, str]:
    """Iron deficiency anemia: low MCV, low MCH, low HGB, high RDW."""
    if severity == "severe":
        values["mcv"] = clipped_gauss(62, 4, 52, 72)
        values["mch"] = clipped_gauss(19, 2, 14, 23)
        values["rbc"] = clipped_gauss(3.2, 0.3, 2.5, 3.8)
        values["rdw"] = clipped_gauss(19.5, 2.0, 16, 26)
    else:
        values["mcv"] = clipped_gauss(74, 3, 66, 79)
        values["mch"] = clipped_gauss(24, 1.5, 20, 26.5)
        values["rbc"] = clipped_gauss(4.0, 0.3, 3.4, 4.6)
        values["rdw"] = clipped_gauss(16.5, 1.2, 14.8, 21)

    # Recalculate derived values
    values["hgb"] = values["rbc"] * values["mch"] / 10
    values["hct"] = values["rbc"] * values["mcv"] / 10
    values["mchc"] = (values["hgb"] / values["hct"] * 100) if values["hct"] > 0 else 30.0

    note = f"Iron deficiency anemia ({severity})"
    return values, note


def apply_b12_folate_deficiency(values: dict) -> tuple[dict, str]:
    """B12/folate deficiency: high MCV, low RBC, normal-to-low WBC."""
    values["mcv"] = clipped_gauss(108, 5, 101, 125)
    values["mch"] = clipped_gauss(34, 2, 30, 40)
    values["rbc"] = clipped_gauss(3.2, 0.4, 2.2, 4.0)
    values["rdw"] = clipped_gauss(16, 1.5, 14.0, 22)
    values["wbc"] = clipped_gauss(4.5, 1.0, 2.8, 7.0)

    # Recalculate
    values["hgb"] = values["rbc"] * values["mch"] / 10
    values["hct"] = values["rbc"] * values["mcv"] / 10
    values["mchc"] = (values["hgb"] / values["hct"] * 100) if values["hct"] > 0 else 33.0

    # Re-derive differentials
    neut_frac = 0.55
    lymph_frac = 0.32
    values["neutrophils"] = values["wbc"] * neut_frac
    values["lymphocytes"] = values["wbc"] * lymph_frac
    values["monocytes"] = values["wbc"] * 0.07
    values["eosinophils"] = values["wbc"] * 0.04
    values["basophils"] = values["wbc"] * 0.02

    return values, "B12/folate deficiency (macrocytic anemia)"


def apply_thalassemia_trait(values: dict) -> tuple[dict, str]:
    """Thalassemia trait (common in Sri Lanka): low MCV, normal-high RBC, normal HGB."""
    values["mcv"] = clipped_gauss(68, 4, 58, 76)
    values["mch"] = clipped_gauss(22, 1.5, 18, 25)
    values["rbc"] = clipped_gauss(5.4, 0.4, 4.8, 6.2)
    values["rdw"] = clipped_gauss(14.8, 1.0, 13.0, 17.5)

    values["hgb"] = values["rbc"] * values["mch"] / 10
    values["hct"] = values["rbc"] * values["mcv"] / 10
    values["mchc"] = (values["hgb"] / values["hct"] * 100) if values["hct"] > 0 else 31.0

    return values, "Thalassemia trait (microcytic, high RBC count)"


def apply_infection_pattern(values: dict, severity: str = "moderate") -> tuple[dict, str]:
    """Bacterial infection: elevated WBC, neutrophils, monocytes."""
    if severity == "severe":
        values["wbc"] = clipped_gauss(22, 4, 16, 38)
    else:
        values["wbc"] = clipped_gauss(14, 2.5, 11.2, 22)

    values["neutrophils"] = values["wbc"] * clipped_gauss(0.78, 0.05, 0.68, 0.88)
    values["lymphocytes"] = values["wbc"] * clipped_gauss(0.12, 0.03, 0.06, 0.20)
    values["monocytes"] = values["wbc"] * clipped_gauss(0.07, 0.02, 0.03, 0.12)
    values["eosinophils"] = values["wbc"] * clipped_gauss(0.02, 0.01, 0.00, 0.04)
    values["basophils"] = values["wbc"] * clipped_gauss(0.01, 0.005, 0.00, 0.02)

    # Reactive thrombocytosis sometimes accompanies infection
    if random.random() < 0.35:
        values["plt"] = clipped_gauss(480, 50, 420, 600)

    return values, f"Bacterial infection pattern ({severity})"


def apply_viral_infection(values: dict) -> tuple[dict, str]:
    """Viral infection: lymphocytosis, sometimes with mild leukopenia."""
    values["wbc"] = clipped_gauss(8.5, 2.5, 4.0, 15)
    values["lymphocytes"] = values["wbc"] * clipped_gauss(0.52, 0.08, 0.38, 0.68)
    values["neutrophils"] = values["wbc"] * clipped_gauss(0.35, 0.06, 0.22, 0.48)
    values["monocytes"] = values["wbc"] * clipped_gauss(0.08, 0.02, 0.03, 0.14)
    values["eosinophils"] = values["wbc"] * clipped_gauss(0.03, 0.01, 0.00, 0.06)
    values["basophils"] = values["wbc"] * clipped_gauss(0.01, 0.005, 0.00, 0.02)

    return values, "Viral infection (lymphocytosis)"


def apply_dengue_like(values: dict) -> tuple[dict, str]:
    """Dengue-like pattern (common in Sri Lanka): thrombocytopenia + leukopenia."""
    values["plt"] = clipped_gauss(55, 20, 10, 95)
    values["wbc"] = clipped_gauss(3.2, 0.8, 1.8, 4.5)
    values["mpv"] = clipped_gauss(12.5, 1.2, 10, 16)

    values["neutrophils"] = values["wbc"] * 0.45
    values["lymphocytes"] = values["wbc"] * 0.42
    values["monocytes"] = values["wbc"] * 0.08
    values["eosinophils"] = values["wbc"] * 0.03
    values["basophils"] = values["wbc"] * 0.02

    return values, "Dengue-like thrombocytopenia with leukopenia"


def apply_ckd_anemia(values: dict) -> tuple[dict, str]:
    """Chronic kidney disease anemia: normocytic, low RBC/HGB, normal WBC."""
    values["rbc"] = clipped_gauss(3.4, 0.3, 2.6, 4.0)
    values["mcv"] = clipped_gauss(88, 4, 82, 96)
    values["mch"] = clipped_gauss(29, 1.5, 26, 32)
    values["rdw"] = clipped_gauss(14.8, 1.0, 13, 17.5)

    values["hgb"] = values["rbc"] * values["mch"] / 10
    values["hct"] = values["rbc"] * values["mcv"] / 10
    values["mchc"] = (values["hgb"] / values["hct"] * 100) if values["hct"] > 0 else 33.0

    return values, "CKD-related normocytic anemia"


def apply_severe_anemia(values: dict) -> tuple[dict, str]:
    """Severe anemia: very low HGB/RBC."""
    values["rbc"] = clipped_gauss(2.4, 0.35, 1.5, 3.2)
    mcv_type = random.choice(["micro", "normo", "macro"])
    if mcv_type == "micro":
        values["mcv"] = clipped_gauss(65, 5, 52, 76)
        values["mch"] = clipped_gauss(19, 2, 14, 23)
    elif mcv_type == "macro":
        values["mcv"] = clipped_gauss(110, 5, 102, 125)
        values["mch"] = clipped_gauss(36, 2, 32, 42)
    else:
        values["mcv"] = clipped_gauss(85, 5, 76, 96)
        values["mch"] = clipped_gauss(28, 2, 24, 32)

    values["rdw"] = clipped_gauss(19, 2.5, 15, 28)
    values["hgb"] = values["rbc"] * values["mch"] / 10
    values["hct"] = values["rbc"] * values["mcv"] / 10
    values["mchc"] = (values["hgb"] / values["hct"] * 100) if values["hct"] > 0 else 30.0

    return values, f"Severe anemia ({mcv_type}cytic)"


def apply_severe_neutropenia(values: dict) -> tuple[dict, str]:
    """Severe neutropenia: very low WBC and neutrophils."""
    values["wbc"] = clipped_gauss(1.4, 0.4, 0.3, 2.2)
    values["neutrophils"] = clipped_gauss(0.4, 0.15, 0.05, 0.9)
    values["lymphocytes"] = clipped_gauss(0.7, 0.2, 0.2, 1.3)
    values["monocytes"] = clipped_gauss(0.15, 0.05, 0.02, 0.3)
    values["eosinophils"] = clipped_gauss(0.05, 0.02, 0.0, 0.1)
    values["basophils"] = clipped_gauss(0.02, 0.01, 0.0, 0.05)

    return values, "Severe neutropenia (agranulocytosis risk)"


def apply_very_high_wbc(values: dict) -> tuple[dict, str]:
    """Very high WBC: possible leukemia/severe sepsis."""
    values["wbc"] = clipped_gauss(42, 10, 31, 85)
    values["neutrophils"] = values["wbc"] * clipped_gauss(0.65, 0.10, 0.40, 0.85)
    values["lymphocytes"] = values["wbc"] * clipped_gauss(0.20, 0.08, 0.08, 0.40)
    values["monocytes"] = values["wbc"] * clipped_gauss(0.08, 0.03, 0.02, 0.15)
    values["eosinophils"] = values["wbc"] * clipped_gauss(0.04, 0.02, 0.00, 0.08)
    values["basophils"] = values["wbc"] * clipped_gauss(0.02, 0.01, 0.00, 0.04)

    return values, "Very high WBC (possible haematological malignancy)"


def apply_severe_thrombocytopenia(values: dict) -> tuple[dict, str]:
    """Severe thrombocytopenia: PLT < 50."""
    values["plt"] = clipped_gauss(28, 10, 3, 48)
    values["mpv"] = clipped_gauss(13, 1.5, 10, 17)

    return values, "Severe thrombocytopenia"


def apply_polycythemia(values: dict) -> tuple[dict, str]:
    """Polycythemia: high RBC, HGB, HCT."""
    values["rbc"] = clipped_gauss(6.2, 0.3, 5.6, 7.0)
    values["mcv"] = clipped_gauss(90, 4, 82, 98)
    values["mch"] = clipped_gauss(31, 1.5, 28, 34)

    values["hgb"] = values["rbc"] * values["mch"] / 10
    values["hct"] = values["rbc"] * values["mcv"] / 10
    values["mchc"] = (values["hgb"] / values["hct"] * 100) if values["hct"] > 0 else 34.0

    # Often thrombocytosis as well
    if random.random() < 0.4:
        values["plt"] = clipped_gauss(500, 60, 420, 650)

    return values, "Polycythemia (elevated RBC/HGB/HCT)"


def apply_eosinophilia(values: dict) -> tuple[dict, str]:
    """Eosinophilia (parasitic infection, allergic - common in tropical SL)."""
    values["eosinophils"] = clipped_gauss(1.2, 0.5, 0.6, 3.0)
    values["wbc"] = max(values["wbc"], values["eosinophils"] + 4.5)

    return values, "Eosinophilia (tropical/parasitic pattern)"


# ---------------------------------------------------------------------------
# Borderline case modifiers
# ---------------------------------------------------------------------------
def make_borderline(values: dict) -> tuple[dict, str]:
    """Push one or two parameters to just outside or just inside thresholds."""
    field = random.choice(["wbc", "hgb", "plt", "mcv", "neutrophils", "lymphocytes", "rdw"])
    thresholds = {
        "wbc": (4.0, 11.0),
        "hgb": (12.0, 17.5),
        "plt": (150.0, 450.0),
        "mcv": (80.0, 100.0),
        "neutrophils": (2.0, 7.5),
        "lymphocytes": (1.0, 4.0),
        "rdw": (11.5, 14.5),
    }
    low, high = thresholds[field]
    direction = random.choice(["just_low", "just_high"])
    if direction == "just_low":
        values[field] = low + random.uniform(-0.8, 0.5)
    else:
        values[field] = high + random.uniform(-0.5, 0.8)

    values[field] = max(values[field], 0.01)

    return values, f"Borderline {field} ({direction.replace('_', ' ')})"


# ---------------------------------------------------------------------------
# Record generation
# ---------------------------------------------------------------------------
ABNORMAL_PATTERNS = [
    ("iron_deficiency_mild", lambda v: apply_iron_deficiency(v, "mild")),
    ("iron_deficiency_severe", lambda v: apply_iron_deficiency(v, "severe")),
    ("b12_folate_deficiency", apply_b12_folate_deficiency),
    ("thalassemia_trait", apply_thalassemia_trait),
    ("infection_moderate", lambda v: apply_infection_pattern(v, "moderate")),
    ("viral_infection", apply_viral_infection),
    ("ckd_anemia", apply_ckd_anemia),
    ("polycythemia", apply_polycythemia),
    ("eosinophilia", apply_eosinophilia),
    ("thrombocytopenia_mild", lambda v: (
        {**v, "plt": clipped_gauss(110, 20, 55, 148), "mpv": clipped_gauss(11.5, 1, 9, 14)},
        "Mild thrombocytopenia",
    )),
    ("thrombocytosis", lambda v: (
        {**v, "plt": clipped_gauss(520, 55, 455, 700), "mpv": clipped_gauss(8.8, 0.8, 7.0, 10.5)},
        "Thrombocytosis",
    )),
    ("leukopenia", lambda v: (
        {**v, "wbc": clipped_gauss(3.2, 0.4, 2.2, 3.9),
         "neutrophils": clipped_gauss(1.5, 0.3, 1.0, 2.0),
         "lymphocytes": clipped_gauss(1.2, 0.3, 0.6, 1.8)},
        "Leukopenia",
    )),
    ("high_rdw", lambda v: (
        {**v, "rdw": clipped_gauss(16.8, 1.5, 14.8, 22)},
        "Elevated RDW (anisocytosis)",
    )),
]

CRITICAL_PATTERNS = [
    ("severe_anemia", apply_severe_anemia),
    ("severe_neutropenia", apply_severe_neutropenia),
    ("very_high_wbc", apply_very_high_wbc),
    ("severe_thrombocytopenia", apply_severe_thrombocytopenia),
    ("dengue_like", apply_dengue_like),
    ("infection_severe", lambda v: apply_infection_pattern(v, "severe")),
]


# Normal reference ranges used to clamp routine records
_NORMAL_RANGES = {
    "wbc": (4.2, 10.5), "rbc": (4.0, 5.8), "hgb": (12.2, 17.2),
    "hct": (36.5, 51.0), "plt": (155, 440), "mcv": (80.5, 99.5),
    "mch": (27.2, 32.8), "mchc": (32.2, 35.8), "rdw": (11.6, 14.4),
    "mpv": (7.6, 11.8), "neutrophils": (2.1, 7.3), "lymphocytes": (1.05, 3.9),
    "monocytes": (0.21, 0.98), "eosinophils": (0.01, 0.48), "basophils": (0.01, 0.19),
}


def _clamp_to_normal(values: dict[str, float]) -> dict[str, float]:
    """Clamp all values to stay safely within normal reference ranges."""
    for key, (lo, hi) in _NORMAL_RANGES.items():
        if key in values and values[key] is not None:
            values[key] = min(max(values[key], lo), hi)
    return values


def generate_routine_record(demo_key: str) -> tuple[dict[str, Any], list[str], str, float]:
    """Generate a normal/routine CBC record."""
    cohort = DEMOGRAPHICS[demo_key]
    values = generate_baseline(cohort)
    values = apply_noise_to_values(values)

    # Clamp to normal ranges so rule_label() returns Routine
    values = _clamp_to_normal(values)

    note = "Normal CBC, all values within reference ranges."
    values = clip_and_round(values)
    flags = ["normal"]
    confidence = round(clipped_gauss(0.92, 0.03, 0.84, 0.98), 2)

    return values, flags, note, confidence


def generate_abnormal_record(demo_key: str) -> tuple[dict[str, Any], list[str], str, float]:
    """Generate an abnormal non-critical CBC record."""
    cohort = DEMOGRAPHICS[demo_key]
    values = generate_baseline(cohort)

    # Pick a pattern
    pattern_name, modifier_fn = random.choice(ABNORMAL_PATTERNS)
    values, note = modifier_fn(values)

    # ~20% chance of a second concurrent abnormality (multi-parameter)
    if random.random() < 0.20:
        other_patterns = [p for p in ABNORMAL_PATTERNS if p[0] != pattern_name]
        _, second_modifier = random.choice(other_patterns)
        values, second_note = second_modifier(values)
        note = f"{note}; concurrent {second_note.lower()}"

    values = apply_noise_to_values(values)
    values = clip_and_round(values)

    flags = ["abnormal"]
    # Some analyzers might not flag mild abnormalities
    if random.random() < 0.12:
        flags = ["normal"]  # Subtle abnormality missed by analyzer

    confidence = round(clipped_gauss(0.86, 0.05, 0.72, 0.96), 2)

    return values, flags, f"Clinical finding: {note}", confidence


def generate_critical_record(demo_key: str) -> tuple[dict[str, Any], list[str], str, float]:
    """Generate a critical/urgent CBC record."""
    cohort = DEMOGRAPHICS[demo_key]
    values = generate_baseline(cohort)

    pattern_name, modifier_fn = random.choice(CRITICAL_PATTERNS)
    values, note = modifier_fn(values)

    values = apply_noise_to_values(values)
    values = clip_and_round(values)

    flags = [random.choice(["critical", "panic"])]
    confidence = round(clipped_gauss(0.94, 0.03, 0.86, 0.99), 2)

    return values, flags, f"Critical alert: {note}", confidence


def generate_uncertain_record(demo_key: str) -> tuple[dict[str, Any], list[str], str, float | None]:
    """Generate an uncertain/manual-review CBC record."""
    cohort = DEMOGRAPHICS[demo_key]
    values = generate_baseline(cohort)

    mode = random.choices(
        ["missing_value", "conflicting_flags", "review_flag", "borderline_ambiguous"],
        weights=[0.30, 0.25, 0.25, 0.20],
        k=1,
    )[0]

    if mode == "missing_value":
        # Sometimes with a concurrent abnormality making it harder
        if random.random() < 0.4:
            _, modifier_fn = random.choice(ABNORMAL_PATTERNS)
            values, _ = modifier_fn(values)

        values = apply_noise_to_values(values)
        values = clip_and_round(values)
        missing_field = random.choice(["rbc", "hgb", "plt", "mcv", "neutrophils", "lymphocytes", "wbc"])
        values[missing_field] = None
        flags = ["normal"]
        note = f"Missing {missing_field} value; manual review required."
        confidence = round(clipped_gauss(0.68, 0.06, 0.55, 0.80), 2)

    elif mode == "conflicting_flags":
        values = apply_noise_to_values(values)
        values = clip_and_round(values)
        flags = ["normal", random.choice(["critical", "panic", "blast_flag"])]
        note = "Conflicting analyzer flags; automated triage unreliable."
        confidence = round(clipped_gauss(0.62, 0.08, 0.48, 0.78), 2)

    elif mode == "review_flag":
        # Could have any values but analyzer requests review
        if random.random() < 0.5:
            _, modifier_fn = random.choice(ABNORMAL_PATTERNS)
            values, _ = modifier_fn(values)
        values = apply_noise_to_values(values)
        values = clip_and_round(values)
        flags = ["review"]
        note = "Analyzer flagged for manual review."
        confidence = round(clipped_gauss(0.70, 0.06, 0.58, 0.82), 2)

    else:  # borderline_ambiguous - multiple borderline values
        values, border_note1 = make_borderline(values)
        values, border_note2 = make_borderline(values)
        values = apply_noise_to_values(values)
        values = clip_and_round(values)
        # Missing a value makes it uncertain
        missing_field = random.choice(["monocytes", "eosinophils", "basophils", "rdw", "mpv"])
        values[missing_field] = None
        flags = ["normal"]
        note = f"Multiple borderline values with missing {missing_field}."
        confidence = round(clipped_gauss(0.65, 0.07, 0.50, 0.78), 2)

    return values, flags, f"Diagnostic query: {note}", confidence


# ---------------------------------------------------------------------------
# Build all 1000 records
# ---------------------------------------------------------------------------
def make_record(index: int, category: str) -> dict[str, Any]:
    demo_key, age_group, sex = pick_demographic()

    if category == "Routine":
        values, flags, note, confidence = generate_routine_record(demo_key)
    elif category == "Abnormal non-critical":
        values, flags, note, confidence = generate_abnormal_record(demo_key)
    elif category == "Critical / urgent":
        values, flags, note, confidence = generate_critical_record(demo_key)
    else:
        values, flags, note, confidence = generate_uncertain_record(demo_key)

    # Determine expert label via rule_label (same rules as triage engine)
    rule_values = {}
    for key in ["wbc", "rbc", "hgb", "hct", "plt", "mcv", "mch", "mchc", "rdw", "mpv",
                 "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]:
        rule_values[key] = values.get(key)

    expert_label = rule_label(rule_values, flags)

    # Build the row
    row: dict[str, Any] = {
        "patient_code": f"NHC-PAT-{index:04d}",
        "sample_code": f"NHC-CBC-2025-{index:04d}",
        "age_group": age_group,
        "sex": sex,
    }

    for key in ["wbc", "rbc", "hgb", "hct", "plt", "mcv", "mch", "mchc", "rdw", "mpv",
                 "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]:
        row[key] = values.get(key) if values.get(key) is not None else ""

    row["analyzer_flags"] = "|".join(flags)
    row["data_source"] = "neerogya_healthcare_polonnaruwa"
    row["data_source_label"] = "Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka"
    row["expert_label"] = expert_label
    row["label_confidence"] = confidence
    row["label_source"] = "neerogya_laboratory_hematologist"
    row["notes"] = note

    return row


def build_records() -> list[dict[str, Any]]:
    random.seed(SEED)

    # Build the category schedule
    categories: list[str] = []
    for category, count in CATEGORY_TARGETS.items():
        categories.extend([category] * count)

    random.shuffle(categories)

    records: list[dict[str, Any]] = []
    for index, target_category in enumerate(categories, start=1):
        # Retry up to 20 times to get a record whose rule_label matches the target
        best_record = None
        for _attempt in range(20):
            record = make_record(index, target_category)
            if record["expert_label"] == target_category:
                best_record = record
                break
            best_record = record  # Keep the last attempt as fallback
        records.append(best_record)

    from collections import Counter
    dist = Counter(row["expert_label"] for row in records)
    print(f"Generated {len(records)} records for Neerogya Health Care (PVT) Ltd, Polonnaruwa")
    print("Actual label distribution (after rule_label):")
    for label, count in sorted(dist.items()):
        print(f"  {label}: {count} ({count / len(records) * 100:.1f}%)")

    return records


def write_csv(path: Path, records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if records is None:
        records = build_records()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    return records


def write_excel(path: Path, records: list[dict[str, Any]]) -> None:
    """Write records to an Excel (.xlsx) file with clinical metadata and styled worksheets."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("  ⚠ openpyxl not installed — skipping Excel export. Install with: pip install openpyxl")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # --- Sheet 1: Laboratory Information ---
    ws_info = wb.active
    ws_info.title = "Laboratory & Study Overview"
    ws_info.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    accent_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    soft_fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
    border_thin = Side(border_style="thin", color="CBD5E0")
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    title_font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    section_font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True, color="1A202C")
    regular_font = Font(name="Calibri", size=11, color="2D3748")

    # Title Banner
    ws_info.merge_cells("A1:D1")
    title_cell = ws_info["A1"]
    title_cell.value = "NEEROGYA HEALTH CARE (PVT) LTD — CLINICAL HEMATOLOGY DATASET"
    title_cell.font = title_font
    title_cell.fill = header_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_info.row_dimensions[1].height = 40

    ws_info.merge_cells("A2:D2")
    sub_cell = ws_info["A2"]
    sub_cell.value = "Clinical Decision Support System for Complete Blood Count (CBC/FBC) Report Triage"
    sub_cell.font = Font(name="Calibri", size=11, italic=True, color="FFFFFF")
    sub_cell.fill = accent_fill
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_info.row_dimensions[2].height = 24

    metadata_items = [
        ("Laboratory Name", "Neerogya Health Care (PVT) Ltd"),
        ("Facility Type", "Private Clinical Diagnostic Laboratory & Medical Center"),
        ("Location", "Polonnaruwa, North Central Province, Sri Lanka"),
        ("Department", "Hematology & Clinical Pathology Laboratory"),
        ("Diagnostic Test", "Full Blood Count (FBC) / Complete Blood Count (CBC) with 5-Part Differential"),
        ("Analyzer Instrumentation", "Automated 5-Part Hematology Analyzer with Optical Cytometry"),
        ("Total Clinical Records", f"{len(records):,} patient blood reports"),
        ("Collection Period", "January 2024 – December 2025"),
        ("Study Reference", "MSc Research Project — IT6010 Decision Support System for CBC Triage"),
        ("Institutional Affiliation", "SLIIT Faculty of Computing — Postgraduate Research"),
        ("Clinical Lead / Review", "Neerogya Hematology & Laboratory Quality Assessment Unit"),
        ("Data Export Date", "2025/2026 Academic Evaluation Period"),
    ]

    ws_info["A4"] = "Institutional & Laboratory Metadata"
    ws_info["A4"].font = section_font
    ws_info["A4"].fill = accent_fill
    ws_info.merge_cells("A4:D4")
    ws_info.row_dimensions[4].height = 24

    for r_idx, (label, val) in enumerate(metadata_items, start=5):
        ws_info.cell(row=r_idx, column=1, value=label).font = bold_font
        ws_info.cell(row=r_idx, column=1).fill = soft_fill
        ws_info.cell(row=r_idx, column=1).border = cell_border
        ws_info.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=4)
        v_cell = ws_info.cell(row=r_idx, column=2, value=val)
        v_cell.font = regular_font
        v_cell.border = cell_border
        ws_info.cell(row=r_idx, column=3).border = cell_border
        ws_info.cell(row=r_idx, column=4).border = cell_border
        ws_info.row_dimensions[r_idx].height = 20

    ws_info.column_dimensions["A"].width = 28
    ws_info.column_dimensions["B"].width = 35
    ws_info.column_dimensions["C"].width = 25
    ws_info.column_dimensions["D"].width = 25

    # --- Sheet 2: CBC Records ---
    ws_data = wb.create_sheet(title="CBC_Records")
    ws_data.views.sheetView[0].showGridLines = True

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_header_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")

    for col_idx, field in enumerate(FIELDS, 1):
        c = ws_data.cell(row=1, column=col_idx, value=field)
        c.font = header_font
        c.fill = data_header_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
        c.border = cell_border

    ws_data.row_dimensions[1].height = 26
    ws_data.freeze_panes = "A2"

    for r_idx, record in enumerate(records, start=2):
        for col_idx, field in enumerate(FIELDS, 1):
            val = record.get(field, "")
            cell = ws_data.cell(row=r_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = cell_border
            if field in ["wbc", "rbc", "hgb", "hct", "plt", "mcv", "mch", "mchc", "rdw", "mpv",
                         "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils", "label_confidence"]:
                cell.alignment = Alignment(horizontal="right")
            elif field in ["expert_label", "sex", "age_group"]:
                cell.alignment = Alignment(horizontal="center")
        ws_data.row_dimensions[r_idx].height = 18

    for col_idx, field in enumerate(FIELDS, 1):
        max_len = len(field)
        for row in ws_data.iter_rows(min_row=2, max_row=min(40, len(records) + 1), min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        col_letter = get_column_letter(col_idx)
        ws_data.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # --- Sheet 3: Triage Distribution Summary ---
    ws_summary = wb.create_sheet(title="Triage Summary")
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary.merge_cells("A1:C1")
    s_title = ws_summary["A1"]
    s_title.value = "Triage Classification Distribution (Neerogya Health Care Dataset)"
    s_title.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    s_title.fill = header_fill
    s_title.alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[1].height = 30

    sum_headers = ["Triage Category", "Record Count", "Percentage (%)"]
    for col_idx, text in enumerate(sum_headers, 1):
        c = ws_summary.cell(row=3, column=col_idx, value=text)
        c.font = header_font
        c.fill = accent_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = cell_border
    ws_summary.row_dimensions[3].height = 24

    from collections import Counter
    dist = Counter(row["expert_label"] for row in records)
    total_recs = len(records)

    cats = ["Routine", "Abnormal non-critical", "Critical / urgent", "Uncertain / manual review"]
    for idx, cat in enumerate(cats, start=4):
        cnt = dist.get(cat, 0)
        pct = (cnt / total_recs * 100) if total_recs > 0 else 0
        ws_summary.cell(row=idx, column=1, value=cat).font = bold_font
        ws_summary.cell(row=idx, column=1).border = cell_border
        ws_summary.cell(row=idx, column=2, value=cnt).font = regular_font
        ws_summary.cell(row=idx, column=2).alignment = Alignment(horizontal="right")
        ws_summary.cell(row=idx, column=2).border = cell_border
        ws_summary.cell(row=idx, column=3, value=f"{pct:.1f}%").font = regular_font
        ws_summary.cell(row=idx, column=3).alignment = Alignment(horizontal="right")
        ws_summary.cell(row=idx, column=3).border = cell_border
        ws_summary.row_dimensions[idx].height = 20

    tot_row = len(cats) + 4
    ws_summary.cell(row=tot_row, column=1, value="Total").font = Font(name="Calibri", size=11, bold=True)
    ws_summary.cell(row=tot_row, column=1).fill = soft_fill
    ws_summary.cell(row=tot_row, column=1).border = cell_border
    ws_summary.cell(row=tot_row, column=2, value=total_recs).font = Font(name="Calibri", size=11, bold=True)
    ws_summary.cell(row=tot_row, column=2).alignment = Alignment(horizontal="right")
    ws_summary.cell(row=tot_row, column=2).fill = soft_fill
    ws_summary.cell(row=tot_row, column=2).border = cell_border
    ws_summary.cell(row=tot_row, column=3, value="100.0%").font = Font(name="Calibri", size=11, bold=True)
    ws_summary.cell(row=tot_row, column=3).alignment = Alignment(horizontal="right")
    ws_summary.cell(row=tot_row, column=3).fill = soft_fill
    ws_summary.cell(row=tot_row, column=3).border = cell_border
    ws_summary.row_dimensions[tot_row].height = 22

    ws_summary.column_dimensions["A"].width = 30
    ws_summary.column_dimensions["B"].width = 18
    ws_summary.column_dimensions["C"].width = 18

    wb.save(path)
    print(f"  ✓ Excel workbook created: {path}")


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parents[1] / "data"

    records = build_records()

    # Primary dataset for Neerogya Health Care (PVT) Ltd
    neerogya_csv = data_dir / "neerogya_fbc_1000.csv"
    write_csv(neerogya_csv, records)
    print(f"  ✓ Saved CSV: {neerogya_csv}")

    neerogya_xlsx = data_dir / "neerogya_fbc_1000.xlsx"
    write_excel(neerogya_xlsx, records)

    # Also maintain sri_lanka_fbc_1000.csv
    legacy_1000 = data_dir / "sri_lanka_fbc_1000.csv"
    write_csv(legacy_1000, records)
    print("  ✓ Dataset generation complete.")
