<?php

namespace App\Http\Controllers;

use App\Models\DatasetImport;
use App\Services\DatasetImportService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DatasetController extends Controller
{
    public function index(): JsonResponse
    {
        return response()->json(DatasetImport::latest()->get());
    }

    public function import(Request $request, DatasetImportService $service): JsonResponse
    {
        $data = $request->validate([
            'file' => ['required', 'file', 'mimes:csv,txt,xlsx'],
            'source_type' => ['nullable', 'string', 'max:120'],
            'notes' => ['nullable', 'string', 'max:1000'],
        ]);

        return response()->json($service->import($data['file'], $data), 201);
    }

    public function summary(DatasetImport $dataset): JsonResponse
    {
        return response()->json($dataset);
    }
}
