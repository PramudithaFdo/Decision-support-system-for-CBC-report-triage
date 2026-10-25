<script setup>
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from '../i18n';
import { api } from '../services/api';

const { t } = useI18n();
const nodes = ref([]);
const edges = ref([]);
const metrics = ref(null);
const error = ref('');

const nodeForm = reactive({ label: 'New Reviewer', role: 'Reviewer', department: 'Laboratory' });
const edgeForm = reactive({
  source_node_id: '',
  target_node_id: '',
  interaction_type: 'handover',
  report_reference: '',
  channel: 'phone',
  delay_minutes: 10,
  occurred_at: '',
  weight: 1,
});

async function loadAll() {
  error.value = '';
  try {
    nodes.value = await api.listNodes();
    edges.value = await api.listEdges();
    metrics.value = await api.getMetrics();
    if (!edgeForm.source_node_id && nodes.value[0]) edgeForm.source_node_id = nodes.value[0].id;
    if (!edgeForm.target_node_id && nodes.value[1]) edgeForm.target_node_id = nodes.value[1].id;
  } catch (err) {
    error.value = err.message;
  }
}

async function addNode() {
  await api.createNode(nodeForm);
  await loadAll();
}

async function addEdge() {
  await api.createEdge(edgeForm);
  await loadAll();
}

onMounted(loadAll);
</script>

<template>
  <section class="sna-grid">
    <p v-if="error" class="alert">{{ error }}</p>

    <div class="panel">
      <h2>{{ t('workflowNodes') }}</h2>
      <div v-for="node in nodes" :key="node.id" class="list-item">
        <strong>{{ node.label }}</strong>
        <span>{{ node.role }} · {{ node.department || t('noDepartment') }}</span>
      </div>
      <form class="compact-form" @submit.prevent="addNode">
        <input v-model="nodeForm.label" placeholder="Label" required />
        <input v-model="nodeForm.role" :placeholder="t('role')" required />
        <input v-model="nodeForm.department" :placeholder="t('department')" />
        <button>{{ t('addNode') }}</button>
      </form>
    </div>

    <div class="panel">
      <h2>{{ t('communications') }}</h2>
      <div v-for="edge in edges" :key="edge.id" class="list-item">
        <strong>{{ edge.source?.label }} → {{ edge.target?.label }}</strong>
        <span>
          {{ edge.interaction_type }} · {{ edge.channel || t('channelUnavailable') }} · {{ edge.report_reference || t('noReportReference') }}
          · {{ t('delay') }} {{ edge.delay_minutes ?? 'n/a' }} {{ t('min') }} · {{ t('weight') }} {{ edge.weight }}
        </span>
      </div>
      <form class="compact-form" @submit.prevent="addEdge">
        <select v-model="edgeForm.source_node_id" required>
          <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.label }}</option>
        </select>
        <select v-model="edgeForm.target_node_id" required>
          <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.label }}</option>
        </select>
        <input v-model="edgeForm.interaction_type" :placeholder="t('interactionType')" required />
        <input v-model="edgeForm.report_reference" :placeholder="t('reportReference')" />
        <input v-model="edgeForm.channel" :placeholder="t('channel')" />
        <input v-model.number="edgeForm.delay_minutes" type="number" min="0" :placeholder="t('delayMinutes')" />
        <input v-model="edgeForm.occurred_at" type="datetime-local" />
        <input v-model.number="edgeForm.weight" type="number" min="1" />
        <button>{{ t('addEdge') }}</button>
      </form>
    </div>

    <div class="panel metrics-panel">
      <h2>{{ t('snaMetrics') }}</h2>
      <p class="muted">{{ t('computedByFastApi') }}</p>
      <div class="metric-row">
        <span>{{ t('nodes') }}</span>
        <strong>{{ metrics?.node_count ?? 0 }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('edges') }}</span>
        <strong>{{ metrics?.edge_count ?? 0 }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('density') }}</span>
        <strong>{{ metrics?.density ?? 0 }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('averagePathLength') }}</span>
        <strong>{{ metrics?.average_path_length ?? 'n/a' }}</strong>
      </div>
      <div class="metric-row">
        <span>{{ t('communities') }}</span>
        <strong>{{ metrics?.communities?.length ?? 0 }}</strong>
      </div>
      <div v-for="(entry, id) in metrics?.degree" :key="id" class="list-item">
        <strong>{{ entry.label }}</strong>
        <span>In {{ entry.in_degree }} · Out {{ entry.out_degree }} · {{ t('weightedHandovers') }} {{ entry.weighted_handover_count }}</span>
      </div>
      <h3>{{ t('bottleneckCandidates') }}</h3>
      <div v-for="candidate in metrics?.bottleneck_candidates || []" :key="candidate.node_id" class="list-item">
        <strong>{{ candidate.label }}</strong>
        <span>{{ t('betweenness') }} {{ candidate.betweenness }} · {{ t('delay') }} {{ candidate.weighted_delay_minutes }} {{ t('min') }}</span>
      </div>
    </div>
  </section>
</template>
