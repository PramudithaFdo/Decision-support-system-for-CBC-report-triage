<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class UsabilityFeedback extends Model
{
    protected $table = 'usability_feedback';

    protected $fillable = [
        'participant_code',
        'role',
        'task_time_seconds',
        'sus_score',
        'trust_score',
        'usefulness_score',
        'comments',
    ];
}
