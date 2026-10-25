<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasOne;

class FbcReport extends Model
{
    protected $fillable = [
        'patient_code',
        'sample_code',
        'collected_at',
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

    protected $casts = [
        'collected_at' => 'datetime',
        'wbc' => 'float',
        'rbc' => 'float',
        'hgb' => 'float',
        'hct' => 'float',
        'plt' => 'float',
        'mcv' => 'float',
        'mch' => 'float',
        'mchc' => 'float',
        'rdw' => 'float',
        'mpv' => 'float',
        'neutrophils' => 'float',
        'lymphocytes' => 'float',
        'monocytes' => 'float',
        'eosinophils' => 'float',
        'basophils' => 'float',
        'analyzer_flags' => 'array',
    ];

    public function triageResult(): HasOne
    {
        return $this->hasOne(TriageResult::class);
    }
}
