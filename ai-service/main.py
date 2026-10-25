import json
from typing import Any

import networkx as nx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from modeling import METRICS_PATH, extract_features, load_model, rule_label
from train_model import train


app = FastAPI(
    title="FBC AI and SNA Service",
    description="Trained clinical ML prediction and social network metrics for FBC triage research prototype.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_BUNDLE = load_model()


class PredictionRequest(BaseModel):
    values: dict[str, float | None]
    analyzer_flags: list[str] = Field(default_factory=list)


class Node(BaseModel):
    id: int
    label: str
    role: str | None = None


class Edge(BaseModel):
    source: int
    target: int
    interaction_type: str = "handover"
    channel: str | None = None
    delay_minutes: int | None = None
    weight: int = 1


class MetricsRequest(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "fbc-ai-sna",
        "model_loaded": MODEL_BUNDLE is not None,
    }


@app.get("/model-info")
def model_info() -> dict[str, Any]:
    if MODEL_BUNDLE is None:
        return {
            "model_loaded": False,
            "decision_support_notice": "No trained model artifact found. Run python train_model.py inside ai-service.",
        }

    metrics = MODEL_BUNDLE.get("metrics", {})
    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    return {
        "model_loaded": True,
        "model_type": metrics.get("model_type"),
        "training_data": metrics.get("training_data"),
        "dataset_size": metrics.get("dataset_size") or metrics.get("sample_count"),
        "real_patient_data": metrics.get("real_patient_data", False),
        "source_notice": metrics.get("source_notice"),
        "class_distribution": metrics.get("class_distribution"),
        "accuracy": metrics.get("accuracy"),
        "sample_count": metrics.get("sample_count"),
        "decision_support_notice": metrics.get("decision_support_notice"),
    }


@app.get("/model-metrics")
def model_metrics() -> dict[str, Any]:
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    return {"model_loaded": False, "message": "No metrics artifact found. Run /train or python train_model.py."}


@app.post("/train")
def train_endpoint() -> dict[str, Any]:
    global MODEL_BUNDLE
    metrics = train()
    MODEL_BUNDLE = load_model()

    return {"model_loaded": MODEL_BUNDLE is not None, "metrics": metrics}


@app.post("/predict-triage")
def predict_triage(payload: PredictionRequest) -> dict[str, Any]:
    missing = [key for key, value in payload.values.items() if value is None]
    flags = {flag.lower() for flag in payload.analyzer_flags}

    if missing:
        return {
            "category": "Uncertain / manual review",
            "confidence": 0.38,
            "explanation": f"Placeholder ML found missing values: {', '.join(missing)}.",
            "source": "uncertainty-override",
        }

    if "normal" in flags and bool({"critical", "panic", "blast_flag"} & flags):
        return {
            "category": "Uncertain / manual review",
            "confidence": 0.36,
            "explanation": "Analyzer flags conflict; manual review is recommended.",
            "source": "uncertainty-override",
        }

    if "review" in flags or "manual_review" in flags:
        return {
            "category": "Uncertain / manual review",
            "confidence": 0.4,
            "explanation": "Analyzer requested manual review.",
            "source": "uncertainty-override",
        }

    if MODEL_BUNDLE is not None:
        features = [extract_features(payload.values, payload.analyzer_flags)]
        pipeline = MODEL_BUNDLE["pipeline"]
        category = pipeline.predict(features)[0]
        probabilities = pipeline.predict_proba(features)[0]
        classes = list(pipeline.classes_)
        confidence = float(probabilities[classes.index(category)])

        if confidence < 0.55:
            return {
                "category": "Uncertain / manual review",
                "confidence": round(confidence, 3),
                "explanation": "Trained synthetic-data model confidence is below the manual-review threshold.",
                "source": "trained-model-low-confidence",
            }

        return {
            "category": category,
            "confidence": round(confidence, 3),
            "explanation": "Trained synthetic-data RandomForest model prediction. Rule-based Laravel triage remains authoritative.",
            "source": "trained-model",
        }

    category = rule_label(payload.values, payload.analyzer_flags)

    if category == "Critical / urgent":
        return {
            "category": "Critical / urgent",
            "confidence": 0.7,
            "explanation": "Fallback rule detected a critical pattern.",
            "source": "fallback-rules",
        }

    if category == "Abnormal non-critical":
        return {
            "category": "Abnormal non-critical",
            "confidence": 0.62,
            "explanation": "Fallback rule detected a non-critical abnormal pattern.",
            "source": "fallback-rules",
        }

    return {
        "category": "Routine",
        "confidence": 0.66,
        "explanation": "Fallback rules detected no obvious abnormal pattern.",
        "source": "fallback-rules",
    }


@app.post("/sna/metrics")
def sna_metrics(payload: MetricsRequest) -> dict[str, Any]:
    graph = nx.DiGraph()
    for node in payload.nodes:
        graph.add_node(node.id, label=node.label, role=node.role)
    for edge in payload.edges:
        graph.add_edge(
            edge.source,
            edge.target,
            weight=edge.weight,
            interaction_type=edge.interaction_type,
            delay_minutes=edge.delay_minutes,
            channel=edge.channel,
        )

    degree: dict[str, dict[str, Any]] = {
        str(node.id): {
            "label": node.label,
            "role": node.role,
            "in_degree": 0,
            "out_degree": 0,
            "weighted_handover_count": 0,
            "weighted_delay_minutes": 0,
        }
        for node in payload.nodes
    }

    interaction_counts: dict[str, int] = {}

    for edge in payload.edges:
        source_key = str(edge.source)
        target_key = str(edge.target)
        if source_key in degree:
            degree[source_key]["out_degree"] += 1
            degree[source_key]["weighted_handover_count"] += edge.weight
            degree[source_key]["weighted_delay_minutes"] += (edge.delay_minutes or 0) * edge.weight
        if target_key in degree:
            degree[target_key]["in_degree"] += 1
        interaction_counts[edge.interaction_type] = interaction_counts.get(edge.interaction_type, 0) + edge.weight

    betweenness = nx.betweenness_centrality(graph, weight="weight", normalized=True) if graph.number_of_nodes() else {}
    closeness = nx.closeness_centrality(graph) if graph.number_of_nodes() else {}
    density = nx.density(graph) if graph.number_of_nodes() else 0
    average_path_length = None
    if graph.number_of_nodes() > 1 and nx.is_weakly_connected(graph):
        average_path_length = nx.average_shortest_path_length(graph.to_undirected())
    communities = list(nx.algorithms.community.greedy_modularity_communities(graph.to_undirected())) if graph.number_of_edges() else []
    modularity = nx.algorithms.community.modularity(graph.to_undirected(), communities) if communities else 0
    bottlenecks = sorted(
        [
            {
                "node_id": node_id,
                "id": node_id,
                "label": graph.nodes[node_id].get("label"),
                "betweenness": round(score, 4),
                "closeness": round(closeness.get(node_id, 0), 4),
                "weighted_delay_minutes": degree.get(str(node_id), {}).get("weighted_delay_minutes", 0),
            }
            for node_id, score in betweenness.items()
        ],
        key=lambda row: row["betweenness"],
        reverse=True,
    )[:5]

    return {
        "node_count": len(payload.nodes),
        "edge_count": len(payload.edges),
        "degree": degree,
        "betweenness_centrality": {str(k): round(v, 4) for k, v in betweenness.items()},
        "closeness_centrality": {str(k): round(v, 4) for k, v in closeness.items()},
        "density": round(density, 4),
        "modularity": round(modularity, 4),
        "average_path_length": round(average_path_length, 4) if average_path_length is not None else None,
        "interaction_counts": interaction_counts,
        "bottleneck_candidates": bottlenecks,
        "source": "fastapi-networkx",
    }
