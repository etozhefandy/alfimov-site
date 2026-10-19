<?php
// Пульт: страница заказчика — подключение его CRM (Kommo, amoCRM, Bitrix24, вебхук) и журнал передачи заявок.
// Библиотека передачи — _crm.php (та же, что принимает заявки на сайте).
declare(strict_types=1);

/** Заказчик по slug из рекламных страниц на сайтах хостинга. */
function pult_client(string $slug): ?array
{
    foreach (pult_landings() as $c) if ($c['slug'] === $slug) return $c;
    return null;
}

/** Применить форму к настройкам: пустой ключ = оставить прежний (если тип тот же). → [настройки, ошибка]. */
function pult_crm_from_form(array $old, array $post): array
{
    $type = (string) ($post['type'] ?? '');
    if ($type === '') return [[], ''];
    if (!isset(CRM_TYPES[$type])) return [$old, 'Неизвестный тип CRM'];
    $same = ($old['type'] ?? '') === $type;
    $c = ['type' => $type];
    $key = crm_secret_key($type);
    $secret = trim((string) ($post[$key] ?? ''));
    $c[$key] = $secret !== '' ? $secret : ($same ? (string) ($old[$key] ?? '') : '');
    if ($type === 'kommo' || $type === 'amocrm') {
        $host = crm_amo_host($type, (string) ($post['host'] ?? ''));
        if (!$host) return [$old, 'Адрес аккаунта: например guestory.kommo.com (Kommo) или guestory.amocrm.ru (amoCRM)'];
        $c['host'] = $host;
        $sel = explode(':', (string) ($post['stage'] ?? ''));   // «воронка:этап»
        if (count($sel) === 2 && (int) $sel[0] > 0) { $c['pipeline_id'] = (int) $sel[0]; $c['status_id'] = (int) $sel[1]; }
    } else {
        if ($c[$key] !== '' && !crm_url_ok($c[$key])) return [$old, 'Адрес должен начинаться с https:// и вести на обычный сайт'];
        if ($type === 'bitrix24' && !empty($post['status_id'])) $c['status_id'] = (string) $post['status_id'];
    }
    if (!empty($post['user_id']) && in_array($type, ['kommo', 'amocrm', 'bitrix24'], true)) $c['user_id'] = (int) $post['user_id'];
    if ($same && isset($old['lists'])) $c['lists'] = $old['lists'];
    return [$c, ''];
}

