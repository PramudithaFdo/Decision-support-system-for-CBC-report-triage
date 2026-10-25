<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from '../i18n';

const { t, category, source } = useI18n();
const props = defineProps({
  reports: { type: Array, required: true },
  selectedReport: { type: Object, default: null },
  loading: { type: Boolean, default: false },
});

const emit = defineEmits(['select', 'refresh', 'create', 'triage', 'label']);

const form = reactive({
  patient_code: 'NHC-PAT-0001',
  sample_code: `FBC-${Date.now()}`,
  wbc: 6.2,
  rbc: 4.7,
  hgb: 14.0,
  hct: 42.0,
  plt: 260,
  mcv: 88.0,
  mch: 30.0,
  mchc: 34.0,
  rdw: 13.0,
  mpv: 9.5,
  neutrophils: 3.4,
  lymphocytes: 2.1,
  monocytes: 0.5,
  eosinophils: 0.2,
  basophils: 0.1,
  analyzer_flags_text: 'normal',
  notes: '',
});

const labelForm = reactive({
  label: 'Routine',
  expert_role: 'Medical laboratory technologist',
  confidence: 0.9,
  rationale: '',
});
const searchText = ref('');
const categoryFilter = ref('all');
const currentPage = ref(1);
const pageSize = 25;

const filteredReports = computed(() => {
  const search = searchText.value.trim().toLowerCase();
  return props.reports.filter((report) => {
    const category = report.triage_result?.category || 'Pending';
    const matchesCategory = categoryFilter.value === 'all' || category === categoryFilter.value;
    const matchesSearch = !search
      || report.sample_code?.toLowerCase().includes(search)
      || report.patient_code?.toLowerCase().includes(search);
    return matchesCategory && matchesSearch;
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredReports.value.length / pageSize)));
const pagedReports = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredReports.value.slice(start, start + pageSize);
});

watch([searchText, categoryFilter], () => {
  currentPage.value = 1;
});

watch(totalPages, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});

function categoryClass(category) {
  if (category === 'Critical / urgent') return 'critical';
  if (category === 'Abnormal non-critical') return 'abnormal';
  if (category === 'Uncertain / manual review') return 'uncertain';
  return 'routine';
}

function valueOrMissing(value) {
  return value ?? t('missing');
}

function submit() {
  emit('create', {
    ...form,
    patient_code: form.patient_code,
    analyzer_flags: form.analyzer_flags_text.split(',').map((flag) => flag.trim()).filter(Boolean),
  });
}

function submitLabel(reportId) {
  emit('label', {
    reportId,
    payload: {
      label: labelForm.label,
      expert_role: labelForm.expert_role,
      confidence: labelForm.confidence,
      rationale: labelForm.rationale,
    },
  });
  labelForm.rationale = '';
}
</script>

