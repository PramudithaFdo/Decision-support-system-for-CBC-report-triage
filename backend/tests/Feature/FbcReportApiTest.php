<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class FbcReportApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_creates_report_and_triage(): void
    {
        $response = $this->postJson('/api/fbc-reports', $this->payload());

        $response->assertCreated()
            ->assertJsonPath('triage_result.category', 'Routine');
    }

    public function test_routine_triage(): void
    {
        $this->postJson('/api/fbc-reports', $this->payload(['sample_code' => 'T-ROUTINE']))
            ->assertJsonPath('triage_result.category', 'Routine');
    }

    public function test_abnormal_non_critical_triage(): void
    {
        $this->postJson('/api/fbc-reports', $this->payload(['sample_code' => 'T-ABN', 'wbc' => 12.4]))
            ->assertJsonPath('triage_result.category', 'Abnormal non-critical');
    }

    public function test_critical_triage(): void
    {
        $this->postJson('/api/fbc-reports', $this->payload(['sample_code' => 'T-CRIT', 'hgb' => 6.5]))
            ->assertJsonPath('triage_result.category', 'Critical / urgent');
    }

    public function test_missing_values_are_uncertain(): void
    {
        $this->postJson('/api/fbc-reports', $this->payload(['sample_code' => 'T-MISSING', 'rbc' => null]))
            ->assertJsonPath('triage_result.category', 'Uncertain / manual review');
    }

    public function test_conflicting_flags_are_uncertain(): void
    {
        $this->postJson('/api/fbc-reports', $this->payload(['sample_code' => 'T-FLAGS', 'analyzer_flags' => ['normal', 'critical']]))
            ->assertJsonPath('triage_result.category', 'Uncertain / manual review');
    }

    public function test_imports_deidentified_csv_dataset(): void
    {
        $csv = "patient_code,sample_code,wbc,rbc,hgb,hct,plt,mcv,mch,mchc,rdw,mpv,neutrophils,lymphocytes,monocytes,eosinophils,basophils,analyzer_flags\n".
            "NHC-P-X,FBC-IMPORT-001,6.2,4.7,14,42,250,88,30,34,13,9.5,3.5,2,0.5,0.2,0.1,normal\n";

        $file = UploadedFile::fake()->createWithContent('clinical_fbc.csv', $csv);

        $this->post('/api/datasets/import', ['file' => $file, 'source_type' => 'real_deidentified'], ['Accept' => 'application/json'])
            ->assertCreated()
            ->assertJsonPath('imported_count', 1)
            ->assertJsonPath('source_type', 'real_deidentified');

        $this->assertDatabaseHas('fbc_reports', [
            'sample_code' => 'FBC-IMPORT-001',
            'data_source' => 'real_deidentified',
            'data_source_label' => 'De-identified real FBC dataset',
        ]);
    }

    public function test_stores_expert_label_and_summary(): void
    {
        $report = $this->postJson('/api/fbc-reports', $this->payload(['sample_code' => 'T-LABEL']))->json();

        $this->postJson('/api/fbc-reports/'.$report['id'].'/expert-label', [
            'label' => 'Routine',
            'expert_role' => 'Medical laboratory technologist',
            'confidence' => 0.95,
            'rationale' => 'Expert validated clinical report.',
        ])->assertCreated();

        $this->getJson('/api/labels/summary')
            ->assertOk()
            ->assertJsonPath('total_labels', 1);
    }

    public function test_records_evaluation_feedback_and_dashboard_alignment(): void
    {
        $this->postJson('/api/evaluation/feedback', [
            'participant_code' => 'STAFF-001',
            'role' => 'Medical laboratory technologist',
            'task_time_seconds' => 140,
            'sus_score' => 82,
            'trust_score' => 4,
            'usefulness_score' => 5,
            'comments' => 'Clinical usability feedback.',
        ])->assertCreated();

        $this->getJson('/api/evaluation/summary')
            ->assertOk()
            ->assertJsonPath('responses', 1)
            ->assertJsonPath('average_sus', 82);

        $this->getJson('/api/research-dashboard')
            ->assertOk()
            ->assertJsonPath('hypotheses.4.key', 'H5');
    }

    public function test_seeds_neerogya_healthcare_clinical_dataset(): void
    {
        Http::fake([
            '*' => Http::response([
                'category' => 'Uncertain / manual review',
                'confidence' => 0.35,
                'explanation' => 'Fake ML response for tests.',
            ]),
        ]);

        $this->seed();

        $this->assertSame(1000, DB::table('fbc_reports')->where('sample_code', 'like', 'NHC-CBC-2025-%')->count());
        $this->assertSame(1000, DB::table('fbc_reports')->where('data_source', 'neerogya_healthcare_polonnaruwa')->count());
        $this->assertSame(1000, DB::table('expert_labels')->where('label_source', 'neerogya_laboratory_hematologist')->count());
        $this->assertSame(1004, DB::table('triage_results')->count());
        $this->assertDatabaseHas('dataset_imports', [
            'filename' => 'Neerogya Health Care (PVT) Ltd CBC Dataset (1000 records)',
            'source_type' => 'clinical_lab_neerogya',
            'row_count' => 1000,
            'imported_count' => 1000,
        ]);
    }

    private function payload(array $overrides = []): array
    {
        return array_merge([
            'patient_code' => 'TEST-PAT-001',
            'sample_code' => 'T-001',
            'wbc' => 6.2,
            'rbc' => 4.7,
            'hgb' => 14.0,
            'hct' => 42.0,
            'plt' => 250,
            'mcv' => 88.0,
            'mch' => 30.0,
            'mchc' => 34.0,
            'rdw' => 13.0,
            'mpv' => 9.5,
            'neutrophils' => 3.5,
            'lymphocytes' => 2.0,
            'monocytes' => 0.5,
            'eosinophils' => 0.2,
            'basophils' => 0.1,
            'analyzer_flags' => ['normal'],
        ], $overrides);
    }
}
