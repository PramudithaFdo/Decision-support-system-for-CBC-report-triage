<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('fbc_reports', function (Blueprint $table) {
            $table->id();
            $table->string('patient_code')->nullable();
            $table->string('sample_code')->unique();
            $table->timestamp('collected_at')->nullable();
            $table->decimal('wbc', 6, 2)->nullable();
            $table->decimal('rbc', 6, 2)->nullable();
            $table->decimal('hgb', 6, 2)->nullable();
            $table->decimal('hct', 6, 2)->nullable();
            $table->decimal('plt', 8, 2)->nullable();
            $table->decimal('mcv', 6, 2)->nullable();
            $table->decimal('mch', 6, 2)->nullable();
            $table->decimal('mchc', 6, 2)->nullable();
            $table->decimal('rdw', 6, 2)->nullable();
            $table->decimal('mpv', 6, 2)->nullable();
            $table->decimal('neutrophils', 6, 2)->nullable();
            $table->decimal('lymphocytes', 6, 2)->nullable();
            $table->decimal('monocytes', 6, 2)->nullable();
            $table->decimal('eosinophils', 6, 2)->nullable();
            $table->decimal('basophils', 6, 2)->nullable();
            $table->json('analyzer_flags')->nullable();
            $table->string('data_source')->default('manual_entry');
            $table->string('data_source_label')->default('Manual entry');
            $table->text('notes')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('fbc_reports');
    }
};