<template>
  <section class="workspace-grid">
    <div class="panel">
      <div class="panel-heading">
        <h2>{{ t('reports') }}</h2>
        <button class="ghost" @click="$emit('refresh')">{{ t('refresh') }}</button>
      </div>
      <div class="list-controls">
        <input v-model="searchText" :placeholder="t('searchReports')" />
        <select v-model="categoryFilter">
          <option value="all">{{ t('allCategories') }}</option>
          <option value="Routine">{{ category('Routine') }}</option>
          <option value="Abnormal non-critical">{{ category('Abnormal non-critical') }}</option>
          <option value="Critical / urgent">{{ category('Critical / urgent') }}</option>
          <option value="Uncertain / manual review">{{ category('Uncertain / manual review') }}</option>
          <option value="Pending">{{ category('Pending') }}</option>
        </select>
      </div>
      <p class="muted">{{ filteredReports.length }} {{ t('reportsShown') }} · {{ t('page') }} {{ currentPage }} / {{ totalPages }}</p>
      <p v-if="loading" class="muted">{{ t('loadingReports') }}</p>
      <button
        v-for="report in pagedReports"
        :key="report.id"
        class="report-row"
        :class="{ selected: selectedReport?.id === report.id }"
        @click="$emit('select', report.id)"
      >
        <span>
          <strong>{{ report.sample_code }}</strong>
          <small>{{ report.patient_code }}</small>
          <small class="source-badge" :class="report.data_source">{{ source(report.data_source, report.data_source_label) }}</small>
        </span>
        <span class="badge" :class="categoryClass(report.triage_result?.category)">
          {{ category(report.triage_result?.category || 'Pending') }}
        </span>
      </button>
      <div class="pagination">
        <button class="ghost" :disabled="currentPage === 1" @click="currentPage -= 1">{{ t('previous') }}</button>
        <button class="ghost" :disabled="currentPage === totalPages" @click="currentPage += 1">{{ t('next') }}</button>
      </div>
    </div>

    <div class="panel detail-panel" v-if="selectedReport">
      <div class="panel-heading">
        <div>
          <h2>{{ selectedReport.sample_code }}</h2>
          <p class="muted">{{ t('subjectCode') }}: {{ selectedReport.patient_code }}</p>
          <p class="muted">{{ t('dataSource') }}: {{ source(selectedReport.data_source, selectedReport.data_source_label) }}</p>
        </div>
        <button @click="$emit('triage', selectedReport.id)">{{ t('runTriage') }}</button>
      </div>

      <div class="value-grid">
        <span>WBC <strong>{{ valueOrMissing(selectedReport.wbc) }}</strong></span>
        <span>RBC <strong>{{ valueOrMissing(selectedReport.rbc) }}</strong></span>
        <span>HGB <strong>{{ valueOrMissing(selectedReport.hgb) }}</strong></span>
        <span>HCT <strong>{{ valueOrMissing(selectedReport.hct) }}</strong></span>
        <span>PLT <strong>{{ valueOrMissing(selectedReport.plt) }}</strong></span>
        <span>{{ t('mcv') }} <strong>{{ valueOrMissing(selectedReport.mcv) }}</strong></span>
        <span>{{ t('mch') }} <strong>{{ valueOrMissing(selectedReport.mch) }}</strong></span>
        <span>{{ t('mchc') }} <strong>{{ valueOrMissing(selectedReport.mchc) }}</strong></span>
        <span>RDW <strong>{{ valueOrMissing(selectedReport.rdw) }}</strong></span>
        <span>{{ t('mpv') }} <strong>{{ valueOrMissing(selectedReport.mpv) }}</strong></span>
        <span>{{ t('neutrophils') }} <strong>{{ valueOrMissing(selectedReport.neutrophils) }}</strong></span>
        <span>{{ t('lymphocytes') }} <strong>{{ valueOrMissing(selectedReport.lymphocytes) }}</strong></span>
        <span>{{ t('monocytes') }} <strong>{{ valueOrMissing(selectedReport.monocytes) }}</strong></span>
        <span>{{ t('eosinophils') }} <strong>{{ valueOrMissing(selectedReport.eosinophils) }}</strong></span>
        <span>{{ t('basophils') }} <strong>{{ valueOrMissing(selectedReport.basophils) }}</strong></span>
      </div>

      <div class="result-strip" :class="categoryClass(selectedReport.triage_result?.category)">
        <strong>{{ category(selectedReport.triage_result?.category) }}</strong>
        <span>{{ t('confidence') }} {{ selectedReport.triage_result?.confidence }}</span>
      </div>
      <p>{{ selectedReport.triage_result?.rule_summary }}</p>
      <ul v-if="selectedReport.triage_result?.uncertainty_reasons?.length" class="reason-list">
        <li v-for="reason in selectedReport.triage_result.uncertainty_reasons" :key="reason">{{ t('manualReviewRecommended') }}: {{ reason }}</li>
      </ul>
      <p class="muted">{{ t('analyzerFlags') }}: {{ selectedReport.analyzer_flags?.join(', ') || t('none') }}</p>
      <p class="muted">{{ t('mlPlaceholder') }}: {{ selectedReport.triage_result?.ml_placeholder?.explanation }}</p>

      <form class="compact-form label-form" @submit.prevent="submitLabel(selectedReport.id)">
        <h3>{{ t('expertReviewLabel') }}</h3>
        <div class="form-grid">
          <label>{{ t('reviewedLabel') }}
            <select v-model="labelForm.label" required>
              <option value="Routine">{{ category('Routine') }}</option>
              <option value="Abnormal non-critical">{{ category('Abnormal non-critical') }}</option>
              <option value="Critical / urgent">{{ category('Critical / urgent') }}</option>
              <option value="Uncertain / manual review">{{ category('Uncertain / manual review') }}</option>
            </select>
          </label>
          <label>{{ t('reviewerRole') }} <input v-model="labelForm.expert_role" required /></label>
          <label>{{ t('confidence') }} <input v-model.number="labelForm.confidence" type="number" min="0" max="1" step="0.01" /></label>
        </div>
        <label>{{ t('rationale') }} <textarea v-model="labelForm.rationale" rows="2" :placeholder="t('notes')"></textarea></label>
        <button type="submit">{{ t('saveExpertLabel') }}</button>
      </form>
    </div>

    <form class="panel form-panel" @submit.prevent="submit">
      <h2>{{ t('createReport') }}</h2>
      <label>{{ t('deidentifiedSubjectCode') }} <input v-model="form.patient_code" required /></label>
      <label>Sample code <input v-model="form.sample_code" required /></label>
      <div class="form-grid">
        <label>WBC <input v-model.number="form.wbc" type="number" step="0.01" /></label>
        <label>RBC <input v-model.number="form.rbc" type="number" step="0.01" /></label>
        <label>HGB <input v-model.number="form.hgb" type="number" step="0.01" /></label>
        <label>HCT <input v-model.number="form.hct" type="number" step="0.01" /></label>
        <label>PLT <input v-model.number="form.plt" type="number" step="0.01" /></label>
        <label>MCV <input v-model.number="form.mcv" type="number" step="0.01" /></label>
        <label>MCH <input v-model.number="form.mch" type="number" step="0.01" /></label>
        <label>MCHC <input v-model.number="form.mchc" type="number" step="0.01" /></label>
        <label>RDW <input v-model.number="form.rdw" type="number" step="0.01" /></label>
        <label>MPV <input v-model.number="form.mpv" type="number" step="0.01" /></label>
        <label>{{ t('neutrophils') }} <input v-model.number="form.neutrophils" type="number" step="0.01" /></label>
        <label>{{ t('lymphocytes') }} <input v-model.number="form.lymphocytes" type="number" step="0.01" /></label>
        <label>{{ t('monocytes') }} <input v-model.number="form.monocytes" type="number" step="0.01" /></label>
        <label>{{ t('eosinophils') }} <input v-model.number="form.eosinophils" type="number" step="0.01" /></label>
        <label>{{ t('basophils') }} <input v-model.number="form.basophils" type="number" step="0.01" /></label>
      </div>
      <label>{{ t('analyzerFlags') }} <input v-model="form.analyzer_flags_text" placeholder="normal, abnormal, critical, review" /></label>
      <label>{{ t('notes') }} <textarea v-model="form.notes" rows="3"></textarea></label>
      <button type="submit">{{ t('createAndTriage') }}</button>
    </form>
  </section>
</template>
