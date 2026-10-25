<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class DatasetImport extends Model
{
    protected $fillable = [
        'filename',
        'source_type',
        'row_count',
        'imported_count',
        'skipped_count',
        'missing_value_summary',
        'errors',
        'notes',
    ];

    protected $casts = [
        'missing_value_summary' => 'array',
        'errors' => 'array',
    ];
}
