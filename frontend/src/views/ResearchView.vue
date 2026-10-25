<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from '../i18n';
import { api } from '../services/api';

const { t, category, source } = useI18n();
const datasets = ref([]);
const labelSummary = ref(null);
const evaluationSummary = ref(null);
const researchDashboard = ref(null);
const modelInfo = ref(null);
const modelMetrics = ref(null);
const selectedFile = ref(null);
const importNotes = ref('Research dataset import');
const importSourceType = ref('research_deidentified');
const status = ref('');
const error = ref('');

const feedbackForm = reactive({
  participant_code: 'STAFF-01',
  role: 'Medical laboratory technologist',
  task_time_seconds: 180,
  sus_score: 75,
  trust_score: 4,
  usefulness_score: 4,
  comments: '',
});

const confusionMatrix = computed(() => {
  const source = modelMetrics.value?.confusion_matrix || modelInfo.value?.metrics?.confusion_matrix || [];
  return Array.isArray(source) ? source : source.matrix || [];
});
const metrics = computed(() => modelMetrics.value || modelInfo.value?.metrics || {});
const trainingSource = computed(() => metrics.value?.training_data || modelInfo.value?.training_data || 'n/a');
const datasetSize = computed(() => metrics.value?.dataset_size || modelInfo.value?.dataset_size || metrics.value?.sample_count || 'n/a');
const classDistribution = computed(() => metrics.value?.class_distribution || modelInfo.value?.class_distribution || {});

async function loadResearchData() {
  error.value = '';
  try {
    const [datasetData, labelData, evaluationData, dashboardData, infoData, metricData] = await Promise.all([
      api.listDatasets().catch((e) => { console.warn('Datasets fetch failed:', e); return []; }),
      api.getLabelSummary().catch((e) => { console.warn('Labels summary fetch failed:', e); return null; }),
      api.getEvaluationSummary().catch((e) => { console.warn('Evaluation summary fetch failed:', e); return null; }),
      api.getResearchDashboard().catch((e) => { console.warn('Research dashboard fetch failed:', e); return null; }),
      api.getModelInfo().catch((e) => { console.warn('Model info fetch failed:', e); return null; }),
      api.getModelMetrics().catch(() => null),
    ]);
    datasets.value = datasetData || [];
    labelSummary.value = labelData;
    evaluationSummary.value = evaluationData;
    researchDashboard.value = dashboardData;
    modelInfo.value = infoData;
    modelMetrics.value = metricData;
  } catch (err) {
    error.value = err.message;
  }
}

async function importDataset() {
  if (!selectedFile.value) {
    error.value = t('selectDatasetFile');
    return;
  }
  error.value = '';
  status.value = t('importingDataset');
  try {
    await api.importDataset(selectedFile.value, importNotes.value, importSourceType.value);
    status.value = t('datasetImported');
    selectedFile.value = null;
    await loadResearchData();
  } catch (err) {
    error.value = err.message;
    status.value = '';
  }
}

async function trainModel() {
  error.value = '';
  status.value = t('trainingModel');
  try {
    modelInfo.value = await api.trainModel();
    modelMetrics.value = modelInfo.value.metrics;
    status.value = t('trainingComplete');
  } catch (err) {
    error.value = err.message;
    status.value = '';
  }
}

async function saveFeedback() {
  error.value = '';
  try {
    await api.saveFeedback(feedbackForm);
    feedbackForm.comments = '';
    await loadResearchData();
    status.value = 'Usability feedback saved.';
  } catch (err) {
    error.value = err.message;
  }
}

function handleFile(event) {
  selectedFile.value = event.target.files?.[0] || null;
}

onMounted(loadResearchData);
</script>

