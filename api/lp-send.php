<?php
// Приём заявки с рекламной страницы заказчика (/lp/<заказчик>/<страница>/) → Telegram (см. _lp.php).
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex');

function reply(bool $ok, int $code = 200): void
{
    http_response_code($code);
    echo json_encode(['ok' => $ok]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') reply(false, 405);
require __DIR__ . '/_phone.php';
require __DIR__ . '/_lp.php';

// Антиспам: скрытое поле должно быть пустым, опрос не проходится быстрее 3 секунд.
if (trim((string) ($_POST['website'] ?? '')) !== '') reply(true);
$ts = (int) ($_POST['ts'] ?? 0);
if ($ts > 0 && (microtime(true) * 1000 - $ts) < 3000) reply(true);

$client = (string) ($_POST['client'] ?? '');
$page = (string) ($_POST['page'] ?? '');
if (!isset(lp_clients()[$client]['pages'][$page])) reply(false, 422);
if (trim((string) ($_POST['name'] ?? '')) === '') reply(false, 422);
$phone = lead_phone(mb_substr((string) ($_POST['phone'] ?? ''), 0, 80));
if ($phone === null) reply(false, 422);
if (lead_rate_limited()) reply(false, 429);

$cfg = tg_cfg();
if (empty($cfg['tg_token']) || empty($cfg['tg_chat'])) reply(false, 503);
lp_register_sites();
$text = lp_lead_text($client, $page, $_POST, $phone);
$ok = tg_on_site(lp_tg_site($client), fn() => tg_send_lead($text));
reply($ok, $ok ? 200 : 502);
