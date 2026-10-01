<?php
// Временная диагностика хостинга (удалится следующим коммитом).
if (!hash_equals('7efd4bf8d5b6eb0bef8649654a466b0c', $_GET['t'] ?? '')) { http_response_code(404); exit; }
header('Content-Type: text/plain; charset=utf-8');
$root = dirname(__DIR__, 2);
$data = "$root/alfimov-data";
if (isset($_GET['sleep'])) {
  echo "started\n"; ignore_user_abort(true); @set_time_limit(0);
  if (function_exists('fastcgi_finish_request')) fastcgi_finish_request();
  @mkdir($data, 0750, true);
  for ($i = 10; $i <= (int)$_GET['sleep']; $i += 10) { sleep(10); file_put_contents("$data/probe-sleep.txt", date('c') . " alive $i\n", FILE_APPEND); }
  exit;
}
$out = [
  'sapi' => PHP_SAPI, 'version' => PHP_VERSION, 'user' => function_exists('posix_getpwuid') ? posix_getpwuid(posix_geteuid())['name'] : get_current_user(),
  'root' => $root, 'open_basedir' => ini_get('open_basedir'), 'max_execution_time' => ini_get('max_execution_time'),
  'set_time_limit' => @set_time_limit(300) ? 'ok' : 'fail', 'met_after' => ini_get('max_execution_time'),
  'memory_limit' => ini_get('memory_limit'), 'upload_max' => ini_get('upload_max_filesize'), 'post_max' => ini_get('post_max_size'),
  'disable_functions' => ini_get('disable_functions'), 'finish_request' => function_exists('fastcgi_finish_request'),
  'curl' => function_exists('curl_init'), 'gd_webp' => function_exists('imagewebp'), 'mb' => function_exists('mb_strlen'),
  'root_writable' => is_writable($root), 'mkdir' => (is_dir($data) || @mkdir($data, 0750, true)) ? 'ok' : 'fail',
  'data_writable' => is_writable($data), 'sess_path' => ini_get('session.save_path'),
  'root_list' => implode(' ', array_slice(scandir($root) ?: [], 0, 30)),
  'sleep_log' => @file_get_contents("$data/probe-sleep.txt"),
];
if (function_exists('curl_init')) { $c = curl_init('https://api.anthropic.com/v1/models'); curl_setopt_array($c, [CURLOPT_RETURNTRANSFER => 1, CURLOPT_TIMEOUT => 15]); curl_exec($c); $out['anthropic_http'] = curl_getinfo($c, CURLINFO_HTTP_CODE) . ' ' . curl_error($c); }
foreach ($out as $k => $v) echo "$k: " . var_export($v, true) . "\n";