function pult_client_page(array $client, string $msg = '', bool $good = true): void
{
    $slug = $client['slug'];
    $c = crm_config($slug);
    $type = (string) ($c['type'] ?? '');
    $opt = fn($v, $label, $sel) => '<option value="' . pult_h($v) . '"' . ($sel ? ' selected' : '') . '>' . pult_h($label) . '</option>';

    $types = $opt('', 'Не подключена (заявки только в Telegram)', $type === '');
    foreach (CRM_TYPES as $k => $label) $types .= $opt($k, $label, $type === $k);

    $L = (array) ($c['lists'] ?? []);
    $users = '';
    if (!empty($L['users'])) {
        $users = $opt('', 'Ответственный — по умолчанию', empty($c['user_id']));
        foreach ($L['users'] as [$id, $name]) $users .= $opt($id, $name, (int) ($c['user_id'] ?? 0) === (int) $id);
        $users = '<label>Ответственный за заявки<select name="user_id">' . $users . '</select></label>';
    }
    $stages = '';
    if (!empty($L['pipelines'])) {
        $o = $opt('', 'Воронка и этап — по умолчанию (первый этап основной воронки)', empty($c['pipeline_id']));
        foreach ($L['pipelines'] as $p) {
            $o .= '<optgroup label="' . pult_h($p['name']) . '">';
            foreach ($p['statuses'] as [$sid, $sname]) $o .= $opt("{$p['id']}:$sid", $sname, (int) ($c['pipeline_id'] ?? 0) === $p['id'] && (int) ($c['status_id'] ?? 0) === $sid);
            $o .= '</optgroup>';
        }
        $stages = '<label>Куда класть заявку<select name="stage">' . $o . '</select></label>';
    } elseif (!empty($L['statuses'])) {
        $o = $opt('', 'Стадия — по умолчанию (новый лид)', empty($c['status_id']));
        foreach ($L['statuses'] as [$sid, $sname]) $o .= $opt($sid, $sname, (string) ($c['status_id'] ?? '') === (string) $sid);
        $stages = '<label>Стадия лида<select name="status_id">' . $o . '</select></label>';
    }
    $listsHint = ($stages || $users) ? '' : ($type !== '' && crm_enabled($c)
        ? '<p class="muted">Воронки и сотрудников покажем после «Проверить подключение».</p>' : '');

    $tokenHint = fn($k) => !empty($c[$k]) && $type !== '' ? 'сохранён ' . crm_mask((string) $c[$k]) . ' — оставьте пустым, чтобы не менять' : '';
    $pages = '';
    foreach ($client['pages'] as [$t, $u]) $pages .= '<a class="btn" href="' . pult_h($u) . '" target="_blank" rel="noopener">' . pult_h($t) . '</a>';

    $log = '';
    foreach (array_slice(array_filter(crm_read('crm-log'), fn($r) => ($r['client'] ?? '') === $slug), 0, 12) as $r) {
        $log .= '<tr><td>' . date('d.m H:i', (int) $r['t']) . '</td><td>' . pult_h(CRM_TYPES[$r['type']] ?? $r['type']) . (!empty($r['test']) ? ' · тест' : '') . '</td>'
            . '<td>' . ($r['ok'] ? '<span class="pill ok">в CRM' . ($r['id'] ? ' · №' . pult_h($r['id']) : '') . '</span>' : '<span class="pill bad">не ушла</span> ' . pult_h($r['error'])) . '</td></tr>';
    }
    $log = $log ? '<h2>Последние передачи в CRM</h2><div class="scroll"><table><tr><th>Когда</th><th>CRM</th><th>Итог</th></tr>' . $log . '</table></div>'
        : '<p class="muted">Заявки в CRM пока не передавались.</p>';

    $flash = $msg ? '<p class="flash ' . ($good ? 'ok' : 'bad') . '">' . pult_h($msg) . '</p>' : '';
    $enabled = crm_enabled($c);
    $tools = $enabled
        ? '<div class="row"><button class="btn" name="do" value="crm_check" form="crm">Проверить подключение</button>'
          . '<button class="btn" name="do" value="crm_test" form="crm" onclick="return confirm(\'В CRM создастся тестовая заявка «ТЕСТ (можно удалить)». Отправить?\')">Отправить тестовую заявку</button></div>'
        : '';

    $css = '<style>[hidden]{display:none!important}.flash{padding:10px 12px;border-radius:8px;margin:0 0 14px}label{display:grid;gap:4px;font-size:14px;font-weight:600;margin-bottom:12px}'
        . 'label input,label select{font-weight:400;width:100%}select{padding:10px 12px;border:1px solid #cfd3d8;border-radius:6px;font:inherit;font-size:16px;background:#fff}'
        . '.hint{font-weight:400;color:#6b7178;font-size:13px}.crm{max-width:620px}</style>';
    $js = '<script>(function(){var t=document.querySelector("[name=type]");function f(){var v=t.value,a=v==="kommo"||v==="amocrm";'
        . 'document.querySelectorAll("[data-for]").forEach(function(e){var k=e.getAttribute("data-for").split(" ");e.hidden=!(k.indexOf(v)>=0);e.querySelectorAll("input,select").forEach(function(i){i.disabled=e.hidden})});'
        . 'var h=document.querySelector("[name=host]");if(h)h.placeholder=v==="kommo"?"guestory.kommo.com":"guestory.amocrm.ru"}t.addEventListener("change",f);f()})()</script>';

    pult_page('Заказчик ' . $client['name'] . ' — пульт', $css . '<div class="wrap"><div class="top"><h1>' . pult_h($client['name']) . '</h1>'
        . '<a class="btn" href="/">← Пульт</a></div>' . $flash
        . '<div class="muted">Рекламные страницы на ' . pult_h($client['site']) . '</div><div class="row">' . $pages . '</div>'
        . pult_client_tg($client)
        . pult_client_leads($client)
        . '<h2>Куда передавать заявки</h2><p class="muted">Заявка всегда приходит в Telegram. Если подключить CRM заказчика, она ещё создаст там сделку с контактом, '
        . 'ответами из опроса и метками рекламы (UTM). Если CRM не ответит, заявку в Telegram вы всё равно получите, а об ошибке напишет бот.</p>'
        . '<form id="crm" class="card crm" method="post" autocomplete="off"><input type="hidden" name="c" value="' . pult_h($slug) . '">'
        . '<label>CRM заказчика<select name="type">' . $types . '</select></label>'
        . '<label data-for="kommo amocrm">Адрес аккаунта<input name="host" value="' . pult_h($c['host'] ?? '') . '" placeholder="guestory.kommo.com"></label>'
        . '<label data-for="kommo amocrm">Долгосрочный токен<input name="token" type="password" autocomplete="new-password" placeholder="' . pult_h($tokenHint('token')) . '">'
        . '<span class="hint">Берёт администратор CRM: Настройки → Интеграции → Создать интеграцию → Внешняя → «Ключи и доступы» → долгосрочный токен.</span></label>'
        . '<label data-for="bitrix24">Входящий вебхук<input name="url" type="password" autocomplete="new-password" placeholder="' . pult_h($tokenHint('url')) . '">'
        . '<span class="hint">Приложения → Разработчикам → Другое → Входящий вебхук; права: CRM (crm), по желанию «Пользователи». Адрес вида https://…bitrix24.kz/rest/1/…/</span></label>'
        . '<label data-for="webhook">Адрес вебхука<input name="url" type="password" autocomplete="new-password" placeholder="' . pult_h($tokenHint('url')) . '">'
        . '<span class="hint">Куда отправлять заявку POST-запросом (JSON): Make, Zapier, n8n, своя CRM.</span></label>'
        . '<div data-for="kommo amocrm bitrix24">' . $stages . $users . $listsHint . '</div>'
        . '<div class="row"><button class="btn main" name="do" value="crm_save" type="submit">Сохранить</button></div>' . $tools . '</form>'
        . $log . pult_client_capi($client) . pult_client_links($client) . '</div>' . $js);
}

