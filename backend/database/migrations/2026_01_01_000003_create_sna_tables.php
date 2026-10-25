<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('sna_nodes', function (Blueprint $table) {
            $table->id();
            $table->string('label');
            $table->string('role');
            $table->string('department')->nullable();
            $table->timestamps();
        });

        Schema::create('sna_edges', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_node_id')->constrained('sna_nodes')->cascadeOnDelete();
            $table->foreignId('target_node_id')->constrained('sna_nodes')->cascadeOnDelete();
            $table->string('interaction_type');
            $table->string('report_reference')->nullable();
            $table->string('channel')->nullable();
            $table->timestamp('occurred_at')->nullable();
            $table->unsignedInteger('delay_minutes')->nullable();
            $table->unsignedInteger('weight')->default(1);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('sna_edges');
        Schema::dropIfExists('sna_nodes');
    }
};
