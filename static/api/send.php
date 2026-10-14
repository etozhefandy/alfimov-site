<?php
// Приём заявки с сайта и отправка в Telegram.
// Токен и chat_id — в tg-config.php рядом с httpdocs; привязанная группа — в alfimov-data/telegram.json.
header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex');

function reply($ok, $code = 200) {
    http_response_code($code);
    echo json_encode(['ok' => $ok]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') reply(false, 405);

$field = function ($name, $max) {
    $v = isset($_POST[$name]) ? trim((string) $_POST[$name]) : '';
    return mb_substr($v, 0, $max);
};

// Антиспам: скрытое поле должно быть пустым, форма не может быть заполнена быстрее 2 секунд.
if ($field('company', 100) !== '') reply(true);
$ts = (int) $field('ts', 20);
if ($ts > 0 && (microtime(true) * 1000 - $ts) < 2000) reply(true);

$name = $field('name', 80);
$contact = $field('contact', 80);
$message = $field('message', 1000);
$source = $field('source', 60);
$lang = $field('lang', 5);
if ($name === '' || $contact === '') reply(false, 422);
require __DIR__ . '/_phone.php';
$phone = lead_phone($contact);
if ($phone === null) reply(false, 422);
[$contact, $digits] = $phone;
if (lead_rate_limited()) reply(false, 429);

// Секреты лежат вне папки сайта (рядом с httpdocs), чтобы не попадать в публичный репозиторий.
// Куда слать — личка владельца или привязанная по PIN группа (см. _tg.php).
require __DIR__ . '/_tg.php';
$cfg = tg_cfg();
if (empty($cfg['tg_token']) || empty($cfg['tg_chat'])) reply(false, 503);

$esc = function ($s) { return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); };
$text = "🔥 <b>Новая заявка с alfimov.kz</b>\n\n"
    . "👤 " . $esc($name) . "\n"
    . "📞 " . $esc($contact) . " · <a href=\"https://wa.me/$digits\">WhatsApp</a>\n"
    . ($message !== '' ? "💬 " . $esc($message) . "\n" : '')
    . "\n📄 Страница: " . $esc($source) . " (" . $esc($lang) . ")";

$ok = tg_send_lead($text);
reply($ok, $ok ? 200 : 502);
