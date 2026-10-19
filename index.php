<?php
// Пульт admin.alfimov.kz — маршруты. Устройство и функции — в pult.php.
declare(strict_types=1);
require __DIR__ . '/pult.php';
require is_file(__DIR__ . '/_crm.php') ? __DIR__ . '/_crm.php' : dirname(__DIR__) . '/static/api/_crm.php';
require __DIR__ . '/clients.php';

// ---------------------------------------------------------------- маршруты

header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');
header('Referrer-Policy: same-origin');

$do = (string) ($_POST['do'] ?? '');
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // формы пульта — только со своих страниц
    $o = parse_url((string) ($_SERVER['HTTP_ORIGIN'] ?? ''));
    $origin = isset($o['host']) ? $o['host'] . (isset($o['port']) ? ':' . $o['port'] : '') : '';
    if ($do !== '' && $origin !== '' && $origin !== ($_SERVER['HTTP_HOST'] ?? '')) {
        http_response_code(403);
        exit;
    }
}

if (!pult_session()) {
    if (($_GET['p'] ?? '') === 'api') {
        http_response_code(401);
        header('Content-Type: application/json; charset=utf-8');
        echo '{"error":"Нужно войти в пульт"}';
        exit;
    }
    if ($do === 'send') { $err = pult_send_code(); pult_login_page($err, $err === '' || !empty(pult_read('login')['hash'])); }
    if ($do === 'code') {
        $err = pult_check_code((string) ($_POST['code'] ?? ''));
        if ($err === '') {   // после входа — туда же, куда шли (только свои адреса)
            $back = (string) ($_SERVER['REQUEST_URI'] ?? '/');
            header('Location: ' . (preg_match('#^/[^/\\]#', $back) || $back === '/' ? $back : '/'), true, 303);
            exit;
        }
        pult_login_page($err, !empty(pult_read('login')['hash']));
    }
    pult_login_page();
}

if ($do === 'logout') { pult_end_session(); header('Location: /', true, 303); exit; }
if ($do === 'watch' || $do === 'unwatch') {
    $d = strtolower(trim((string) ($_POST['d'] ?? '')));
    $d = preg_replace('#^https?://|/.*$#', '', $d);
    $cfg = pult_read('domains');
    $extra = (array) ($cfg['extra'] ?? ['guestory.kz']);
    if ($do === 'watch' && preg_match('/^[a-z0-9.-]+\.[a-z]{2,}$/', $d)) $extra[] = $d;
    if ($do === 'unwatch') $extra = array_values(array_diff($extra, [$d]));
    pult_write('domains', ['extra' => array_values(array_unique($extra))]);
    pult_monitor(true);
    header('Location: /', true, 303);
    exit;
}

if (str_starts_with($do, 'crm_') || ($_GET['p'] ?? '') === 'client') {
    $client = pult_client((string) ($_POST['c'] ?? $_GET['c'] ?? ''));
    if (!$client) { http_response_code(404); pult_page('Нет такого заказчика', '<div class="wrap"><p>Заказчик не найден. <a href="/">В пульт</a></p></div>'); }
    if ($_SERVER['REQUEST_METHOD'] === 'POST') pult_client_action($client, $do, $_POST);
    pult_client_page($client);
}

$p = (string) ($_GET['p'] ?? '');
if ($p === 'admin' || $p === 'api') {
    $site = pult_sites()[(string) ($_GET['site'] ?? '')] ?? null;
    if (!$site) { http_response_code(404); pult_page('Нет такого сайта', '<div class="wrap"><p>Сайт не найден. <a href="/">В пульт</a></p></div>'); }
    pult_site_admin($site, $p);
    exit;
}
pult_dashboard();
