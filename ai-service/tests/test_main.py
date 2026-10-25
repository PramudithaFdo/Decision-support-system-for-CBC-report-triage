from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_predict_triage_returns_placeholder_category():
    response = client.post(
        "/predict-triage",
        json={
            "values": {
                "wbc": 6.1,
                "rbc": 4.7,
                "hgb": 14.2,
                "hct": 42,
                "plt": 260,
                "mcv": 88,
                "mch": 30,
                "mchc": 34,
                "rdw": 13,
                "mpv": 9.5,
                "neutrophils": 3.5,
                "lymphocytes": 2.1,
                "monocytes": 0.5,
                "eosinophils": 0.2,
                "basophils": 0.1,
            },
            "analyzer_flags": ["normal"],
        },
    )

    assert response.status_code == 200
    assert response.json()["category"] == "Routine"


def test_model_info_endpoint_is_available():
    response = client.get("/model-info")

    assert response.status_code == 200
    assert "model_loaded" in response.json()


def test_predict_triage_manual_review_on_missing_values():
    response = client.post(
        "/predict-triage",
        json={
            "values": {
                "wbc": 6.1,
                "rbc": None,
                "hgb": 14.2,
                "hct": 42,
                "plt": 260,
                "mcv": 88,
                "mch": 30,
                "mchc": 34,
                "rdw": 13,
                "mpv": 9.5,
                "neutrophils": 3.5,
                "lymphocytes": 2.1,
                "monocytes": 0.5,
                "eosinophils": 0.2,
                "basophils": 0.1,
            },
            "analyzer_flags": ["normal"],
        },
    )

    assert response.status_code == 200
    assert response.json()["category"] == "Uncertain / manual review"


def test_sna_metrics_counts_degrees():
    response = client.post(
        "/sna/metrics",
        json={
            "nodes": [
                {"id": 1, "label": "Lab", "role": "Scientist"},
                {"id": 2, "label": "Ward", "role": "Clinician"},
            ],
            "edges": [
                {"source": 1, "target": 2, "interaction_type": "handover", "weight": 2}
            ],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["degree"]["1"]["out_degree"] == 1
    assert body["degree"]["2"]["in_degree"] == 1
    assert body["interaction_counts"]["handover"] == 2
    assert "betweenness_centrality" in body
    assert "density" in body
    assert "bottleneck_candidates" in body


def test_train_and_model_metrics_endpoints():
    response = client.post("/train")

    assert response.status_code == 200
    assert response.json()["model_loaded"] is True
    assert "macro_f1" in response.json()["metrics"]
    assert response.json()["metrics"]["training_data"] == "neerogya_healthcare_fbc_1000"
    assert response.json()["metrics"]["dataset_size"] == 1000
    assert response.json()["metrics"]["real_patient_data"] is True

    metrics_response = client.get("/model-metrics")

    assert metrics_response.status_code == 200
    assert "confusion_matrix" in metrics_response.json()
    assert metrics_response.json()["training_data"] == "neerogya_healthcare_fbc_1000"
