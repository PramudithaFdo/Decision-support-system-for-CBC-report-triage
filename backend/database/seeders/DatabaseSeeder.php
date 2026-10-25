<?php

namespace Database\Seeders;

use App\Models\DatasetImport;
use App\Models\ExpertLabel;
use App\Models\FbcReport;
use App\Models\SnaEdge;
use App\Models\SnaNode;
use App\Services\AiServiceClient;
use App\Services\TriageService;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        $triage = app(TriageService::class);
        $ai = app(AiServiceClient::class);

        $reports = [
            [
                'patient_code' => 'NHC-P-0001',
                'sample_code' => 'FBC-ROUTINE-001',
                'wbc' => 6.2,
                'rbc' => 4.7,
                'hgb' => 14.1,
                'hct' => 42.0,
                'plt' => 260,
                'mcv' => 88.0,
                'mch' => 30.0,
                'mchc' => 34.0,
                'rdw' => 13.0,
                'mpv' => 9.5,
                'neutrophils' => 3.4,
                'lymphocytes' => 2.1,
                'monocytes' => 0.5,
                'eosinophils' => 0.2,
                'basophils' => 0.1,
                'analyzer_flags' => ['normal'],
                'data_source' => 'manual_entry',
                'data_source_label' => 'Clinical laboratory entry',
                'notes' => 'Routine clinical screening profile.',
            ],
            [
                'patient_code' => 'NHC-P-0002',
                'sample_code' => 'FBC-ABNORMAL-001',
                'wbc' => 12.8,
                'rbc' => 4.4,
                'hgb' => 11.2,
                'hct' => 35.0,
                'plt' => 480,
                'mcv' => 76.0,
                'mch' => 25.0,
                'mchc' => 31.0,
                'rdw' => 16.0,
                'mpv' => 12.5,
                'neutrophils' => 8.0,
                'lymphocytes' => 1.4,
                'monocytes' => 1.2,
                'eosinophils' => 0.4,
                'basophils' => 0.1,
                'analyzer_flags' => ['abnormal'],
                'data_source' => 'manual_entry',
                'data_source_label' => 'Clinical laboratory entry',
                'notes' => 'Abnormal non-critical clinical profile.',
            ],
            [
                'patient_code' => 'NHC-P-0003',
                'sample_code' => 'FBC-CRITICAL-001',
                'wbc' => 36.5,
                'rbc' => 3.2,
                'hgb' => 6.4,
                'hct' => 22.0,
                'plt' => 42,
                'mcv' => 72.0,
                'mch' => 23.0,
                'mchc' => 30.0,
                'rdw' => 18.0,
                'mpv' => 13.0,
                'neutrophils' => 0.8,
                'lymphocytes' => 5.5,
                'monocytes' => 1.1,
                'eosinophils' => 0.1,
                'basophils' => 0.1,
                'analyzer_flags' => ['critical'],
                'data_source' => 'manual_entry',
                'data_source_label' => 'Clinical laboratory entry',
                'notes' => 'Urgent critical hematology alert.',
            ],
            [
                'patient_code' => 'NHC-P-0004',
                'sample_code' => 'FBC-UNCERTAIN-001',
                'wbc' => 5.5,
                'rbc' => null,
                'hgb' => 13.2,
                'hct' => 40.0,
                'plt' => 240,
                'mcv' => 90.0,
                'mch' => 30.0,
                'mchc' => 34.0,
                'rdw' => 13.0,
                'mpv' => 9.0,
                'neutrophils' => 3.1,
                'lymphocytes' => 2.0,
                'monocytes' => 0.5,
                'eosinophils' => 0.2,
                'basophils' => 0.1,
                'analyzer_flags' => ['normal', 'critical'],
                'data_source' => 'manual_entry',
                'data_source_label' => 'Clinical laboratory entry',
                'notes' => 'Diagnostic uncertainty review profile with missing value and conflicting flags.',
            ],
        ];

        foreach ($reports as $payload) {
            $report = FbcReport::updateOrCreate(['sample_code' => $payload['sample_code']], $payload);
            $this->triageReport($report, $triage, $ai);
        }

        $this->importNeerogyaDataset($triage, $ai);

        $lab = SnaNode::updateOrCreate(['label' => 'Lab Scientist A'], ['role' => 'Lab scientist', 'department' => 'Haematology']);
        $mlt = SnaNode::updateOrCreate(['label' => 'MLT Reviewer'], ['role' => 'Reviewer', 'department' => 'Laboratory']);
        $ward = SnaNode::updateOrCreate(['label' => 'Ward Clinician'], ['role' => 'Clinician', 'department' => 'Medical ward']);

        SnaEdge::updateOrCreate(
            ['source_node_id' => $lab->id, 'target_node_id' => $mlt->id, 'report_reference' => 'FBC-UNCERTAIN-001'],
            ['interaction_type' => 'manual_review_handover', 'channel' => 'bench_handover', 'delay_minutes' => 18, 'weight' => 2]
        );
        SnaEdge::updateOrCreate(
            ['source_node_id' => $mlt->id, 'target_node_id' => $ward->id, 'report_reference' => 'FBC-CRITICAL-001'],
            ['interaction_type' => 'urgent_notification', 'channel' => 'phone', 'delay_minutes' => 4, 'weight' => 1]
        );
    }

    private function importNeerogyaDataset(TriageService $triage, AiServiceClient $ai): void
    {
        $path = database_path('data/neerogya_fbc_1000.csv');
        if (! file_exists($path)) {
            return;
        }

        $handle = fopen($path, 'r');
        $headers = fgetcsv($handle) ?: [];
        $rows = [];
        while (($line = fgetcsv($handle)) !== false) {
            $rows[] = array_combine($headers, array_pad($line, count($headers), null));
        }
        fclose($handle);

        $missing = [];
        $errors = [];
        $imported = 0;
        $fields = [
            'patient_code',
            'sample_code',
            'wbc',
            'rbc',
            'hgb',
            'hct',
            'plt',
            'mcv',
            'mch',
            'mchc',
            'rdw',
            'mpv',
            'neutrophils',
            'lymphocytes',
            'monocytes',
            'eosinophils',
            'basophils',
            'analyzer_flags',
            'data_source',
            'data_source_label',
            'notes',
        ];

        foreach ($rows as $index => $row) {
            $pCode = $row['patient_code'] ?? null;
            if (empty($pCode) || empty($row['sample_code'])) {
                $errors[] = 'Row '.($index + 2).' skipped: missing patient_code or sample_code.';
                continue;
            }

            $payload = [];
            foreach ($fields as $field) {
                $payload[$field] = $row[$field] ?? null;
                if ($payload[$field] === '') {
                    $payload[$field] = null;
                }
            }
            $payload['patient_code'] = $pCode;

            foreach (['wbc', 'rbc', 'hgb', 'hct', 'plt', 'mcv', 'mch', 'mchc', 'rdw', 'mpv', 'neutrophils', 'lymphocytes', 'monocytes', 'eosinophils', 'basophils'] as $field) {
                if ($payload[$field] === null) {
                    $missing[$field] = ($missing[$field] ?? 0) + 1;
                } else {
                    $payload[$field] = (float) $payload[$field];
                }
            }

            $payload['analyzer_flags'] = array_values(array_filter(explode('|', (string) ($payload['analyzer_flags'] ?? ''))));
            $payload['data_source'] = $row['data_source'] ?? 'neerogya_healthcare_polonnaruwa';
            $payload['data_source_label'] = $row['data_source_label'] ?? 'Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka';
            $report = FbcReport::updateOrCreate(['sample_code' => $payload['sample_code']], $payload);

            ExpertLabel::updateOrCreate(
                ['fbc_report_id' => $report->id, 'label_source' => $row['label_source'] ?? 'neerogya_laboratory_hematologist'],
                [
                    'label' => $row['expert_label'] ?? 'Uncertain / manual review',
                    'expert_role' => 'Neerogya Laboratory Hematologist / MLT',
                    'confidence' => isset($row['label_confidence']) ? (float) $row['label_confidence'] : 0.85,
                    'rationale' => 'Validated clinical laboratory evaluation by Neerogya Health Care (PVT) Ltd.',
                ]
            );

            $this->triageReport($report, $triage, $ai);
            $imported++;
        }

        DatasetImport::updateOrCreate(
            ['filename' => 'Neerogya Health Care (PVT) Ltd CBC Dataset (1000 records)'],
            [
                'source_type' => 'clinical_lab_neerogya',
                'row_count' => count($rows),
                'imported_count' => $imported,
                'skipped_count' => count($errors),
                'missing_value_summary' => $missing,
                'errors' => $errors,
                'notes' => 'Clinical FBC/CBC laboratory records collected from Neerogya Health Care (PVT) Ltd, Polonnaruwa, Sri Lanka.',
            ]
        );
    }

    private function triageReport(FbcReport $report, TriageService $triage, AiServiceClient $ai): void
    {
        $ruleResult = $triage->evaluate($report);
        $ruleResult['ml_placeholder'] = $ai->predict($report);
        $report->triageResult()->updateOrCreate(['fbc_report_id' => $report->id], $ruleResult);
    }
}
