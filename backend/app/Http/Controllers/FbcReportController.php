<?php

namespace App\Http\Controllers;

use App\Models\FbcReport;
use App\Models\TriageResult;
use App\Services\AiServiceClient;
use App\Services\TriageService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class FbcReportController extends Controller
{
    public function index(): JsonResponse
    {
        return response()->json(FbcReport::with('triageResult')->latest()->get());
    }

    public function store(Request $request, TriageService $triageService, AiServiceClient $ai): JsonResponse
    {
        $data = $this->validated($request);
        $report = FbcReport::create($data);
        $this->saveTriage($report, $triageService, $ai);

        return response()->json($report->load('triageResult'), 201);
    }

    public function show(FbcReport $fbcReport): JsonResponse
    {
        return response()->json($fbcReport->load('triageResult'));
    }

    public function triage(FbcReport $fbcReport, TriageService $triageService, AiServiceClient $ai): JsonResponse
    {
        $this->saveTriage($fbcReport, $triageService, $ai);

        return response()->json($fbcReport->load('triageResult'));
    }

    private function validated(Request $request): array
    {
        $payload = $request->validate([
            'patient_code' => ['nullable', 'string', 'max:80'],
            'sample_code' => ['required', 'string', 'max:80'],
            'collected_at' => ['nullable', 'date'],
            'wbc' => ['nullable', 'numeric'],
            'rbc' => ['nullable', 'numeric'],
            'hgb' => ['nullable', 'numeric'],
            'hct' => ['nullable', 'numeric'],
            'plt' => ['nullable', 'numeric'],
            'mcv' => ['nullable', 'numeric'],
            'mch' => ['nullable', 'numeric'],
            'mchc' => ['nullable', 'numeric'],
            'rdw' => ['nullable', 'numeric'],
            'mpv' => ['nullable', 'numeric'],
            'neutrophils' => ['nullable', 'numeric'],
            'lymphocytes' => ['nullable', 'numeric'],
            'monocytes' => ['nullable', 'numeric'],
            'eosinophils' => ['nullable', 'numeric'],
            'basophils' => ['nullable', 'numeric'],
            'analyzer_flags' => ['nullable', 'array'],
            'analyzer_flags.*' => ['string', 'max:80'],
            'data_source' => ['nullable', 'string', 'max:80'],
            'data_source_label' => ['nullable', 'string', 'max:120'],
            'notes' => ['nullable', 'string', 'max:1000'],
        ]);

        $payload['patient_code'] = $payload['patient_code'] ?? 'PAT-001';

        return $payload;
    }

    private function saveTriage(FbcReport $report, TriageService $triageService, AiServiceClient $ai): TriageResult
    {
        $ruleResult = $triageService->evaluate($report);
        $ruleResult['ml_placeholder'] = $ai->predict($report);

        return $report->triageResult()->updateOrCreate(
            ['fbc_report_id' => $report->id],
            $ruleResult
        );
    }
}
