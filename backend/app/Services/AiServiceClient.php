<?php

namespace App\Services;

use App\Models\FbcReport;
use App\Models\SnaEdge;
use App\Models\SnaNode;
use Illuminate\Support\Facades\Http;
use Throwable;

class AiServiceClient
{
    public function predict(FbcReport $report): array
    {
        try {
            $response = Http::timeout(2)->post(config('services.ai.url').'/predict-triage', [
                'values' => [
                    'wbc' => $report->wbc,
                    'rbc' => $report->rbc,
                    'hgb' => $report->hgb,
                    'hct' => $report->hct,
                    'plt' => $report->plt,
                    'mcv' => $report->mcv,
                    'mch' => $report->mch,
                    'mchc' => $report->mchc,
                    'rdw' => $report->rdw,
                    'mpv' => $report->mpv,
                    'neutrophils' => $report->neutrophils,
                    'lymphocytes' => $report->lymphocytes,
                    'monocytes' => $report->monocytes,
                    'eosinophils' => $report->eosinophils,
                    'basophils' => $report->basophils,
                ],
                'analyzer_flags' => $report->analyzer_flags ?? [],
            ]);

            return $response->successful() ? $response->json() : $this->fallbackPrediction();
        } catch (Throwable) {
            return $this->fallbackPrediction();
        }
    }

    public function snaMetrics($nodes, $edges): array
    {
        try {
            $response = Http::timeout(2)->post(config('services.ai.url').'/sna/metrics', [
                'nodes' => $nodes->map(fn (SnaNode $node) => [
                    'id' => $node->id,
                    'label' => $node->label,
                    'role' => $node->role,
                ])->values(),
                'edges' => $edges->map(fn (SnaEdge $edge) => [
                    'source' => $edge->source_node_id,
                    'target' => $edge->target_node_id,
                    'interaction_type' => $edge->interaction_type,
                    'channel' => $edge->channel,
                    'delay_minutes' => $edge->delay_minutes,
                    'weight' => $edge->weight,
                ])->values(),
            ]);

            return $response->successful() ? $response->json() : $this->localMetrics($nodes, $edges);
        } catch (Throwable) {
            return $this->localMetrics($nodes, $edges);
        }
    }

    private function fallbackPrediction(): array
    {
        return [
            'category' => 'Uncertain / manual review',
            'confidence' => 0.35,
            'explanation' => 'ML placeholder unavailable; rule-based Laravel triage remains authoritative.',
        ];
    }

    private function localMetrics($nodes, $edges): array
    {
        $degree = [];
        foreach ($nodes as $node) {
            $degree[(string) $node->id] = ['label' => $node->label, 'in_degree' => 0, 'out_degree' => 0, 'weighted_handover_count' => 0];
        }

        foreach ($edges as $edge) {
            $degree[(string) $edge->source_node_id]['out_degree']++;
            $degree[(string) $edge->source_node_id]['weighted_handover_count'] += $edge->weight;
            $degree[(string) $edge->target_node_id]['in_degree']++;
        }

        return [
            'node_count' => $nodes->count(),
            'edge_count' => $edges->count(),
            'degree' => $degree,
            'source' => 'laravel-fallback',
        ];
    }
}