<template>
  <section class="research-grid">
    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="status" class="notice">{{ status }}</p>
    <p class="notice"><strong>{{ t('dataSource') }}:</strong> {{ t('clinicalLabNotice') }}</p>

    <div class="panel">
      <h2>{{ t('datasetImport') }}</h2>
      <p class="muted">{{ t('csvImportsNotice') }}</p>
      <div class="metric-row">
        <span>{{ t('dataSource') }}</span>
        <strong>{{ t('neerogyaClinicalData') }}</strong>
      </div>
      <form class="compact-form" @submit.prevent="importDataset">
        <input type="file" accept=".csv,.xlsx" @change="handleFile" />
        <select v-model="importSourceType">
          <option value="neerogya_healthcare_polonnaruwa">{{ t('neerogyaClinicalData') }}</option>
          <option value="research_deidentified">{{ t('researchDeidentifiedData') }}</option>
          <option value="real_deidentified">{{ t('realDeidentifiedData') }}</option>
          <option value="pending_ethics_review">{{ t('pendingEthicsReview') }}</option>
        </select>
        <input v-model="importNotes" :placeholder="t('importNotes')" />
        <button type="submit">{{ t('importDataset') }}</button>
      </form>
      <div v-for="dataset in datasets" :key="dataset.id" class="list-item">
        <strong>{{ dataset.filename }}</strong>
        <span>{{ dataset.imported_count }} imported · {{ dataset.skipped_count }} skipped · {{ source(dataset.source_type) }}</span>
      </div>
    </div>

    <div class="panel">
      <h2>{{ t('modelEvaluation') }}</h2>
      <div class="metric-row">
        <span>{{ t('modelLoaded') }}</span>
        <strong>{{ modelInfo?.model_loaded ? t('yes') : t('no') }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('trainingSource') }}</span>
        <strong>{{ trainingSource }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('datasetSize') }}</span>
        <strong>{{ datasetSize }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('realPatientData') }}</span>
        <strong>{{ metrics?.real_patient_data || modelInfo?.real_patient_data ? t('yes') : t('no') }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('macroF1') }}</span>
        <strong>{{ metrics?.macro_f1 ?? 'n/a' }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('coverage') }}</span>
        <strong>{{ metrics?.coverage ?? 'n/a' }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('deferralRate') }}</span>
        <strong>{{ metrics?.deferral_rate ?? 'n/a' }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('calibrationError') }}</span>
        <strong>{{ metrics?.expected_calibration_error ?? 'n/a' }}</strong>
      </div>
      <button @click="trainModel">{{ t('trainEvaluateModel') }}</button>
      <div v-for="(count, label) in classDistribution" :key="label" class="metric-row">
        <span>{{ category(label) }}</span>
        <strong>{{ count }}</strong>
      </div>
      <div v-if="confusionMatrix.length" class="matrix">
        <span v-for="(value, index) in confusionMatrix.flat()" :key="index">{{ value }}</span>
      </div>
    </div>

    <div class="panel">
      <h2>{{ t('expertLabels') }}</h2>
      <div class="metric-row">
        <span>{{ t('totalLabels') }}</span>
        <strong>{{ labelSummary?.total_labels ?? 0 }}</strong>
      </div>
      <div v-for="(count, label) in labelSummary?.by_label || {}" :key="label" class="metric-row">
        <span>{{ category(label) }}</span>
        <strong>{{ count }}</strong>
      </div>
    </div>

    <div class="panel">
      <h2>{{ t('usabilityEvaluation') }}</h2>
      <form class="compact-form" @submit.prevent="saveFeedback">
        <input v-model="feedbackForm.participant_code" :placeholder="t('participantCode')" required />
        <input v-model="feedbackForm.role" :placeholder="t('staffRole')" required />
        <input v-model.number="feedbackForm.task_time_seconds" type="number" min="0" :placeholder="t('taskTimeSeconds')" />
        <input v-model.number="feedbackForm.sus_score" type="number" min="0" max="100" :placeholder="t('susScore')" />
        <input v-model.number="feedbackForm.trust_score" type="number" min="1" max="5" :placeholder="t('trustScore')" />
        <input v-model.number="feedbackForm.usefulness_score" type="number" min="1" max="5" :placeholder="t('usefulnessScore')" />
        <textarea v-model="feedbackForm.comments" rows="3" :placeholder="t('staffComments')"></textarea>
        <button type="submit">{{ t('saveFeedback') }}</button>
      </form>
      <div class="metric-row">
        <span>{{ t('responses') }}</span>
        <strong>{{ evaluationSummary?.responses ?? 0 }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('averageSus') }}</span>
        <strong>{{ evaluationSummary?.average_sus ?? 'n/a' }}</strong>
      </div>
    </div>

    <div class="panel wide-panel">
      <h2>{{ t('proposalAlignment') }}</h2>
      <div v-for="objective in researchDashboard?.objectives || []" :key="objective.key" class="list-item">
        <strong>{{ objective.key }} · {{ objective.title }}</strong>
        <span>{{ objective.status }} · {{ objective.evidence }}</span>
      </div>
      <div v-for="hypothesis in researchDashboard?.hypotheses || []" :key="hypothesis.key" class="list-item">
        <strong>{{ hypothesis.key }}</strong>
        <span>{{ hypothesis.measure }} · {{ hypothesis.current_output }}</span>
      </div>
    </div>
  </section>
</template>
