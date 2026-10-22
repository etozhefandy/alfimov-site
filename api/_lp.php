<?php
// Рекламные страницы заказчиков на alfimov.kz (/lp/<заказчик>/<страница>/) — только под трафик из Meta,
// закрыты от поиска. Заявки идут тем же ботом, но как отдельный «сайт»: у каждого заказчика своя группа
// в Telegram (бот: «🔗 Привязать группу» → выбрать «lp-<заказчик>»), с заявками агентства они не смешиваются.
declare(strict_types=1);
require_once __DIR__ . '/_tg.php';
require_once __DIR__ . '/_crm.php';
require_once __DIR__ . '/_hub.php';
require_once __DIR__ . '/_capi.php';

/** Заказчики, их страницы и допустимые ответы опроса — собирает build.py из src/lp_<заказчик>.py. */
function lp_clients(): array
{
    static $c = null;
    return $c ??= (array) json_decode((string) @file_get_contents(__DIR__ . '/_lp-clients.json'), true);
}

function lp_tg_site(string $client): array
{
    return ['host' => "lp-$client", 'label' => 'реклама ' . lp_clients()[$client]['name'], 'state' => tg_data_dir() . "/telegram-lp-$client.json"];
}

/** Записать рекламные страницы заказчиков в список сайтов бота, чтобы им можно было привязать свою группу. */
function lp_register_sites(): void
{
    $dir = tg_hub_dir() . '/tg-sites';
    if (!is_dir($dir) && !@mkdir($dir, 0750, true) && !is_dir($dir)) return;
    foreach (array_keys(lp_clients()) as $client) {
        $site = lp_tg_site($client);
        $file = "$dir/{$site['host']}.json";
        if (is_file($file) && json_decode((string) @file_get_contents($file), true) === $site) continue;
        @file_put_contents($file, json_encode($site, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }
}

/** Ответ из опроса: одно значение или список (need[]), только из допустимых вариантов. */
function lp_answer(array $post, string $key, array $options): string
{
    $v = $post[$key] ?? '';
    $vals = array_map(fn($x) => trim((string) $x), is_array($v) ? $v : [$v]);
    return implode(', ', array_values(array_intersect($vals, $options)));
}

/** Заявка в виде данных — для CRM и для текста в Telegram. $phone — [красивый, цифры] из lead_phone(). */
function lp_lead_data(string $client, string $page, array $post, array $phone): array
{
    $cut = fn($k, $n) => mb_substr(trim((string) ($post[$k] ?? '')), 0, $n);
    $c = lp_clients()[$client];
    $pg = $c['pages'][$page] ?? ['title' => $page, 'questions' => []];
    $answers = [];
    foreach ($pg['questions'] as $key => [$label, $options]) {
        $a = lp_answer($post, $key, $options);
        if ($a !== '') $answers[] = [$label, $a];
    }
    $utm = [];
    foreach (['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid'] as $k) {
        $v = $cut($k, 100);
        if ($v !== '') $utm[$k] = $v;
    }
    return ['client' => $client, 'client_name' => (string) $c['name'], 'page' => $page, 'page_title' => (string) $pg['title'],
        'name' => $cut('name', 80), 'phone' => $phone[1], 'phone_pretty' => $phone[0], 'answers' => $answers,
        'city' => $cut('city', 60), 'comment' => $cut('comment', 500), 'utm' => $utm];
}

/** Текст заявки для Telegram. */
function lp_lead_text(string $client, string $page, array $post, array $phone): string
{
    $esc = fn($s) => htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $d = lp_lead_data($client, $page, $post, $phone);
    $lines = ["🔥 <b>Заявка {$esc($d['client_name'])}</b> · " . $esc($d['page_title']), ''];
    $lines[] = '👤 ' . $esc($d['name']);
    $lines[] = '📞 ' . $esc($d['phone_pretty']) . " · <a href=\"https://wa.me/{$d['phone']}\">WhatsApp</a>";
    foreach ($d['answers'] as [$label, $a]) $lines[] = "$label: " . $esc($a);
    if ($d['city'] !== '') $lines[] = '📍 Город ' . $esc($d['city']);
    if ($d['comment'] !== '') $lines[] = '💬 ' . $esc($d['comment']);
    $utm = [];
    foreach (['utm_source', 'utm_campaign', 'utm_content', 'utm_term'] as $k) if (isset($d['utm'][$k])) $utm[] = $esc($d['utm'][$k]);
    if ($utm) $lines[] = "\n📣 " . implode(' / ', $utm);
    return implode("\n", $lines);
}

/** Что написать в Telegram после попытки передать заявку в CRM заказчика. null — CRM не подключена, писать нечего. */
function lp_crm_status_text(string $client, array $r): ?string
{
    if (!empty($r['skipped'])) return null;
    if (!empty($r['ok'])) {
        $type = CRM_TYPES[crm_config($client)['type'] ?? ''] ?? 'CRM';
        return "✅ Заявка ушла в $type" . (!empty($r['id']) ? " · №{$r['id']}" : '');
    }
    $name = (string) (lp_clients()[$client]['name'] ?? $client);
    $esc = htmlspecialchars((string) ($r['error'] ?? ''), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    return "⚠️ <b>Заявка не попала в CRM</b> ($name): $esc\n\nВ Telegram она есть выше — перенесите вручную. Исправить подключение: admin.alfimov.kz";
}
