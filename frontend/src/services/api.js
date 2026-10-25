const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const AI_BASE_URL = import.meta.env.VITE_AI_BASE_URL || 'http://localhost:8001';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message || `Request failed with status ${response.status}`);
  }

  return response.json();
}

async function upload(path, formData) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
    },
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message || `Request failed with status ${response.status}`);
  }

  return response.json();
}

async function aiRequest(path, options = {}) {
  const response = await fetch(`${AI_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || body.message || `AI service request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  listReports: () => request('/fbc-reports'),
  createReport: (payload) => request('/fbc-reports', { method: 'POST', body: JSON.stringify(payload) }),
  getReport: (id) => request(`/fbc-reports/${id}`),
  runTriage: (id) => request(`/fbc-reports/${id}/triage`, { method: 'POST' }),
  addExpertLabel: (id, payload) => request(`/fbc-reports/${id}/expert-label`, { method: 'POST', body: JSON.stringify(payload) }),
  listNodes: () => request('/sna/nodes'),
  createNode: (payload) => request('/sna/nodes', { method: 'POST', body: JSON.stringify(payload) }),
  listEdges: () => request('/sna/edges'),
  createEdge: (payload) => request('/sna/edges', { method: 'POST', body: JSON.stringify(payload) }),
  getMetrics: () => request('/sna/metrics'),
  listDatasets: () => request('/datasets'),
  importDataset: (file, notes = '', sourceType = 'research_deidentified') => {
    const formData = new FormData();
    formData.append('file', file);
    if (notes) formData.append('notes', notes);
    if (sourceType) formData.append('source_type', sourceType);
    return upload('/datasets/import', formData);
  },
  getDatasetSummary: (id) => request(`/datasets/${id}/summary`),
  getLabelSummary: () => request('/labels/summary'),
  saveFeedback: (payload) => request('/evaluation/feedback', { method: 'POST', body: JSON.stringify(payload) }),
  getEvaluationSummary: () => request('/evaluation/summary'),
  getResearchDashboard: () => request('/research-dashboard'),
  getModelInfo: () => aiRequest('/model-info'),
  getModelMetrics: () => aiRequest('/model-metrics'),
  trainModel: () => aiRequest('/train', { method: 'POST', body: JSON.stringify({}) }),
};
