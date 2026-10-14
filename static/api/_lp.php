<?php
// Рекламные страницы заказчиков на alfimov.kz (/lp/<заказчик>/<страница>/) — только под трафик из Meta,
// закрыты от поиска. Заявки идут тем же ботом, но как отдельный «сайт»: у каждого заказчика своя группа
// в Telegram (бот: «🔗 Привязать группу» → выбрать «lp-<заказчик>»), с заявками агентства они не смешиваются.
declare(strict_types=1);
require_once __DIR__ . '/_tg.php';

const LP_CLIENTS = [
    'guestory' => [
        'name' => 'Guestory',
        'pages' => ['osnashenie' => 'Оснащение номерного фонда', 'branding' => 'Брендирование'],
    ],
];

// Вопросы опроса: поле → [подпись в заявке, допустимые ответы]. Чужие значения в заявку не попадут.
const LP_ANSWERS = [
    'type' => ['🏨 Объект', ['Отель', 'Гостевой дом / хостел', 'Апарт-отель', 'База отдыха / глэмпинг', 'Санаторий / СПА', 'Ресторан / кафе', 'Другое']],
    'stage' => ['🛠 Этап', ['Строится / открываемся', 'Реновация', 'Работаем, докупаем', 'Работаем, нужен брендинг']],
    'rooms' => ['🚪 Номеров', ['до 15', '15–50', '50–150', 'больше 150']],
    'need' => ['📦 Нужно', ['Постельное бельё', 'Полотенца и халаты', 'Косметика и тапочки', 'Техника в номер', 'Ресторанный текстиль', 'Всё под ключ']],
    'items' => ['🧺 Что брендировать', ['Полотенца', 'Халаты', 'Тапочки', 'Косметика', 'Постельное бельё', 'Текстиль ресторана', 'Пока не знаю']],
    'qty' => ['🔢 Тираж', ['10–50 шт.', '50–200 шт.', '200–1000 шт.', 'больше 1000']],
    'branding' => ['🏷 Брендирование', ['Да', 'Нет', 'Обсудим']],
];

function lp_tg_site(string $client): array
{
    return ['host' => "lp-$client", 'label' => 'реклама ' . LP_CLIENTS[$client]['name'], 'state' => tg_data_dir() . "/telegram-lp-$client.json"];
}

/** Записать рекламные страницы заказчиков в список сайтов бота, чтобы им можно было привязать свою группу. */
function lp_register_sites(): void
{
    $dir = tg_hub_dir() . '/tg-sites';
    if (!is_dir($dir) && !@mkdir($dir, 0750, true) && !is_dir($dir)) return;
    foreach (array_keys(LP_CLIENTS) as $client) {
        $site = lp_tg_site($client);
        $file = "$dir/{$site['host']}.json";
        if (is_file($file) && json_decode((string) @file_get_contents($file), true) === $site) continue;
        @file_put_contents($file, json_encode($site, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }
}

/** Ответ из опроса: одно значение или список (need[]), только из допустимых. */
function lp_answer(array $post, string $key): string
{
    $v = $post[$key] ?? '';
    $vals = array_map(fn($x) => trim((string) $x), is_array($v) ? $v : [$v]);
    return implode(', ', array_values(array_intersect($vals, LP_ANSWERS[$key][1])));
}

/** Текст заявки для Telegram. $phone — [красивый, цифры] из lead_phone(). */
function lp_lead_text(string $client, string $page, array $post, array $phone): string
{
    $esc = fn($s) => htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $cut = fn($k, $n) => mb_substr(trim((string) ($post[$k] ?? '')), 0, $n);
    $c = LP_CLIENTS[$client];
    $lines = ["🔥 <b>Заявка {$esc($c['name'])}</b> · " . $esc($c['pages'][$page] ?? $page), ''];
    $lines[] = '👤 ' . $esc($cut('name', 80));
    $lines[] = '📞 ' . $esc($phone[0]) . " · <a href=\"https://wa.me/{$phone[1]}\">WhatsApp</a>";
    foreach (LP_ANSWERS as $key => [$label]) {
        $a = lp_answer($post, $key);
        if ($a !== '') $lines[] = "$label: " . $esc($a);
    }
    foreach (['city' => '📍 Город', 'comment' => '💬'] as $key => $label) {
        $v = $cut($key, $key === 'comment' ? 500 : 60);
        if ($v !== '') $lines[] = "$label " . $esc($v);
    }
    $utm = [];
    foreach (['utm_source', 'utm_campaign', 'utm_content', 'utm_term'] as $k) {
        $v = $cut($k, 100);
        if ($v !== '') $utm[] = $esc($v);
    }
    if ($utm) $lines[] = "\n📣 " . implode(' / ', $utm);
    return implode("\n", $lines);
}
