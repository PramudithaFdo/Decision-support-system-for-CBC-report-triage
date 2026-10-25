<?php

namespace App\Http\Controllers;

use App\Models\UsabilityFeedback;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class EvaluationController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        $feedback = UsabilityFeedback::create($request->validate([
            'participant_code' => ['required', 'string', 'max:80'],
            'role' => ['nullable', 'string', 'max:120'],
            'task_time_seconds' => ['nullable', 'integer', 'min:0'],
            'sus_score' => ['nullable', 'integer', 'min:0', 'max:100'],
            'trust_score' => ['nullable', 'integer', 'min:1', 'max:5'],
            'usefulness_score' => ['nullable', 'integer', 'min:1', 'max:5'],
            'comments' => ['nullable', 'string', 'max:2000'],
        ]));

        return response()->json($feedback, 201);
    }

    public function summary(): JsonResponse
    {
        return response()->json([
            'responses' => UsabilityFeedback::count(),
            'average_sus' => round((float) UsabilityFeedback::avg('sus_score'), 2),
            'average_task_time_seconds' => round((float) UsabilityFeedback::avg('task_time_seconds'), 2),
            'average_trust' => round((float) UsabilityFeedback::avg('trust_score'), 2),
            'average_usefulness' => round((float) UsabilityFeedback::avg('usefulness_score'), 2),
            'recent_feedback' => UsabilityFeedback::latest()->limit(5)->get(),
        ]);
    }
}
