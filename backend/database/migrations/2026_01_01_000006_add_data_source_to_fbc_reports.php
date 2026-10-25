<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasColumn('fbc_reports', 'data_source')) {
            Schema::table('fbc_reports', function (Blueprint $table): void {
                $table->string('data_source')->default('manual_entry');
            });
        }

        if (! Schema::hasColumn('fbc_reports', 'data_source_label')) {
            Schema::table('fbc_reports', function (Blueprint $table): void {
                $table->string('data_source_label')->default('Manual entry');
            });
        }
    }

    public function down(): void
    {
        foreach (['data_source_label', 'data_source'] as $column) {
            if (Schema::hasColumn('fbc_reports', $column)) {
                Schema::table('fbc_reports', function (Blueprint $table) use ($column): void {
                    $table->dropColumn($column);
                });
            }
        }
    }
};
