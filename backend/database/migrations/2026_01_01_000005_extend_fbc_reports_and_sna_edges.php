<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        $fbcColumns = [
            'mcv' => [6, 2],
            'mch' => [6, 2],
            'mchc' => [6, 2],
            'rdw' => [6, 2],
            'mpv' => [6, 2],
            'monocytes' => [6, 2],
            'eosinophils' => [6, 2],
            'basophils' => [6, 2],
        ];

        foreach ($fbcColumns as $column => [$precision, $scale]) {
            if (! Schema::hasColumn('fbc_reports', $column)) {
                Schema::table('fbc_reports', function (Blueprint $table) use ($column, $precision, $scale): void {
                    $table->decimal($column, $precision, $scale)->nullable();
                });
            }
        }

        if (! Schema::hasColumn('sna_edges', 'channel')) {
            Schema::table('sna_edges', function (Blueprint $table): void {
                $table->string('channel')->nullable();
            });
        }

        if (! Schema::hasColumn('sna_edges', 'occurred_at')) {
            Schema::table('sna_edges', function (Blueprint $table): void {
                $table->timestamp('occurred_at')->nullable();
            });
        }

        if (! Schema::hasColumn('sna_edges', 'delay_minutes')) {
            Schema::table('sna_edges', function (Blueprint $table): void {
                $table->integer('delay_minutes')->nullable();
            });
        }
    }

    public function down(): void
    {
        $fbcColumns = ['mcv', 'mch', 'mchc', 'rdw', 'mpv', 'monocytes', 'eosinophils', 'basophils'];

        foreach ($fbcColumns as $column) {
            if (Schema::hasColumn('fbc_reports', $column)) {
                Schema::table('fbc_reports', function (Blueprint $table) use ($column): void {
                    $table->dropColumn($column);
                });
            }
        }

        foreach (['channel', 'occurred_at', 'delay_minutes'] as $column) {
            if (Schema::hasColumn('sna_edges', $column)) {
                Schema::table('sna_edges', function (Blueprint $table) use ($column): void {
                    $table->dropColumn($column);
                });
            }
        }
    }
};