/** Действия со страницы заказчика. */
function pult_client_action(array $client, string $do, array $post): void
{
    $slug = $client['slug'];
    if ($do === 'crm_save') {
        [$cfg, $err] = pult_crm_from_form(crm_config($slug), $post);
        if ($err) pult_client_page($client, $err, false);
        crm_save($slug, $cfg);
        if (crm_enabled($cfg)) {
            $r = crm_check($cfg);
            if ($r['ok']) { $cfg['lists'] = $r['lists']; crm_save($slug, $cfg); }
            pult_client_page($client, $r['ok'] ? 'Сохранено, CRM отвечает. Выберите воронку и ответственного ниже и сохраните ещё раз.' : 'Сохранено, но CRM не подключилась: ' . $r['error'], $r['ok']);
        }
        pult_client_page($client, $cfg ? 'Сохранено, но не хватает адреса или ключа.' : 'Сохранено: заявки идут только в Telegram.', true);
    }
    if ($do === 'capi_save' || $do === 'capi_off' || $do === 'capi_test') {
        $c = capi_config($slug);
        if ($do === 'capi_off') { capi_save($slug, []); pult_client_page($client, 'Отправка в Meta с сервера отключена.'); }
        if ($do === 'capi_save') {
            $pixel = preg_replace('/\D/', '', (string) ($post['pixel'] ?? ''));
            $token = trim((string) ($post['token'] ?? ''));
            $c = ['pixel' => $pixel, 'token' => $token !== '' ? $token : (string) ($c['token'] ?? ''),
                'test_code' => preg_replace('/[^A-Za-z0-9]/', '', (string) ($post['test_code'] ?? ''))];
            if ($pixel !== '' && !preg_match('/^\d{10,20}$/', $pixel)) pult_client_page($client, 'ID пикселя — это 15–16 цифр из Events Manager', false);
            capi_save($slug, $c);
            pult_client_page($client, capi_enabled($c) ? 'Сохранено: заявки будут уходить в Meta и с сервера. Проверьте кнопкой «Отправить тестовое событие».'
                : 'Сохранено, но для отправки нужны и ID пикселя, и токен.', true);
        }
        $ev = capi_event(['name' => 'Тест', 'phone' => '77000000000', 'page' => 'test', 'utm' => []],
            ['ip' => (string) ($_SERVER['REMOTE_ADDR'] ?? ''), 'ua' => (string) ($_SERVER['HTTP_USER_AGENT'] ?? ''), 'event_id' => 'test-' . bin2hex(random_bytes(4))]);
        $r = capi_send($slug, $ev, true);
        pult_client_page($client, $r['ok'] ? 'Meta приняла тестовое событие — оно появится в «Тестовых событиях» Events Manager через минуту.' : 'Не получилось: ' . ($r['error'] ?? ''), $r['ok']);
    }
    $cfg = crm_config($slug);
    if ($do === 'crm_check') {
        $r = crm_check($cfg);
        if ($r['ok']) { $cfg['lists'] = $r['lists']; crm_save($slug, $cfg); }
        pult_client_page($client, $r['ok'] ? 'CRM отвечает, ключ подходит.' : 'Не подключилась: ' . $r['error'], $r['ok']);
    }
    if ($do === 'crm_test') {
        $r = crm_send($slug, crm_test_lead($slug, $client['name']), true);
        pult_client_page($client, !empty($r['skipped']) ? 'CRM не подключена.' : ($r['ok'] ? 'Тестовая заявка создана в CRM' . (!empty($r['id']) ? ' (№' . $r['id'] . ')' : '') . '. Проверьте её там и удалите.' : 'Не получилось: ' . $r['error']), !empty($r['ok']));
    }
    pult_client_page($client);
}

