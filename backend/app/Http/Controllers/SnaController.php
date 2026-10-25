<?php

namespace App\Http\Controllers;

use App\Models\SnaEdge;
use App\Models\SnaNode;
use App\Services\AiServiceClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class SnaController extends Controller
{
    public function nodes(): JsonResponse
    {
        return response()->json(SnaNode::orderBy('label')->get());
    }

    public function storeNode(Request $request): JsonResponse
    {
        $node = SnaNode::create($request->validate([
            'label' => ['required', 'string', 'max:120'],
            'role' => ['required', 'string', 'max:120'],
            'department' => ['nullable', 'string', 'max:120'],
        ]));

        return response()->json($node, 201);
    }

    public function edges(): JsonResponse
    {
        return response()->json(SnaEdge::with(['source', 'target'])->latest()->get());
    }

    public function storeEdge(Request $request): JsonResponse
    {
        $edge = SnaEdge::create($request->validate([
            'source_node_id' => ['required', 'exists:sna_nodes,id'],
            'target_node_id' => ['required', 'exists:sna_nodes,id'],
            'interaction_type' => ['required', 'string', 'max:80'],
            'report_reference' => ['nullable', 'string', 'max:80'],
            'channel' => ['nullable', 'string', 'max:80'],
            'occurred_at' => ['nullable', 'date'],
            'delay_minutes' => ['nullable', 'integer', 'min:0'],
            'weight' => ['nullable', 'integer', 'min:1'],
        ]));

        return response()->json($edge->load(['source', 'target']), 201);
    }

    public function metrics(AiServiceClient $ai): JsonResponse
    {
        $nodes = SnaNode::all();
        $edges = SnaEdge::all();

        return response()->json($ai->snaMetrics($nodes, $edges));
    }
}
