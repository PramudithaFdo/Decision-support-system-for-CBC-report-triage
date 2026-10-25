<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('triage_results', function (Blueprint $table) {
            $table->id();
            $table->foreignId('fbc_report_id')->unique()->constrained()->cascadeOnDelete();
            $table->string('category');
            $table->decimal('confidence', 4, 2);
            $table->text('rule_summary');
            $table->json('uncertainty_reasons')->nullable();
            $table->json('ml_placeholder')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('triage_results');
    }
};
