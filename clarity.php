<?php
// Пульт: поведение посетителей из Microsoft Clarity (тепловые карты стоят на сайтах, код — в сборке сайта, SITE_CLARITY).
// Clarity отдаёт сводку только за последние 1–3 дня и не больше 10 запросов в день на проект, поэтому пульт раз в день
// забирает сводку за сутки (по страницам) и копит её: hub-data/clarity/<домен>/ГГГГ-ММ-ДД.json. По понедельникам из
// накопленного — недельный отчёт в Telegram: посещаемость против прошлой недели, главные страницы, где спотыкаются.
// Ключ выгрузки (Settings → Data export → Generate new API token) — hub-data/clarity.json, в страницах только последние 4 символа.
declare(strict_types=1);

const CLARITY_API = 'https://www.clarity.ms/export-data/api/v1/project-live-insights';

function pult_clarity_cfg(): array { return pult_read('clarity'); }

/** Запрос к Clarity → [код, разобранный JSON|null, сырой ответ]. В тестах HTTP подменяется $GLOBALS['CRM_HTTP']. */
function pult_clarity_get(string $token, string $query): array
{
    $headers = ['Authorization: Bearer ' . $token, 'Accept: application/json'];   // без Content-Type: у GET без тела их nginx отвечает 400
    if (isset($GLOBALS['CRM_HTTP'])) { [$code, $body] = $GLOBALS['CRM_HTTP']('GET', CLARITY_API . "?$query", $headers, null); return [$code, $body, json_encode($body)]; }
    $ch = curl_init(CLARITY_API . "?$query");
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20, CURLOPT_HTTPHEADER => $headers, CURLOPT_USERAGENT => 'alfimov-pult']);
    $raw = (string) curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $body = json_decode($raw, true);
    return [$code, is_array($body) ? $body : null, $raw !== '' ? $raw : curl_error($ch)];
}

/** Сводка за сутки по страницам. Clarity не приняла разбивку по страницам — берём сводку по сайту целиком. → [ok, данные|текст ошибки]. */
function pult_clarity_fetch(string $token): array
{
    foreach (['numOfDays=1&dimension1=URL', 'numOfDays=1'] as $q) {
        [$code, $body, $raw] = pult_clarity_get($token, $q);
        if ($code === 200 && is_array($body)) return [true, $body];
        if ($code !== 400) break;   // 400 — не понравились параметры: пробуем проще
    }
    $why = match ($code) { 0 => "нет связи с Clarity ($raw)", 401, 403 => 'Clarity не приняла ключ — создайте новый в Settings → Data export',
        429 => 'Clarity: исчерпан лимит 10 запросов в день, попробуйте завтра', default => "Clarity ответила ошибкой $code" };
    $detail = trim(mb_substr(strip_tags((string) $raw), 0, 160));
    return [false, $why . ($detail !== '' && $code !== 429 ? ": $detail" : '')];
}

/** Число из ответа Clarity (бывают строки «9554»). */
function pult_clarity_num($v): ?float { return is_numeric($v) ? (float) $v : null; }

/** Первое найденное число из полей-кандидатов. */
function pult_clarity_pick(array $row, array $keys): ?float
{
    foreach ($keys as $k) if (isset($row[$k]) && ($n = pult_clarity_num($row[$k])) !== null) return $n;
    return null;
}

/** Ответ Clarity → [путь страницы => [sessions, scroll, active, rage, dead, quickback, errors]] (значения — суммы за сутки). */
function pult_clarity_pages(array $raw): array
{
    $pages = [];
    $metric = ['traffic' => 'sessions', 'scrolldepth' => 'scroll', 'engagementtime' => 'active', 'rageclickcount' => 'rage',
        'deadclickcount' => 'dead', 'quickbackclick' => 'quickback', 'scripterrorcount' => 'errors'];
    foreach ($raw as $m) {
        $name = $metric[strtolower(preg_replace('/\s+/', '', (string) ($m['metricName'] ?? '')))] ?? null;
        if (!$name) continue;
        foreach ((array) ($m['information'] ?? []) as $row) {
            if (!is_array($row)) continue;
            $url = (string) ($row['URL'] ?? $row['Url'] ?? $row['url'] ?? '');
            $path = $url === '' ? 'весь сайт' : (parse_url($url, PHP_URL_PATH) ?: '/');   // без разбивки по страницам — одна строка на сайт
            $p = &$pages[$path];
            $p ??= ['sessions' => 0.0, 'scroll' => null, 'active' => null, 'rage' => 0.0, 'dead' => 0.0, 'quickback' => 0.0, 'errors' => 0.0];
            switch ($name) {
                case 'sessions':
                    $all = pult_clarity_pick($row, ['totalSessionCount']) ?? 0;
                    $p['sessions'] += max(0, $all - (pult_clarity_pick($row, ['totalBotSessionCount']) ?? 0));   // без ботов
                    break;
                case 'scroll': $p['scroll'] = pult_clarity_pick($row, ['averageScrollDepth', 'scrollDepth', 'value']); break;
                case 'active': $p['active'] = pult_clarity_pick($row, ['activeTime', 'totalTime']); break;
                default: $p[$name] += pult_clarity_pick($row, ['sessionsCount', 'subTotal', 'count']) ?? 0;   // визитов с проблемой
            }
            unset($p);
        }
    }
    return $pages;
}

