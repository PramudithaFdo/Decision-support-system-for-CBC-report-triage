<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class SnaEdge extends Model
{
    protected $fillable = [
        'source_node_id',
        'target_node_id',
        'interaction_type',
        'report_reference',
        'channel',
        'occurred_at',
        'delay_minutes',
        'weight',
    ];

    protected $casts = [
        'occurred_at' => 'datetime',
        'delay_minutes' => 'integer',
        'weight' => 'integer',
    ];

    public function source(): BelongsTo
    {
        return $this->belongsTo(SnaNode::class, 'source_node_id');
    }

    public function target(): BelongsTo
    {
        return $this->belongsTo(SnaNode::class, 'target_node_id');
    }
}