/** Заявки заказчика за месяц: таблица на странице заказчика. */
function pult_client_leads(array $client): string
{
    $slug = $client['slug'];
    $months = hub_lead_months($slug);
    $month = in_array($_GET['m'] ?? '', $months, true) ? (string) $_GET['m'] : ($months[0] ?? date('Y-m'));
    $leads = hub_leads($slug, $month);
    $tabs = '';
    foreach ($months as $m) $tabs .= '<a class="btn' . ($m === $month ? ' main' : '') . '" href="/?p=client&amp;c=' . pult_h($slug) . '&amp;m=' . $m . '">' . $m . '</a>';
    if (!$leads) return '<h2>Заявки</h2><p class="muted">Заявок с рекламных страниц пока нет. Журнал ведётся с 20.10.2026 — раньше заявки были только в Telegram.</p>';
    $rows = '';
    foreach ($leads as $l) {
        $ans = '';
        foreach ((array) $l['answers'] as [$q, $a]) $ans .= '<div><span class="muted">' . pult_h(crm_label($q)) . ':</span> ' . pult_h($a) . '</div>';
        if ($l['comment'] !== '') $ans .= '<div><span class="muted">Комментарий:</span> ' . pult_h($l['comment']) . '</div>';
        $u = (array) ($l['utm'] ?? []);
        $src = implode(' / ', array_filter([$u['utm_campaign'] ?? '', $u['utm_content'] ?? '', $u['utm_term'] ?? '']));
        $crm = $l['crm'] === null ? '<span class="pill">только Telegram</span>'
            : ($l['crm']['ok'] ? '<span class="pill ok">CRM' . ($l['crm']['id'] ? ' №' . pult_h($l['crm']['id']) : '') . '</span>' : '<span class="pill bad" title="' . pult_h($l['crm']['error']) . '">CRM: ошибка</span>');
        $rows .= '<tr><td>' . date('d.m H:i', (int) $l['t']) . '</td><td><b>' . pult_h($l['name']) . '</b><br><a href="https://wa.me/' . pult_h($l['phone']) . '" target="_blank" rel="noopener">+' . pult_h($l['phone']) . '</a></td>'
            . '<td>' . pult_h($l['page_title']) . '</td><td>' . $ans . '</td><td>' . ($src !== '' ? pult_h($src) : '<span class="muted">—</span>') . '</td><td>' . $crm . '</td></tr>';
    }
    return '<h2>Заявки · ' . count($leads) . ' за ' . pult_h($month) . '</h2><div class="row" style="margin:0 0 10px">' . $tabs
        . '<a class="btn" href="/?p=client&amp;c=' . pult_h($slug) . '&amp;m=' . $month . '&amp;csv=1">Скачать CSV</a></div>'
        . '<div class="scroll"><table><tr><th>Когда</th><th>Кто</th><th>Страница</th><th>Ответы</th><th>Реклама (кампания / объявление / группа)</th><th>Передача</th></tr>' . $rows . '</table></div>';
}

function pult_client_csv(array $client, string $month): void
{
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $client['slug'] . '-leads-' . preg_replace('/[^0-9-]/', '', $month) . '.csv"');
    echo hub_leads_csv(hub_leads($client['slug'], $month));
    exit;
}

/** Ссылки для объявлений Meta: адрес страницы + параметры URL, которые Meta сама заполнит названиями кампании, группы и объявления. */
const PULT_META_PARAMS = 'utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_term={{adset.name}}&utm_content={{ad.name}}';

function pult_client_links(array $client): string
{
    $rows = '';
    foreach ($client['pages'] as [$t, $u]) {
        $rows .= '<tr><td>' . pult_h($t) . '</td><td><code>' . pult_h($u) . '</code></td><td><button class="link" type="button" data-copy="' . pult_h($u) . '">скопировать</button></td></tr>';
    }
    return '<h2>Ссылки для рекламы</h2><p class="muted">В объявлении Meta: «Ссылка на сайт» — адрес страницы, а в поле «Параметры URL» — строка ниже. '
        . 'Meta сама подставит названия кампании, группы и объявления, и в заявке будет видно, откуда она.</p>'
        . '<div class="card" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><code style="flex:1;min-width:240px;word-break:break-all">' . pult_h(PULT_META_PARAMS) . '</code>'
        . '<button class="btn" type="button" data-copy="' . pult_h(PULT_META_PARAMS) . '">Скопировать параметры</button></div>'
        . '<div class="scroll" style="margin-top:10px"><table><tr><th>Страница</th><th>Адрес</th><th></th></tr>' . $rows . '</table></div>'
        . '<script>document.querySelectorAll("[data-copy]").forEach(function(b){b.addEventListener("click",function(){var t=b.textContent;'
        . 'navigator.clipboard.writeText(b.getAttribute("data-copy")).then(function(){b.textContent="скопировано";setTimeout(function(){b.textContent=t},1500)})})})</script>';
}

