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
// Только телефон: 11 цифр с кодом 7 (8 в начале → 7; 10 цифр без кода — дописываем 7).
$digits = preg_replace('/\D/', '', $contact);
if (strlen($digits) === 11 && $digits[0] === '8') $digits = '7' . substr($digits, 1);
if (strlen($digits) === 10) $digits = '7' . $digits;
if (strlen($digits) !== 11 || $digits[0] !== '7') reply(false, 422);
$contact = sprintf('+7 (%s) %s-%s-%s', substr($digits, 1, 3), substr($digits, 4, 3), substr($digits, 7, 2), substr($digits, 9, 2));

// Простое ограничение частоты: не больше 5 заявок с одного IP за 10 минут.
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$rlFile = sys_get_temp_dir() . '/alfimov_rl_' . md5($ip);
$now = time();
$hits = array_filter(
    is_file($rlFile) ? (array) json_decode((string) @file_get_contents($rlFile), true) : [],
    function ($t) use ($now) { return $now - (int) $t < 600; }
);
if (count($hits) >= 5) reply(false, 429);
$hits[] = $now;
@file_put_contents($rlFile, json_encode(array_values($hits)));

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
