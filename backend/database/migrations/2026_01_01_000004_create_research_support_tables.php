<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('dataset_imports', function (Blueprint $table) {
            $table->id();
            $table->string('filename');
            $table->string('source_type')->default('clinical_deidentified');
            $table->unsignedInteger('row_count')->default(0);
            $table->unsignedInteger('imported_count')->default(0);
            $table->unsignedInteger('skipped_count')->default(0);
            $table->json('missing_value_summary')->nullable();
            $table->json('errors')->nullable();
            $table->text('notes')->nullable();
            $table->timestamps();
        });

        Schema::create('expert_labels', function (Blueprint $table) {
            $table->id();
            $table->foreignId('fbc_report_id')->constrained()->cascadeOnDelete();
            $table->string('label');
            $table->string('expert_role')->nullable();
            $table->string('label_source')->default('expert_review');
            $table->decimal('confidence', 4, 2)->nullable();
            $table->text('rationale')->nullable();
            $table->timestamps();
        });

        Schema::create('usability_feedback', function (Blueprint $table) {
            $table->id();
            $table->string('participant_code');
            $table->string('role')->nullable();
            $table->unsignedInteger('task_time_seconds')->nullable();
            $table->unsignedTinyInteger('sus_score')->nullable();
            $table->unsignedTinyInteger('trust_score')->nullable();
            $table->unsignedTinyInteger('usefulness_score')->nullable();
            $table->text('comments')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('usability_feedback');
        Schema::dropIfExists('expert_labels');
        Schema::dropIfExists('dataset_imports');
    }
};
