<?php

namespace App\Http\Controllers;

use App\Models\ExpertLabel;
use App\Models\FbcReport;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class LabelController extends Controller
{
    public function store(Request $request, FbcReport $fbcReport): JsonResponse
    {
        $label = ExpertLabel::create($request->validate([
            'label' => ['required', 'in:Routine,Abnormal non-critical,Critical / urgent,Uncertain / manual review'],
            'expert_role' => ['nullable', 'string', 'max:120'],
            'label_source' => ['nullable', 'string', 'max:120'],
            'confidence' => ['nullable', 'numeric', 'min:0', 'max:1'],
            'rationale' => ['nullable', 'string', 'max:1000'],
        ]) + ['fbc_report_id' => $fbcReport->id]);

        return response()->json($label, 201);
    }

    public function summary(): JsonResponse
    {
        return response()->json([
            'total_labels' => ExpertLabel::count(),
            'labeled_reports' => ExpertLabel::distinct('fbc_report_id')->count('fbc_report_id'),
            'by_category' => ExpertLabel::select('label', DB::raw('count(*) as count'))->groupBy('label')->get(),
        ]);
    }
}
