<?php
// Вебхук Telegram-бота заявок (@alfimovkz_bot): привязка группы по PIN и команды владельца.
// Telegram подписывает запросы секретом (X-Telegram-Bot-Api-Secret-Token) — без него ничего не делаем.
declare(strict_types=1);
require __DIR__ . '/_tg.php';
header('X-Robots-Tag: noindex');
$secret = (string) (tg_state()['hook_secret'] ?? '');
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || $secret === ''
    || !hash_equals($secret, (string) ($_SERVER['HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN'] ?? ''))) {
    http_response_code(404);
    exit;
}
$u = json_decode((string) file_get_contents('php://input'), true);
try {
    if (is_array($u)) tg_handle_update($u);
} catch (Throwable $ex) {
    error_log('tg-hook: ' . $ex->getMessage());
}
echo 'ok';
