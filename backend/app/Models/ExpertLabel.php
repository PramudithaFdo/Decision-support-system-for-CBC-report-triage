<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ExpertLabel extends Model
{
    protected $fillable = [
        'fbc_report_id',
        'label',
        'expert_role',
        'label_source',
        'confidence',
        'rationale',
    ];

    protected $casts = [
        'confidence' => 'float',
    ];

    public function fbcReport(): BelongsTo
    {
        return $this->belongsTo(FbcReport::class);
    }
}
