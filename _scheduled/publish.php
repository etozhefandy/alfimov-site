<?php
// Выход статей по расписанию прямо на хостинге, без компьютера.
// Plesk → Планировщик задач → «Выполнить PHP-скрипт» httpdocs/_scheduled/publish.php, каждые 15 минут.
//
// build.py заранее собирает «сайт в момент T» для каждой запланированной статьи и кладёт
// отличия в _scheduled/<T>-<hash>/ (manifest.json + files/). Здесь копируем наступившие версии
// поверх сайта. Применённые запоминаем в .applied, чтобы не копировать их каждые 15 минут.
if (PHP_SAPI !== 'cli') { http_response_code(403); exit; }

$dir = __DIR__;
$site = dirname($dir);
$lock = fopen("$dir/.lock", 'c');
if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) exit(0);

$appliedFile = "$dir/.applied";
$applied = is_file($appliedFile) ? array_filter(array_map('trim', file($appliedFile))) : [];

$safe = function ($rel) {
    return $rel !== '' && $rel[0] !== '/' && strpos($rel, '..') === false && strpos($rel, '_scheduled/') !== 0;
};

$due = [];
foreach (glob("$dir/*/manifest.json") ?: [] as $mf) {
    $key = basename(dirname($mf));
    $m = json_decode((string) file_get_contents($mf), true);
    if (!is_array($m) || in_array($key, $applied, true)) continue;
    if ((int) ($m['at_unix'] ?? PHP_INT_MAX) <= time()) $due[$key] = $m;
}
uasort($due, function ($a, $b) { return $a['at_unix'] <=> $b['at_unix']; });

foreach ($due as $key => $m) {
    $n = 0;
    foreach ($m['files'] ?? [] as $rel) {
        if (!$safe($rel)) continue;
        $src = "$dir/$key/files/$rel";
        $dst = "$site/$rel";
        if (!is_file($src)) continue;
        if (!is_dir(dirname($dst))) mkdir(dirname($dst), 0755, true);
        $tmp = "$dst.tmp-" . getmypid();
        if (copy($src, $tmp) && rename($tmp, $dst)) $n++;
        else { @unlink($tmp); fwrite(STDERR, "не удалось записать $rel\n"); exit(1); }
    }
    foreach ($m['delete'] ?? [] as $rel) {
        if ($safe($rel) && is_file("$site/$rel")) unlink("$site/$rel");
    }
    file_put_contents($appliedFile, "$key\n", FILE_APPEND);
    echo date('Y-m-d H:i') . " опубликовано по расписанию: $key ($n файлов)\n";
}
