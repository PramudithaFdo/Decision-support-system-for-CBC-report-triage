<?php

use Illuminate\Support\Facades\Artisan;

Artisan::command('about:fbc', function () {
    $this->info('FBC Triage Decision Support MVP');
});
