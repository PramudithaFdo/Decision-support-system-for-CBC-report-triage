<?php

namespace App\Http\Controllers;

use App\Models\DatasetImport;
use App\Models\ExpertLabel;
use App\Models\FbcReport;
use App\Models\SnaEdge;
use App\Models\SnaNode;
use App\Models\TriageResult;
use App\Models\UsabilityFeedback;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

class ResearchDashboardController extends Controller
{
    public function __invoke(): JsonResponse
    {
        $reportCount = FbcReport::count();
        $importCount = DatasetImport::count();
        $labelCount = ExpertLabel::count();
        $triageCount = TriageResult::count();
        $nodeCount = SnaNode::count();
        $edgeCount = SnaEdge::count();
        $feedbackCount = UsabilityFeedback::count();

        return response()->json([
            'objectives' => [
                [
                    'key' => 'O1',
                    'title' => 'FBC triage decision-support baseline',
                    'status' => $triageCount > 0 ? 'Evidence available' : 'Needs triage runs',
                    'evidence' => "{$triageCount} triage results across {$reportCount} clinical/de-identified reports.",
                ],
                [
                    'key' => 'O2',
                    'title' => 'Dataset import and expert-label provenance',
                    'status' => $importCount > 0 || $labelCount > 0 ? 'Evidence available' : 'Ready for data collection',
                    'evidence' => "{$importCount} dataset imports and {$labelCount} expert labels recorded.",
                ],
                [
                    'key' => 'O3',
                    'title' => 'Workflow and SNA bottleneck analysis',
                    'status' => $edgeCount > 0 ? 'Evidence available' : 'Needs workflow edges',
                    'evidence' => "{$nodeCount} actors/departments and {$edgeCount} handover or communication edges.",
                ],
                [
                    'key' => 'O4',
                    'title' => 'Prototype usability and feasibility evaluation',
                    'status' => $feedbackCount > 0 ? 'Evidence available' : 'Ready for evaluation sessions',
                    'evidence' => "{$feedbackCount} feedback responses; average SUS ".round((float) UsabilityFeedback::avg('sus_score'), 2).'.',
                ],
            ],
            'category_counts' => TriageResult::select('category', DB::raw('count(*) as count'))->groupBy('category')->get(),
            'hypotheses' => [
                ['key' => 'H1', 'measure' => 'Classification performance', 'current_output' => 'FastAPI model metrics include confusion matrix, precision, recall, specificity, sensitivity, and macro F1.'],
                ['key' => 'H2', 'measure' => 'Uncertainty-aware deferral', 'current_output' => 'Model metrics and triage rules expose calibration error, coverage, deferral rate, low confidence, missing values, and flag conflicts.'],
                ['key' => 'H3', 'measure' => 'SNA bottleneck detection', 'current_output' => 'SNA metrics include degree, betweenness, closeness, density, average path length, modularity, and bottleneck candidates.'],
                ['key' => 'H4', 'measure' => 'Workflow/time improvement evidence', 'current_output' => 'Workflow edges store timestamps, delays, channels, roles, departments, report references, and edge weights.'],
                ['key' => 'H5', 'measure' => 'Usability and feasibility', 'current_output' => 'Evaluation records capture SUS score, task timing, trust, usefulness, and staff comments.'],
            ],
        ]);
    }
}
