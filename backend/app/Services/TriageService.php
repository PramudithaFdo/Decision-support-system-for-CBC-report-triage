<?php

namespace App\Services;

use App\Models\FbcReport;

class TriageService
{
    private const UNCERTAIN = 'Uncertain / manual review';
    private const CRITICAL = 'Critical / urgent';
    private const ABNORMAL = 'Abnormal non-critical';
    private const ROUTINE = 'Routine';

    public function evaluate(FbcReport $report): array
    {
        $missing = $this->missingValues($report);
        $flags = array_map('strtolower', $report->analyzer_flags ?? []);
        $uncertaintyReasons = [];

        if ($missing !== []) {
            $uncertaintyReasons[] = 'Missing FBC values: '.implode(', ', $missing);
        }

        if ($this->hasConflictingFlags($flags)) {
            $uncertaintyReasons[] = 'Analyzer flags conflict and require manual review';
        }

        if (in_array('review', $flags, true) || in_array('manual_review', $flags, true)) {
            $uncertaintyReasons[] = 'Analyzer requested manual review';
        }

        if ($uncertaintyReasons !== []) {
            return [
                'category' => self::UNCERTAIN,
                'confidence' => 0.42,
                'rule_summary' => 'Uncertainty rule override applied before clinical severity rules.',
                'uncertainty_reasons' => $uncertaintyReasons,
            ];
        }

        $criticalReasons = $this->criticalReasons($report, $flags);
        if ($criticalReasons !== []) {
            return [
                'category' => self::CRITICAL,
                'confidence' => 0.94,
                'rule_summary' => 'Critical threshold met: '.implode('; ', $criticalReasons),
                'uncertainty_reasons' => [],
            ];
        }

        $abnormalReasons = $this->abnormalReasons($report, $flags);
        if ($abnormalReasons !== []) {
            return [
                'category' => self::ABNORMAL,
                'confidence' => 0.82,
                'rule_summary' => 'Abnormal non-critical pattern: '.implode('; ', $abnormalReasons),
                'uncertainty_reasons' => [],
            ];
        }

        return [
            'category' => self::ROUTINE,
            'confidence' => 0.9,
            'rule_summary' => 'FBC values are inside MVP reference ranges and no conflicting analyzer flags were supplied.',
            'uncertainty_reasons' => [],
        ];
    }

    private function missingValues(FbcReport $report): array
    {
        $fields = [
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
        ];

        return array_values(array_filter($fields, fn (string $field) => $report->{$field} === null));
    }

    private function hasConflictingFlags(array $flags): bool
    {
        return in_array('normal', $flags, true) && (
            in_array('critical', $flags, true)
            || in_array('panic', $flags, true)
            || in_array('blast_flag', $flags, true)
        );
    }

    private function criticalReasons(FbcReport $report, array $flags): array
    {
        $reasons = [];

        if ($report->wbc < 2.0 || $report->wbc > 30.0) {
            $reasons[] = 'WBC outside critical range';
        }
        if ($report->hgb < 7.0) {
            $reasons[] = 'HGB below critical threshold';
        }
        if ($report->plt < 50.0) {
            $reasons[] = 'PLT below critical threshold';
        }
        if ($report->neutrophils < 1.0) {
            $reasons[] = 'Neutrophils below critical threshold';
        }
        if (in_array('critical', $flags, true) || in_array('panic', $flags, true)) {
            $reasons[] = 'Analyzer critical flag present';
        }

        return $reasons;
    }

    private function abnormalReasons(FbcReport $report, array $flags): array
    {
        $ranges = [
            'wbc' => [4.0, 11.0, 'WBC'],
            'rbc' => [4.0, 5.9, 'RBC'],
            'hgb' => [12.0, 17.5, 'HGB'],
            'hct' => [36.0, 52.0, 'HCT'],
            'plt' => [150.0, 450.0, 'PLT'],
            'mcv' => [80.0, 100.0, 'MCV'],
            'mch' => [27.0, 33.0, 'MCH'],
            'mchc' => [32.0, 36.0, 'MCHC'],
            'rdw' => [11.5, 14.5, 'RDW'],
            'mpv' => [7.5, 12.0, 'MPV'],
            'neutrophils' => [2.0, 7.5, 'Neutrophils'],
            'lymphocytes' => [1.0, 4.0, 'Lymphocytes'],
            'monocytes' => [0.2, 1.0, 'Monocytes'],
            'eosinophils' => [0.0, 0.5, 'Eosinophils'],
            'basophils' => [0.0, 0.2, 'Basophils'],
        ];

        $reasons = [];
        foreach ($ranges as $field => [$low, $high, $label]) {
            if ($report->{$field} < $low || $report->{$field} > $high) {
                $reasons[] = "{$label} outside routine range";
            }
        }

        if (in_array('abnormal', $flags, true)) {
            $reasons[] = 'Analyzer abnormal flag present';
        }

        return $reasons;
    }
}
