<?php

use Illuminate\Support\ServiceProvider;

return [
    'name' => env('APP_NAME', 'FBC Triage Decision Support'),
    'env' => env('APP_ENV', 'production'),
    'debug' => (bool) env('APP_DEBUG', false),
    'url' => env('APP_URL', 'http://localhost'),
    'key' => env('APP_KEY'),
    'cipher' => 'AES-256-CBC',
    'timezone' => 'UTC',
    'locale' => 'en',
    'fallback_locale' => 'en',
    'faker_locale' => 'en_US',
    'providers' => ServiceProvider::defaultProviders()->toArray(),
];
