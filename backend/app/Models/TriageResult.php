<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TriageResult extends Model
{
    protected $fillable = [
        'fbc_report_id',
        'category',
        'confidence',
        'rule_summary',
        'uncertainty_reasons',
        'ml_placeholder',
    ];

    protected $casts = [
        'confidence' => 'float',
        'uncertainty_reasons' => 'array',
        'ml_placeholder' => 'array',
    ];

    public function fbcReport(): BelongsTo
    {
        return $this->belongsTo(FbcReport::class);
    }
}