/** Telegram-группа заказчика: привязана ли (бот хранит привязку в файле, путь к нему — в tg-sites/lp-<заказчик>.json). */
function pult_client_tg(array $client): string
{
    $reg = json_decode((string) @file_get_contents(pult_base() . '/tg-sites/lp-' . $client['slug'] . '.json'), true);
    $st = is_array($reg) && !empty($reg['state']) ? json_decode((string) @file_get_contents((string) $reg['state']), true) : null;
    $how = 'В боте заявок: «🔗 Привязать группу» → выбрать «реклама ' . pult_h($client['name']) . '» → добавить бота в группу и написать там PIN.';
    if (!is_array($reg)) return '<p class="muted">Telegram: бот ещё не знает этого заказчика — появится после первой заявки или сообщения боту.</p>';
    if (!empty($st['lead_chat'])) return '<p><span class="pill ok">Telegram: группа «' . pult_h($st['lead_title'] ?? 'группа') . '»</span> '
        . '<span class="muted">заявки идут вам в личку и в эту группу</span></p>';
    return '<p><span class="pill warn">Telegram: группа не привязана</span> <span class="muted">заявки идут только вам в личку. ' . $how . '</span></p>';
}

/** Meta Conversions API: пиксель, токен, тестовый код. */
function pult_client_capi(array $client): string
{
    $c = capi_config($client['slug']);
    $tok = !empty($c['token']) ? 'сохранён ' . crm_mask((string) $c['token']) . ' — оставьте пустым, чтобы не менять' : '';
    $log = '';
    foreach (array_slice(array_filter(crm_read('capi-log'), fn($r) => ($r['client'] ?? '') === $client['slug']), 0, 6) as $r) {
        $log .= '<tr><td>' . date('d.m H:i', (int) $r['t']) . (!empty($r['test']) ? ' · тест' : '') . '</td><td>'
            . ($r['ok'] ? '<span class="pill ok">принято Meta</span>' : '<span class="pill bad">ошибка</span> ' . pult_h($r['error'])) . '</td></tr>';
    }
    return '<h2>Заявки в Meta с сервера (Conversions API)</h2>'
        . '<p class="muted">Пиксель в браузере теряет часть заявок (блокировщики рекламы, iOS). Сервер отправит в Meta то же событие Lead — '
        . 'Meta склеит его с браузерным и посчитает заявку один раз, а реклама лучше обучится. Телефон и имя уходят только в зашифрованном виде.</p>'
        . '<form class="card crm" method="post" autocomplete="off"><input type="hidden" name="c" value="' . pult_h($client['slug']) . '">'
        . '<label>ID пикселя<input name="pixel" inputmode="numeric" value="' . pult_h($c['pixel'] ?? '') . '" placeholder="например 1460843041888688"></label>'
        . '<label>Токен доступа<input name="token" type="password" autocomplete="new-password" placeholder="' . pult_h($tok) . '">'
        . '<span class="hint">Events Manager → пиксель → «Настройки» → «Conversions API» → «Создать маркер доступа». Делает администратор рекламного аккаунта заказчика.</span></label>'
        . '<label>Тестовый код (необязательно)<input name="test_code" value="' . pult_h($c['test_code'] ?? '') . '" placeholder="TEST12345">'
        . '<span class="hint">Events Manager → «Тестовые события» — нужен только для кнопки проверки.</span></label>'
        . '<div class="row"><button class="btn main" name="do" value="capi_save" type="submit">Сохранить</button>'
        . (capi_enabled($c) ? '<button class="btn" name="do" value="capi_test" type="submit">Отправить тестовое событие</button>'
            . '<button class="btn" name="do" value="capi_off" type="submit" onclick="return confirm(\'Отключить отправку заявок в Meta с сервера?\')">Отключить</button>' : '')
        . '</div></form>' . ($log ? '<div class="scroll" style="margin-top:10px"><table><tr><th>Когда</th><th>Итог</th></tr>' . $log . '</table></div>' : '');
}
