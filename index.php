<?php
// Пульт admin.alfimov.kz — маршруты. Устройство и функции — в pult.php.
declare(strict_types=1);
require __DIR__ . '/pult.php';
require is_file(__DIR__ . '/_crm.php') ? __DIR__ . '/_crm.php' : dirname(__DIR__) . '/static/api/_crm.php';
require is_file(__DIR__ . '/_csp.php') ? __DIR__ . '/_csp.php' : dirname(__DIR__) . '/static/api/_csp.php';
require is_file(__DIR__ . '/_hub.php') ? __DIR__ . '/_hub.php' : dirname(__DIR__) . '/static/api/_hub.php';
require is_file(__DIR__ . '/_capi.php') ? __DIR__ . '/_capi.php' : dirname(__DIR__) . '/static/api/_capi.php';
require __DIR__ . '/clients.php';
require __DIR__ . '/clarity.php';

// ---------------------------------------------------------------- маршруты

header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');
header('Referrer-Policy: same-origin');

// Сайты с посетителями будят пульт раз в 12 часов (_hub.php: hub_tick_kick) — проверить домены, SSL, сводку Clarity.
// Только со служебным ключом (hub-data/tick.key, его читают сайты этой подписки) и в заголовке, не в адресе.
// Без ключа или пока идёт прошлая проверка — сразу выходим (pult_monitor сам держит блокировку).
if (isset($_GET['tick'])) {
    $key = pult_tick_key();
    http_response_code(204);
    if ($key === '' || !hash_equals($key, (string) ($_SERVER['HTTP_X_PULT_TICK'] ?? ''))) exit;
    if (function_exists('fastcgi_finish_request')) fastcgi_finish_request();
    ignore_user_abort(true);
    @set_time_limit(180);
    pult_monitor(false);
    pult_clarity_daily();     // сводка Clarity за сутки — раз в день
    pult_clarity_weekly();    // по понедельникам — отчёт в Telegram
    exit;
}
pult_tick_key();   // создать ключ, если его ещё нет — сайты начнут будить пульт

$do = (string) ($_POST['do'] ?? '');
if (!in_array($_SERVER['REQUEST_METHOD'] ?? 'GET', ['GET', 'HEAD'], true)) {
    // всё, что меняет данные, — только со своих страниц: Origin (или Referer, если Origin нет) должен совпасть с пультом
    $self = (getenv('HUB_DEV') ? 'http' : 'https') . '://' . ($_SERVER['HTTP_HOST'] ?? '');
    $from = (string) ($_SERVER['HTTP_ORIGIN'] ?? '');
    if ($from === '' || $from === 'null') {
        $r = parse_url((string) ($_SERVER['HTTP_REFERER'] ?? ''));
        $from = isset($r['scheme'], $r['host']) ? $r['scheme'] . '://' . $r['host'] . (isset($r['port']) ? ':' . $r['port'] : '') : '';
    }
    if ($from !== $self) { http_response_code(403); exit; }
}

if (!pult_session()) {
    if (($_GET['p'] ?? '') === 'api') {
        http_response_code(401);
        header('Content-Type: application/json; charset=utf-8');
        echo '{"error":"Нужно войти в пульт"}';
        exit;
    }
    if ($do === 'send') { $err = pult_send_code(); pult_login_page($err, pult_has_challenge()); }
    if ($do === 'code') {
        $err = pult_check_code((string) ($_POST['code'] ?? ''));
        if ($err === '') {   // после входа — туда же, куда шли (только свои адреса)
            $back = (string) ($_SERVER['REQUEST_URI'] ?? '/');
            header('Location: ' . (preg_match('#^/[^/\\]#', $back) || $back === '/' ? $back : '/'), true, 303);
            exit;
        }
        pult_login_page($err, pult_has_challenge());
    }
    pult_login_page();
}

if ($do === 'logout' || $do === 'logout_all') { pult_end_session($do === 'logout_all'); header('Location: /', true, 303); exit; }
if ($do === 'watch' || $do === 'unwatch') {
    $d = strtolower(trim((string) ($_POST['d'] ?? '')));
    $d = preg_replace('#^https?://|/.*$#', '', $d);
    $cfg = pult_read('domains');
    $extra = (array) ($cfg['extra'] ?? []);
    if ($do === 'watch' && preg_match('/^[a-z0-9.-]+\.[a-z]{2,}$/', $d)) $extra[] = $d;
    if ($do === 'unwatch') $extra = array_values(array_diff($extra, [$d]));
    pult_write('domains', ['extra' => array_values(array_unique($extra))]);
    pult_monitor(true);
    header('Location: /', true, 303);
    exit;
}

if (str_starts_with($do, 'crm_') || str_starts_with($do, 'capi_') || ($_GET['p'] ?? '') === 'client') {
    $client = pult_client((string) ($_POST['c'] ?? $_GET['c'] ?? ''));
    if (!$client) { http_response_code(404); pult_page('Нет такого заказчика', '<div class="wrap"><p>Заказчик не найден. <a href="/">В пульт</a></p></div>'); }
    if ($_SERVER['REQUEST_METHOD'] === 'POST') pult_client_action($client, $do, $_POST);
    if (isset($_GET['csv'])) pult_client_csv($client, (string) ($_GET['m'] ?? ''));
    pult_client_page($client);
}

if ($do === 'clarity_key') {
    $host = (string) ($_POST['h'] ?? '');
    $token = trim((string) ($_POST['token'] ?? ''));
    if (!isset(pult_sites()[$host]) || strlen($token) < 20) pult_dashboard('Вставьте ключ целиком (Clarity → Settings → Data export).');
    $cfg = pult_clarity_cfg();
    $cfg[$host] = ['token' => $token];
    pult_write('clarity', $cfg);
    @unlink(pult_clarity_dir($host) . '/' . date('Y-m-d') . '.json');   // забрать сводку сразу — заодно проверка ключа
    $r = pult_clarity_daily()[$host] ?? '';
    pult_dashboard($r === 'ok' ? "Ключ для $host работает, сводка за сутки получена." : "Ключ сохранён, но: $r");
}
if ($do === 'clarity_retry') {
    $host = (string) ($_POST['h'] ?? '');
    if (empty(pult_clarity_cfg()[$host]['token'])) pult_dashboard('Сначала добавьте ключ.');
    @unlink(pult_clarity_dir($host) . '/' . date('Y-m-d') . '.json');
    $r = pult_clarity_daily()[$host] ?? '';
    pult_dashboard($r === 'ok' ? "Clarity ответила, сводка для $host получена." : "Clarity: $r");
}
if ($do === 'clarity_report') {
    pult_dashboard(pult_clarity_weekly(true) ? 'Отчёт отправлен в Telegram.' : 'Отчёта нет: ещё не накоплено данных (нужен ключ и хотя бы сутки).');
}

$p = (string) ($_GET['p'] ?? '');
if ($p === 'admin' || $p === 'api') {
    $site = pult_sites()[(string) ($_GET['site'] ?? '')] ?? null;
    if (!$site) { http_response_code(404); pult_page('Нет такого сайта', '<div class="wrap"><p>Сайт не найден. <a href="/">В пульт</a></p></div>'); }
    pult_site_admin($site, $p);
    exit;
}
pult_dashboard();