function pult_clarity_dir(string $host): string { return pult_data() . '/clarity/' . preg_replace('/[^a-z0-9.-]/', '', $host); }

/** Раз в день: забрать сводку за сутки по каждому сайту с ключом. $now — для тестов. → [домен => ok|ошибка]. */
function pult_clarity_daily(?int $now = null): array
{
    $now ??= time();
    $cfg = pult_clarity_cfg();
    $out = [];
    foreach ($cfg as $host => $c) {
        if (empty($c['token'])) continue;
        $file = pult_clarity_dir($host) . '/' . date('Y-m-d', $now) . '.json';
        if (is_file($file)) continue;
        [$ok, $data] = pult_clarity_fetch((string) $c['token']);
        $cfg[$host]['last'] = ['t' => $now, 'ok' => $ok, 'error' => $ok ? '' : $data];
        if ($ok) {
            if (!is_dir(dirname($file))) mkdir(dirname($file), 0750, true);
            file_put_contents($file, json_encode(['t' => $now, 'pages' => pult_clarity_pages($data)], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
            @chmod($file, 0600);
        }
        $out[$host] = $ok ? 'ok' : $data;
    }
    if ($out) pult_write('clarity', $cfg);
    return $out;
}

/** Сумма за $days дней, заканчивая днём $end (не включая $skip последних дней). → [страница => метрики], дней с данными. */
function pult_clarity_period(string $host, int $end, int $days): array
{
    $sum = [];
    $have = 0;
    for ($i = 0; $i < $days; $i++) {
        $f = pult_clarity_dir($host) . '/' . date('Y-m-d', $end - $i * 86400) . '.json';
        $d = is_file($f) ? json_decode((string) file_get_contents($f), true) : null;
        if (!is_array($d)) continue;
        $have++;
        foreach ((array) $d['pages'] as $path => $m) {
            $s = &$sum[$path];
            $s ??= ['sessions' => 0.0, 'scroll_w' => 0.0, 'scroll_n' => 0.0, 'rage' => 0.0, 'dead' => 0.0, 'quickback' => 0.0, 'errors' => 0.0];
            $s['sessions'] += (float) $m['sessions'];
            if ($m['scroll'] !== null && $m['sessions'] > 0) { $s['scroll_w'] += $m['scroll'] * $m['sessions']; $s['scroll_n'] += $m['sessions']; }
            foreach (['rage', 'dead', 'quickback', 'errors'] as $k) $s[$k] += (float) $m[$k];
            unset($s);
        }
    }
    return [$sum, $have];
}

/** Текст недельного отчёта по сайту (HTML для Telegram) или '' — данных нет. */
function pult_clarity_report(string $host, ?int $now = null, string $project = ''): string
{
    $now ??= time();
    [$week, $have] = pult_clarity_period($host, $now, 7);
    if (!$have) return '';
    [$prev] = pult_clarity_period($host, $now - 7 * 86400, 7);
    $total = array_sum(array_column($week, 'sessions'));
    $before = array_sum(array_column($prev, 'sessions'));
    $h = fn($s) => htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $lines = ['<b>' . $h($host) . '</b> — ' . (int) $total . ' визитов за неделю'
        . ($before > 0 ? ' (' . ($total >= $before ? '+' : '') . round(($total - $before) / $before * 100) . '% к прошлой)' : '')
        . ($have < 7 ? " · данные за $have дн." : '')];
    uasort($week, fn($a, $b) => $b['sessions'] <=> $a['sessions']);
    $top = array_slice($week, 0, 5, true);
    if ($top) {
        $lines[] = 'Главные страницы:';
        foreach ($top as $path => $m) {
            $scroll = $m['scroll_n'] > 0 ? ' · дочитывают до ' . round($m['scroll_w'] / $m['scroll_n']) . '%' : '';
            $lines[] = '• ' . $h($path) . ' — ' . (int) $m['sessions'] . $scroll;
        }
    }
    // что поправить: только страницы, где визитов достаточно, чтобы доля что-то значила
    $todo = [];
    foreach ($week as $path => $m) {
        if ($m['sessions'] < 20) continue;
        $p = $h($path);
        $share = fn($k) => round($m[$k] / $m['sessions'] * 100);
        if ($share('rage') >= 3) $todo[] = "$p: в {$share('rage')}% визитов злые клики (жмут по одному месту много раз) — Recordings → фильтр Rage clicks на этой странице";
        if ($share('dead') >= 15) $todo[] = "$p: в {$share('dead')}% визитов кликают по некликабельному — сделайте это ссылкой или уберите похожесть на кнопку (Heatmaps покажет, что именно)";
        if ($share('quickback') >= 15) $todo[] = "$p: в {$share('quickback')}% визитов сразу уходят назад — первый экран не про то, что ждали";
        if ($share('errors') >= 2) $todo[] = "$p: ошибки JavaScript в {$share('errors')}% визитов — что-то не работает, напишите Claude";
        if ($m['scroll_n'] >= 20 && $m['scroll_w'] / $m['scroll_n'] < 35) $todo[] = "$p: дочитывают в среднем до " . round($m['scroll_w'] / $m['scroll_n']) . '% — главное (кнопку, форму, цену) поднимите выше';
    }
    $lines[] = $todo ? "Что поправить:\n• " . implode("\n• ", array_slice($todo, 0, 6)) : 'Явных проблем Clarity не нашла.';
    if ($project !== '') $lines[] = '<a href="https://clarity.microsoft.com/projects/view/' . $h($project) . '/dashboard">Открыть в Clarity</a>';
    return implode("\n", $lines);
}

/** По понедельникам — недельный отчёт в Telegram (раз в неделю). $force — кнопка «прислать сейчас». → отправлен ли. */
function pult_clarity_weekly(bool $force = false, ?int $now = null): bool
{
    $now ??= time();
    $cfg = pult_clarity_cfg();
    if (!$cfg) return false;
    $last = (int) (pult_read('clarity-report')['t'] ?? 0);
    if (!$force && (date('N', $now) !== '1' || (int) date('G', $now) < 9 || $last > $now - 6 * 86400)) return false;
    $sites = pult_sites();
    $parts = [];
    foreach ($cfg as $host => $c) {
        if (empty($c['token'])) continue;
        $r = pult_clarity_report($host, $now, (string) ($sites[$host]['clarity'] ?? ''));
        if ($r !== '') $parts[] = $r;
    }
    if (!$parts) return false;
    $ok = pult_tg_send("📊 <b>Поведение на сайтах за неделю</b> (Microsoft Clarity)\n\n" . implode("\n\n", $parts));
    if ($ok) pult_write('clarity-report', ['t' => $now]);
    return $ok;
}

/** Блок пульта: ключи Clarity по сайтам и сводка за 7 дней. */
function pult_clarity_block(string $msg = ''): string
{
    $cfg = pult_clarity_cfg();
    $cards = '';
    foreach (pult_sites() as $host => $s) {
        $c = (array) ($cfg[$host] ?? []);
        $last = (array) ($c['last'] ?? []);
        $status = empty($c['token']) ? '<span class="pill">ключ не добавлен</span>'
            : (empty($last) ? '<span class="pill warn">ключ есть, данных ещё нет</span>'
            : ($last['ok'] ? '<span class="pill ok">сводка за ' . date('d.m', (int) $last['t']) . '</span>' : '<span class="pill bad">' . pult_h($last['error']) . '</span>'));
        [$week, $have] = pult_clarity_period($host, time(), 7);
        $visits = $have ? (int) array_sum(array_column($week, 'sessions')) . ' визитов за ' . $have . ' дн.' : '';
        $link = !empty($s['clarity']) ? '<a class="btn" href="https://clarity.microsoft.com/projects/view/' . pult_h($s['clarity']) . '/dashboard" target="_blank" rel="noopener">Открыть в Clarity</a>' : '';
        $cards .= '<div class="card"><h3>' . pult_h($host) . '</h3><div class="pills">' . $status . ($visits ? '<span class="pill">' . $visits . '</span>' : '') . '</div>'
            . '<form class="inline" method="post" autocomplete="off"><input type="hidden" name="do" value="clarity_key"><input type="hidden" name="h" value="' . pult_h($host) . '">'
            . '<input name="token" type="password" autocomplete="new-password" style="flex:1;min-width:160px" placeholder="' . (!empty($c['token']) ? 'ключ ' . pult_h(crm_mask((string) $c['token'])) : 'ключ Data export') . '">'
            . '<button class="btn" type="submit">' . (!empty($c['token']) ? 'Заменить' : 'Добавить') . '</button></form>'
            . '<div class="row">' . $link . (!empty($c['token']) ? '<form method="post" style="margin:0"><input type="hidden" name="do" value="clarity_retry"><input type="hidden" name="h" value="' . pult_h($host) . '">'
              . '<button class="btn" type="submit">Проверить ещё раз</button></form>' : '') . '</div></div>';
    }
    $flash = $msg !== '' ? '<p class="muted"><b>' . pult_h($msg) . '</b></p>' : '';
    return '<h2>Поведение посетителей (Microsoft Clarity)</h2>' . $flash
        . '<p class="muted">Ключ: Clarity → проект → Settings → Data export → Generate new API token. Пульт раз в день забирает сводку, '
        . 'по понедельникам присылает в Telegram отчёт: посещаемость, главные страницы, где спотыкаются и что поправить.</p>'
        . '<div class="grid">' . $cards . '</div>'
        . '<form method="post" style="margin-top:10px"><input type="hidden" name="do" value="clarity_report"><button class="btn" type="submit">Прислать отчёт в Telegram сейчас</button></form>';
}
