<script setup>
import { computed, onMounted, ref } from 'vue';
import { useI18n } from './i18n';
import { api } from './services/api';
import ReportsView from './views/ReportsView.vue';
import ResearchView from './views/ResearchView.vue';
import SnaView from './views/SnaView.vue';

const { language, setLanguage, t } = useI18n();
const activeView = ref('reports');
const reports = ref([]);
const selectedReportId = ref(null);
const loading = ref(false);
const error = ref('');

const selectedReport = computed(() => reports.value.find((report) => report.id === selectedReportId.value) || reports.value[0] || null);

async function loadReports() {
  loading.value = true;
  error.value = '';
  try {
    reports.value = await api.listReports();
    if (!selectedReportId.value && reports.value.length) {
      selectedReportId.value = reports.value[0].id;
    }
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function createReport(payload) {
  error.value = '';
  try {
    const report = await api.createReport(payload);
    await loadReports();
    selectedReportId.value = report.id;
  } catch (err) {
    error.value = err.message;
  }
}

async function runTriage(reportId) {
  error.value = '';
  try {
    await api.runTriage(reportId);
    await loadReports();
    selectedReportId.value = reportId;
  } catch (err) {
    error.value = err.message;
  }
}

async function addExpertLabel({ reportId, payload }) {
  error.value = '';
  try {
    await api.addExpertLabel(reportId, payload);
    await loadReports();
    selectedReportId.value = reportId;
  } catch (err) {
    error.value = err.message;
  }
}

onMounted(loadReports);
</script>

<template>
  <div class="shell" :lang="language">
    <header class="topbar">
      <div>
        <p class="eyebrow">{{ t('decisionSupportNotice') }}</p>
        <h1>{{ t('triageTitle') }}</h1>
      </div>
      <div class="topbar-actions">
        <nav class="tabs" aria-label="Primary">
          <button :class="{ active: activeView === 'reports' }" @click="activeView = 'reports'">{{ t('fbcReports') }}</button>
          <button :class="{ active: activeView === 'sna' }" @click="activeView = 'sna'">{{ t('snaWorkflow') }}</button>
          <button :class="{ active: activeView === 'research' }" @click="activeView = 'research'">{{ t('researchDashboard') }}</button>
        </nav>
        <div class="language-toggle" :aria-label="t('language')">
          <button :class="{ active: language === 'en' }" @click="setLanguage('en')">{{ t('english') }}</button>
          <button :class="{ active: language === 'si' }" @click="setLanguage('si')">{{ t('sinhala') }}</button>
        </div>
      </div>
    </header>

    <main>
      <p v-if="error" class="alert">{{ error }}</p>
      <ReportsView
        v-if="activeView === 'reports'"
        :reports="reports"
        :selected-report="selectedReport"
        :loading="loading"
        @select="selectedReportId = $event"
        @refresh="loadReports"
        @create="createReport"
        @triage="runTriage"
        @label="addExpertLabel"
      />
      <SnaView v-else-if="activeView === 'sna'" />
      <ResearchView v-else />
    </main>
  </div>
</template>
