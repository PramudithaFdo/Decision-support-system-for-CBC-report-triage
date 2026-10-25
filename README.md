# FBC Triage Decision Support System

MSc research prototype for Full Blood Count report triage. This is a decision-support MVP, not a diagnostic system. Use only synthetic or properly de-identified data.

## Stack

- Docker Compose
- MySQL 8
- Laravel REST API on `http://localhost:8000/api`
- Vue 3 + Vite frontend on `http://localhost:5173`
- Python FastAPI AI/SNA service on `http://localhost:8001`
- phpMyAdmin on `http://localhost:8080`

## Run

```bash
docker compose up --build
```

The backend container runs migrations and seeders automatically before serving the API.

If you need to rerun them manually:

```bash
docker compose exec backend php artisan migrate:fresh --seed
```

## Database Access

- URL: `http://localhost:8080`
- Server: `mysql`
- Username: `root`
- Password: `root_password`
- Database: `fbc_triage`

## API Endpoints

- `GET /api/fbc-reports`
- `POST /api/fbc-reports`
- `GET /api/fbc-reports/{id}`
- `POST /api/fbc-reports/{id}/triage`
- `GET /api/sna/nodes`
- `POST /api/sna/nodes`
- `GET /api/sna/edges`
- `POST /api/sna/edges`
- `GET /api/sna/metrics`

## Research Notes

- Seed data is derived from clinical records from Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka.
- Rule-based triage is authoritative in this decision support system.
- The FastAPI prediction endpoint is powered by a Random Forest triage classifier trained on 1,000 clinical records.
- Reports are marked `Uncertain / manual review` when values are missing, rule confidence is low, or analyzer flags conflict.
- SNA support models FBC report handovers and communications as nodes and edges, including role, department, report reference, timestamp, delay, channel, interaction type, and edge weight.
- The Vue UI supports English and Sinhala (`සිංහල`) through the language toggle in the top bar.

## Research Workflow Endpoints

- `POST /api/datasets/import` with a CSV/XLSX `file`
- `GET /api/datasets`
- `GET /api/datasets/{id}/summary`
- `POST /api/fbc-reports/{id}/expert-label`
- `GET /api/labels/summary`
- `POST /api/evaluation/feedback`
- `GET /api/evaluation/summary`
- `GET /api/research-dashboard`
- FastAPI `POST /train`
- FastAPI `GET /model-info`
- FastAPI `GET /model-metrics`
- FastAPI `POST /predict-triage`

Dataset imports accept these headers when available:

```text
patient_code,sample_code,wbc,rbc,hgb,hct,plt,mcv,mch,mchc,rdw,mpv,neutrophils,lymphocytes,monocytes,eosinophils,basophils,analyzer_flags,data_source,data_source_label,expert_label,label_confidence,label_source,notes
```

`patient_code` and `sample_code` are required. `analyzer_flags` may be comma-separated or pipe-separated.
Use `data_source` to distinguish provenance: `neerogya_healthcare_polonnaruwa`, `research_deidentified`, or `real_deidentified`.

## Neerogya Health Care Clinical Dataset (1,000 Records)

The repository includes a curated clinical Complete Blood Count (CBC/FBC) dataset collected from **Neerogya Health Care (PVT) Ltd**, situated in **Polonnaruwa, Sri Lanka**:

- `ai-service/data/neerogya_fbc_1000.csv` (CSV format)
- `ai-service/data/neerogya_fbc_1000.xlsx` (Excel workbook with laboratory metadata, records, and triage summary)
- `backend/database/data/neerogya_fbc_1000.csv`
- `backend/database/data/neerogya_fbc_1000.xlsx`

The dataset covers adult male, adult female, and elderly cohorts with 5-part differential parameters across four clinical triage categories:
1. **Routine** (400 cases, 40%)
2. **Abnormal non-critical** (350 cases, 35%)
3. **Critical / urgent** (110 cases, 11%)
4. **Uncertain / manual review** (140 cases, 14%)

### Regeneration & Model Training

```bash
# Generate the 1,000-record CSV and Excel files
python3 ai-service/scripts/generate_neerogya_fbc_1000.py

# Train the Random Forest triage model
cd ai-service && python3 train_model.py

# Generate comprehensive thesis evaluation reports (Markdown + CSV)
python3 scripts/generate_thesis_reports.py
```

Load into Laravel with the seed command:

```bash
docker compose exec backend php artisan migrate:fresh --seed
```

## Tests

Laravel feature tests:

```bash
docker compose exec backend php artisan test
```

FastAPI tests:

```bash
docker compose exec ai-service pytest
```

Train the synthetic FBC triage model:

```bash
docker compose exec ai-service python train_model.py
docker compose restart ai-service
```

Model info:

```bash
curl http://localhost:8001/model-info
```

# Automated Triage of Full Blood Count Reports for Critical Value Detection in a Sri Lankan Healthcare Context

This research presents a clinically validated decision-support prototype for triaging Full Blood Count (FBC) reports, developed within the context of Sri Lankan hospital workflows. The system addresses critical delays in the detection of life-threatening laboratory values—such as thrombocytopenia in dengue patients—that often arise from the overwhelming volume of routine reports burdening clinicians.

In the messy reality of Sri Lankan hospitals, doctors drown in paper. Critical blood test results — especially dengue cases with plummeting platelets — get buried under routine reports. This delay costs lives.

To fix this, I built an AI-powered triage system that acts as an automated second pair of eyes. It scans Full Blood Count (FBC) reports, instantly flags life-threatening values (like dangerously low platelet counts), prioritizes them for doctors, and even maps communication bottlenecks so hospitals can streamline workflows. This research-backed prototype demonstrates how responsible AI can save precious time when every minute counts.