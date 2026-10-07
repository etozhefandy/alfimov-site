<?php
// Telegram-бот заявок: общие функции для send.php (заявки), tg-hook.php (вебхук бота) и админки.
//
// Куда слать заявки: по умолчанию — владельцу в личку (tg_chat из tg-config.php рядом с httpdocs).
// Владелец может привязать группу: просит у бота PIN в личке (/pin), добавляет бота в группу и пишет
// там «/link PIN». Привязка и вебхук хранятся в alfimov-data/telegram.json (вне сайта).
declare(strict_types=1);

const TG_PIN_TTL = 900;        // PIN живёт 15 минут
const TG_PIN_MAX_TRIES = 10;   // столько неверных PIN — и текущий сгорает

function tg_cfg(): array
{
    $external = getenv('ALFIMOV_TG_CONFIG') ?: dirname(__DIR__, 2) . '/tg-config.php';  // переменная — для тестов
    $cfg = is_file($external) ? require $external : (is_file(__DIR__ . '/config.php') ? require __DIR__ . '/config.php' : []);
    return is_array($cfg) ? $cfg : [];
}

function tg_state_file(): string
{
    return (getenv('ALFIMOV_DATA') ?: dirname(__DIR__, 2) . '/alfimov-data') . '/telegram.json';
}

function tg_state(): array
{
    $s = is_file(tg_state_file()) ? json_decode((string) file_get_contents(tg_state_file()), true) : null;
    return is_array($s) ? $s : [];
}

function tg_save_state(array $s): void
{
    $file = tg_state_file();
    if (!is_dir(dirname($file))) mkdir(dirname($file), 0750, true);
    $tmp = $file . '.tmp-' . bin2hex(random_bytes(4));
    file_put_contents($tmp, json_encode($s, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    rename($tmp, $file);
    @chmod($file, 0600);
}

/** Владелец бота — тот, кому заявки шли изначально (личный чат, положительный id). */
function tg_owner(): string { return (string) (tg_cfg()['tg_chat'] ?? ''); }

/** Куда сейчас слать заявки. */
function tg_destination(): string
{
    $s = tg_state();
    return (string) (($s['lead_chat'] ?? '') ?: tg_owner());
}

/** Вызов Bot API → ответ Telegram (массив) или ['ok' => false]. $call — подмена для тестов. */
function tg_api(string $method, array $params, ?callable $call = null): array
{
    if ($call) return $call($method, $params);
    $token = (string) (tg_cfg()['tg_token'] ?? '');
    if ($token === '') return ['ok' => false, 'description' => 'нет токена бота'];
    $ch = curl_init("https://api.telegram.org/bot$token/$method");
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => http_build_query($params),
        CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10]);
    $resp = json_decode((string) curl_exec($ch), true);
    return is_array($resp) ? $resp : ['ok' => false, 'description' => 'нет ответа Telegram'];
}

function tg_send(string $chat, string $text, ?callable $call = null): array
{
    return tg_api('sendMessage', ['chat_id' => $chat, 'text' => $text, 'parse_mode' => 'HTML',
        'disable_web_page_preview' => 'true'], $call);
}

/**
 * Заявка: в привязанную группу; группа стала супергруппой — переносим привязку и повторяем;
 * бота убрали из группы — отвязываем и шлём владельцу в личку. Заявка не теряется.
 */
function tg_send_lead(string $text, ?callable $call = null): bool
{
    $dest = tg_destination();
    $r = tg_send($dest, $text, $call);
    $new = $r['parameters']['migrate_to_chat_id'] ?? null;
    if (!$r['ok'] && $new) {
        $s = tg_state();
        $s['lead_chat'] = (string) $new;
        tg_save_state($s);
        $r = tg_send((string) $new, $text, $call);
    }
    if (!$r['ok'] && $dest !== tg_owner()) {
        $s = tg_state();
        $title = $s['lead_title'] ?? 'группа';
        unset($s['lead_chat'], $s['lead_title']);
        tg_save_state($s);
        $r = tg_send(tg_owner(), $text . "\n\n⚠️ Не удалось отправить в «" . htmlspecialchars($title) . "» — бота, видимо, убрали из группы. "
            . "Заявки снова приходят сюда; чтобы вернуть группу — /pin.", $call);
    }
    return !empty($r['ok']);
}

/** Новый одноразовый PIN владельцу в личку. */
function tg_issue_pin(?callable $call = null): bool
{
    $s = tg_state();
    $pin = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $s['pin_hash'] = password_hash($pin, PASSWORD_DEFAULT);
    $s['pin_expires'] = time() + TG_PIN_TTL;
    $s['pin_tries'] = 0;
    tg_save_state($s);
    $r = tg_send(tg_owner(), "🔑 PIN для привязки группы: <code>$pin</code>\n\n"
        . "1. Добавьте меня в группу, куда должны приходить заявки.\n"
        . "2. Отправьте в группе: <code>/link $pin</code>\n\n"
        . "PIN одноразовый и действует 15 минут. Никому его не пересылайте.", $call);
    return !empty($r['ok']);
}

