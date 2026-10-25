<?php

namespace App\Services;

use App\Models\DatasetImport;
use App\Models\ExpertLabel;
use App\Models\FbcReport;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Arr;
use ZipArchive;

class DatasetImportService
{
    private const FIELDS = [
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

    public function __construct(
        private readonly TriageService $triage,
        private readonly AiServiceClient $ai,
    ) {}

    public function import(UploadedFile $file, array $meta = []): DatasetImport
    {
        $rows = $this->readRows($file);
        $missing = [];
        $errors = [];
        $imported = 0;
        $skipped = 0;

        foreach ($rows as $index => $row) {
            $payload = $this->normaliseRow($row);
            $pCode = $payload['patient_code'] ?? null;
            if (empty($pCode) || empty($payload['sample_code'])) {
                $skipped++;
                $errors[] = "Row ".($index + 2)." skipped: patient_code and sample_code are required.";
                continue;
            }

            $sourceType = $payload['data_source'] ?: ($meta['source_type'] ?? 'research_deidentified');
            $payload['data_source'] = $sourceType;
            $payload['data_source_label'] = $payload['data_source_label'] ?: $this->sourceLabel($sourceType);

            foreach (self::FIELDS as $field) {
                if (!array_key_exists($field, $payload) || $payload[$field] === null || $payload[$field] === '') {
                    $missing[$field] = ($missing[$field] ?? 0) + 1;
                }
            }

            $report = FbcReport::updateOrCreate(
                ['sample_code' => $payload['sample_code']],
                Arr::only($payload, self::FIELDS)
            );

            if (! empty($payload['expert_label'])) {
                ExpertLabel::updateOrCreate(
                    [
                        'fbc_report_id' => $report->id,
                        'label_source' => $payload['label_source'] ?? 'imported_dataset',
                    ],
                    [
                        'label' => $payload['expert_label'],
                        'expert_role' => $payload['expert_role'] ?? 'Imported dataset label',
                        'confidence' => $payload['label_confidence'] ?? null,
                        'rationale' => 'Imported dataset label; verify before research analysis.',
                    ]
                );
            }

            $ruleResult = $this->triage->evaluate($report);
            $ruleResult['ml_placeholder'] = $this->ai->predict($report);
            $report->triageResult()->updateOrCreate(['fbc_report_id' => $report->id], $ruleResult);
            $imported++;
        }

        return DatasetImport::create([
            'filename' => $file->getClientOriginalName(),
            'source_type' => $meta['source_type'] ?? 'research_deidentified',
            'row_count' => count($rows),
            'imported_count' => $imported,
            'skipped_count' => $skipped,
            'missing_value_summary' => $missing,
            'errors' => $errors,
            'notes' => $meta['notes'] ?? null,
        ]);
    }

    private function readRows(UploadedFile $file): array
    {
        $extension = strtolower($file->getClientOriginalExtension());

        return $extension === 'xlsx'
            ? $this->readXlsx($file->getRealPath())
            : $this->readCsv($file->getRealPath());
    }

    private function readCsv(string $path): array
    {
        $handle = fopen($path, 'r');
        $headers = array_map([$this, 'normaliseHeader'], fgetcsv($handle) ?: []);
        $rows = [];

        while (($line = fgetcsv($handle)) !== false) {
            $rows[] = array_combine($headers, array_pad($line, count($headers), null));
        }
        fclose($handle);

        return $rows;
    }

    private function readXlsx(string $path): array
    {
        $zip = new ZipArchive();
        $zip->open($path);
        $shared = $this->readSharedStrings($zip);
        $sheet = simplexml_load_string($zip->getFromName('xl/worksheets/sheet1.xml'));
        $sheet->registerXPathNamespace('x', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main');
        $rows = [];

        foreach ($sheet->xpath('//x:sheetData/x:row') as $row) {
            $cells = [];
            foreach ($row->xpath('x:c') as $cell) {
                $type = (string) $cell['t'];
                $value = (string) ($cell->v ?? '');
                $cells[] = $type === 's' ? ($shared[(int) $value] ?? '') : $value;
            }
            $rows[] = $cells;
        }
        $zip->close();

        $headers = array_map([$this, 'normaliseHeader'], array_shift($rows) ?: []);

        return array_map(fn ($row) => array_combine($headers, array_pad($row, count($headers), null)), $rows);
    }

    private function readSharedStrings(ZipArchive $zip): array
    {
        $xml = $zip->getFromName('xl/sharedStrings.xml');
        if ($xml === false) {
            return [];
        }

        $strings = simplexml_load_string($xml);
        $strings->registerXPathNamespace('x', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main');

        return array_map(fn ($node) => (string) $node->t, $strings->xpath('//x:si'));
    }

    private function normaliseRow(array $row): array
    {
        $payload = [];
        foreach ($row as $key => $value) {
            $key = $this->normaliseHeader((string) $key);
            $payload[$key] = $value === '' ? null : $value;
        }

        $pCode = $payload['patient_code'] ?? null;
        if ($pCode) {
            $payload['patient_code'] = $pCode;
        }

        foreach (['wbc', 'rbc', 'hgb', 'hct', 'plt', 'mcv', 'mch', 'mchc', 'rdw', 'mpv', 'neutrophils', 'lymphocytes', 'monocytes', 'eosinophils', 'basophils'] as $field) {
            $payload[$field] = isset($payload[$field]) ? (float) $payload[$field] : null;
        }

        $payload['analyzer_flags'] = isset($payload['analyzer_flags'])
            ? array_values(array_filter(array_map('trim', explode('|', str_replace(',', '|', $payload['analyzer_flags'])))))
            : [];

        foreach (['expert_label', 'label_source', 'expert_role', 'label_confidence', 'data_source', 'data_source_label'] as $field) {
            if (array_key_exists($field, $row)) {
                $payload[$field] = $row[$field] === '' ? null : $row[$field];
            }
        }

        $payload['data_source'] = $payload['data_source'] ?? null;
        $payload['data_source_label'] = $payload['data_source_label'] ?? null;

        return $payload;
    }

    private function sourceLabel(string $source): string
    {
        return match ($source) {
            'neerogya_healthcare_polonnaruwa' => 'Neerogya Health Care (PVT) Ltd Clinical Dataset',
            'real_deidentified' => 'De-identified real FBC dataset',
            'pending_ethics_review' => 'Pending ethics approval dataset',
            default => 'Clinical research dataset',
        };
    }

    private function normaliseHeader(string $header): string
    {
        return strtolower(trim(str_replace([' ', '-'], '_', $header)));
    }
}
