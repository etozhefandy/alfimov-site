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
        . $log . '</div>' . $js);
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