/** Проверка PIN из группы. → true, если группа привязана. */
function tg_check_pin(string $pin, ?callable $call = null): bool
{
    $s = tg_state();
    if (empty($s['pin_hash']) || time() > (int) ($s['pin_expires'] ?? 0)) return false;
    if (password_verify($pin, $s['pin_hash'])) {
        unset($s['pin_hash'], $s['pin_expires'], $s['pin_tries']);
        tg_save_state($s);
        return true;
    }
    $s['pin_tries'] = (int) ($s['pin_tries'] ?? 0) + 1;
    if ($s['pin_tries'] >= TG_PIN_MAX_TRIES) unset($s['pin_hash'], $s['pin_expires']);
    tg_save_state($s);
    return false;
}

function tg_link_group(string $chat, string $title): void
{
    $s = tg_state();
    $s['lead_chat'] = $chat;
    $s['lead_title'] = $title;
    tg_save_state($s);
}

function tg_unlink(): void
{
    $s = tg_state();
    unset($s['lead_chat'], $s['lead_title']);
    tg_save_state($s);
}

/** Вебхук бота: Telegram шлёт обновления на /api/tg-hook.php с секретом в заголовке. */
function tg_ensure_webhook(?callable $call = null): bool
{
    $s = tg_state();
    if (empty($s['hook_secret'])) {
        $s['hook_secret'] = bin2hex(random_bytes(24));
        tg_save_state($s);
    }
    $r = tg_api('setWebhook', ['url' => 'https://alfimov.kz/api/tg-hook.php', 'secret_token' => $s['hook_secret'],
        'allowed_updates' => json_encode(['message', 'my_chat_member']), 'drop_pending_updates' => 'true'], $call);
    return !empty($r['ok']);
}

/** Обработка одного обновления от Telegram. */
function tg_handle_update(array $u, ?callable $call = null): void
{
    $owner = tg_owner();
    // бота добавили в группу — подсказать, как привязать
    $mcm = $u['my_chat_member'] ?? null;
    if ($mcm && in_array($mcm['new_chat_member']['status'] ?? '', ['member', 'administrator'], true)
        && in_array($mcm['chat']['type'] ?? '', ['group', 'supergroup'], true)) {
        tg_send((string) $mcm['chat']['id'], "👋 Я передаю заявки с сайта alfimov.kz.\nЧтобы они приходили в эту группу, владелец отправляет сюда <code>/link PIN</code> — PIN он получит у меня в личке.", $call);
        return;
    }
    $m = $u['message'] ?? null;
    if (!$m || !isset($m['chat']['id'])) return;
    $chat = (string) $m['chat']['id'];
    $from = (string) ($m['from']['id'] ?? '');
    $type = $m['chat']['type'] ?? '';
    $text = trim((string) ($m['text'] ?? ''));
    if (isset($m['migrate_to_chat_id']) && $chat === (string) (tg_state()['lead_chat'] ?? '')) {  // группа → супергруппа
        tg_link_group((string) $m['migrate_to_chat_id'], (string) (tg_state()['lead_title'] ?? ''));
        return;
    }
    if ($type === 'private') {
        if ($from !== $owner) {
            tg_send($chat, 'Это служебный бот сайта alfimov.kz. Связаться с агентством: @fandylol', $call);
            return;
        }
        if (preg_match('#^/(pin|link)\b#', $text)) { tg_issue_pin($call); return; }
        if (preg_match('#^/unlink\b#', $text)) {
            tg_unlink();
            tg_send($chat, '✅ Заявки снова приходят сюда, в личку.', $call);
            return;
        }
        $s = tg_state();
        tg_send($chat, "Заявки сейчас приходят: " . (!empty($s['lead_chat']) ? "в группу «" . htmlspecialchars((string) $s['lead_title']) . "»" : 'сюда, в личку')
            . ".\n\n/pin — получить PIN, чтобы привязать группу\n/unlink — вернуть заявки в личку", $call);
        return;
    }
    if (in_array($type, ['group', 'supergroup'], true)
        && preg_match('#^(?:/(?:link|pin)(?:@\w+)?\s+)?(\d{6})$#', $text, $mm)) {
        if (tg_check_pin($mm[1])) {
            $title = (string) ($m['chat']['title'] ?? 'группа');
            tg_link_group($chat, $title);
            tg_send($chat, '✅ Готово: заявки с сайта alfimov.kz теперь приходят в эту группу.', $call);
            tg_send($owner, "✅ Группа «" . htmlspecialchars($title) . "» привязана — заявки идут туда. Вернуть в личку: /unlink", $call);
        } else {
            tg_send($chat, '❌ PIN неверный или устарел. Новый PIN владелец получит в личке у бота: /pin', $call);
        }
    }
}
