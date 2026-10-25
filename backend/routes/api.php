<?php

use App\Http\Controllers\FbcReportController;
use App\Http\Controllers\DatasetController;
use App\Http\Controllers\EvaluationController;
use App\Http\Controllers\LabelController;
use App\Http\Controllers\ResearchDashboardController;
use App\Http\Controllers\SnaController;
use Illuminate\Support\Facades\Route;

Route::get('/health', fn () => ['status' => 'ok', 'service' => 'fbc-triage-api']);

Route::get('/fbc-reports', [FbcReportController::class, 'index']);
Route::post('/fbc-reports', [FbcReportController::class, 'store']);
Route::get('/fbc-reports/{fbcReport}', [FbcReportController::class, 'show']);
Route::post('/fbc-reports/{fbcReport}/triage', [FbcReportController::class, 'triage']);
Route::post('/fbc-reports/{fbcReport}/expert-label', [LabelController::class, 'store']);

Route::get('/datasets', [DatasetController::class, 'index']);
Route::post('/datasets/import', [DatasetController::class, 'import']);
Route::get('/datasets/{dataset}', [DatasetController::class, 'summary']);
Route::get('/datasets/{dataset}/summary', [DatasetController::class, 'summary']);
Route::get('/labels/summary', [LabelController::class, 'summary']);
Route::post('/evaluation/feedback', [EvaluationController::class, 'store']);
Route::get('/evaluation/summary', [EvaluationController::class, 'summary']);
Route::get('/research-dashboard', ResearchDashboardController::class);

Route::get('/sna/nodes', [SnaController::class, 'nodes']);
Route::post('/sna/nodes', [SnaController::class, 'storeNode']);
Route::get('/sna/edges', [SnaController::class, 'edges']);
Route::post('/sna/edges', [SnaController::class, 'storeEdge']);
Route::get('/sna/metrics', [SnaController::class, 'metrics']);
