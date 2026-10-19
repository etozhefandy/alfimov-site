<?php
// Пульт admin.alfimov.kz — функции (маршруты — в index.php). Одно место для всех сайтов хостинга.
//
// Вход — одноразовый код из Telegram-бота заявок (приходит владельцу в личку), без паролей.
// Сайты находятся сами: всё, что лежит в той же подписке Plesk и собрано на движке (есть _blog/site.php).
// Админка сайта (блог, SEO, заявки) открывается здесь же — /s/<домен>/admin/ — кодом, который выложен
// на самом сайте: пульт только проверяет вход и подключает его, поэтому у каждого сайта своя версия движка.
//
// Все функции пульта — с префиксом pult_: в одном запросе с ними работает код движка сайта.
declare(strict_types=1);
date_default_timezone_set('Asia/Almaty');

const PULT_COOKIE = 'pult_s';
const PULT_SESSION_DAYS = 30;
const PULT_CODE_TTL = 300;          // код входа живёт 5 минут
const PULT_CODE_TRIES = 5;          // неверных попыток на один код
const PULT_SENDS_PER_HOUR = 6;      // кодов в час — больше не шлём (защита от спама владельцу)
const PULT_MONITOR_TTL = 43200;     // проверка доменов и SSL — раз в 12 часов
const PULT_WARN_DAYS = 30;          // предупреждать, если до конца домена/SSL меньше

/** Папка подписки Plesk: в ней лежат сайты, бот (tg-config.php) и данные пульта. */
function pult_base(): string { return rtrim(getenv('HUB_BASE') ?: dirname(__DIR__), '/'); }
function pult_data(): string { return pult_base() . '/hub-data'; }

function pult_read(string $name): array
{
    $f = pult_data() . "/$name.json";
    $v = is_file($f) ? json_decode((string) file_get_contents($f), true) : null;
    return is_array($v) ? $v : [];
}

function pult_write(string $name, array $v): void
{
    if (!is_dir(pult_data())) mkdir(pult_data(), 0750, true);
    $f = pult_data() . "/$name.json";
    $tmp = "$f.tmp-" . bin2hex(random_bytes(4));
    file_put_contents($tmp, json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT));
    @chmod($tmp, 0600);
    rename($tmp, $f);
}

function pult_h($s): string { return htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

// ---------------------------------------------------------------- Telegram

function pult_tg(): array
{
    $f = pult_base() . '/tg-config.php';
    $c = is_file($f) ? require $f : [];
    return is_array($c) ? $c : [];
}

function pult_tg_send(string $text): bool
{
    if (getenv('HUB_DEV')) {   // локальная проверка: код — в файл, а не в Telegram
        if (!is_dir(pult_data())) mkdir(pult_data(), 0750, true);
        @file_put_contents(pult_data() . '/dev-telegram.txt', $text . "\n", FILE_APPEND);
        return true;
    }
    $c = pult_tg();
    if (empty($c['tg_token']) || empty($c['tg_chat'])) return false;
    $ch = curl_init('https://api.telegram.org/bot' . $c['tg_token'] . '/sendMessage');
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10,
        CURLOPT_POSTFIELDS => http_build_query(['chat_id' => $c['tg_chat'], 'text' => $text, 'parse_mode' => 'HTML'])]);
    $r = json_decode((string) curl_exec($ch), true);
    return !empty($r['ok']);
}

// ---------------------------------------------------------------- вход

function pult_session(): bool
{
    $t = (string) ($_COOKIE[PULT_COOKIE] ?? '');
    if (strlen($t) !== 64) return false;
    return (pult_read('sessions')[hash('sha256', $t)] ?? 0) > time();
}

function pult_start_session(): void
{
    $t = bin2hex(random_bytes(32));
    $all = array_filter(pult_read('sessions'), fn($exp) => $exp > time());
    $all[hash('sha256', $t)] = time() + PULT_SESSION_DAYS * 86400;
    pult_write('sessions', $all);
    setcookie(PULT_COOKIE, $t, ['expires' => time() + PULT_SESSION_DAYS * 86400, 'path' => '/',
        'secure' => !getenv('HUB_DEV'), 'httponly' => true, 'samesite' => 'Strict']);
}

function pult_end_session(): void
{
    $t = (string) ($_COOKIE[PULT_COOKIE] ?? '');
    $all = pult_read('sessions');
    unset($all[hash('sha256', $t)]);
    pult_write('sessions', $all);
    setcookie(PULT_COOKIE, '', ['expires' => 1, 'path' => '/', 'secure' => !getenv('HUB_DEV'), 'httponly' => true, 'samesite' => 'Strict']);
}

/** Отправить код входа владельцу в Telegram. → '' или текст ошибки. */
function pult_send_code(): string
{
    $st = pult_read('login');
    $sent = array_values(array_filter($st['sent'] ?? [], fn($t) => $t > time() - 3600));
    if (count($sent) >= PULT_SENDS_PER_HOUR) return 'Слишком много кодов за час. Подождите немного.';
    if ($sent && end($sent) > time() - 30) return 'Код уже отправлен — проверьте Telegram. Новый можно запросить через 30 секунд.';
    $code = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $ip = (string) ($_SERVER['REMOTE_ADDR'] ?? '?');
    if (!pult_tg_send("🔐 Код входа в пульт admin.alfimov.kz: <code>$code</code>\n\nДействует 5 минут. Запрос с IP $ip. "
        . "Если входите не вы — просто ничего не делайте.")) return 'Не получилось отправить код в Telegram. Попробуйте ещё раз.';
    $sent[] = time();
    pult_write('login', ['hash' => password_hash($code, PASSWORD_DEFAULT), 'exp' => time() + PULT_CODE_TTL, 'tries' => 0, 'sent' => $sent]);
    return '';
}

/** → '' при успехе или текст ошибки. */
function pult_check_code(string $code): string
{
    $st = pult_read('login');
    if (empty($st['hash']) || time() > (int) ($st['exp'] ?? 0)) return 'Код устарел. Запросите новый.';
    if (password_verify(trim($code), $st['hash'])) {
        unset($st['hash'], $st['exp'], $st['tries']);
        pult_write('login', $st);
        pult_start_session();
        return '';
    }
    $st['tries'] = (int) ($st['tries'] ?? 0) + 1;
    if ($st['tries'] >= PULT_CODE_TRIES) unset($st['hash'], $st['exp']);
    pult_write('login', $st);
    usleep(400000);
    return $st['tries'] >= PULT_CODE_TRIES ? 'Код сгорел после 5 ошибок. Запросите новый.' : 'Неверный код';
}

// ---------------------------------------------------------------- сайты

/** Сайты на движке в этой подписке: [домен => [host, brand, url, root]]. */
function pult_sites(): array
{
    static $sites = null;
    if ($sites !== null) return $sites;
    $sites = [];
    $base = pult_base();
    foreach (['/*/_blog/site.php', '/*/*/_blog/site.php', '/*/*/*/_blog/site.php'] as $pat) {
        foreach (glob($base . $pat) ?: [] as $f) {
            $root = dirname($f, 2);
            if (realpath($root) === realpath(__DIR__)) continue;
            $src = (string) file_get_contents($f);
            $c = [];
            foreach (['SITE_HOST', 'SITE_BRAND', 'SITE_URL'] as $k) {
                $c[$k] = preg_match("/define\\('$k', '((?:[^'\\\\]|\\\\.)*)'\\)/", $src, $m) ? stripcslashes($m[1]) : '';
            }
            if ($c['SITE_HOST'] === '' || isset($sites[$c['SITE_HOST']]) || !is_file("$root/admin/api.php")) continue;
            $sites[$c['SITE_HOST']] = ['host' => $c['SITE_HOST'], 'brand' => $c['SITE_BRAND'] ?: $c['SITE_HOST'],
                'url' => $c['SITE_URL'] ?: 'https://' . $c['SITE_HOST'], 'root' => $root];
        }
    }
    ksort($sites);
    return $sites;
}

/** Рекламные страницы заказчиков, которые лежат на сайтах (/lp/…): [[client, name, pages => [[title, url]]]]. */
function pult_landings(): array
{
    $out = [];
    foreach (pult_sites() as $s) {
        $f = $s['root'] . '/api/_lp-clients.json';
        $all = is_file($f) ? json_decode((string) file_get_contents($f), true) : null;
        foreach ((array) $all as $slug => $c) {
            $pages = [];
            foreach ((array) ($c['pages'] ?? []) as $p => $info) $pages[] = [(string) ($info['title'] ?? $p), $s['url'] . "/lp/$slug/$p/"];
            $out[] = ['slug' => (string) $slug, 'name' => (string) ($c['name'] ?? $slug), 'site' => $s['host'], 'pages' => $pages];
        }
    }
    return $out;
}

// ---------------------------------------------------------------- мониторинг доменов и SSL

/** Открывается ли сайт: HTTP-код главной (после переадресаций) или null — не ответил. */
function pult_http(string $host): ?int
{
    $ch = curl_init("https://$host/");
    curl_setopt_array($ch, [CURLOPT_NOBODY => true, CURLOPT_FOLLOWLOCATION => true, CURLOPT_MAXREDIRS => 5,
        CURLOPT_TIMEOUT => 8, CURLOPT_RETURNTRANSFER => true, CURLOPT_USERAGENT => 'alfimov-pult-monitor']);
    curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $ssl_ok = !in_array(curl_errno($ch), [51, 58, 60], true);   // 51/58/60 — сертификат не прошёл проверку
    return $code ?: ($ssl_ok ? null : -1);   // -1 — сертификат не прошёл проверку
}

function pult_ssl_days(string $host): ?int
{
    $ctx = stream_context_create(['ssl' => ['capture_peer_cert' => true, 'SNI_enabled' => true, 'peer_name' => $host,
        'verify_peer' => false, 'verify_peer_name' => false]]);
    $s = @stream_socket_client("ssl://$host:443", $errno, $err, 6, STREAM_CLIENT_CONNECT, $ctx);
    if (!$s) return null;
    $cert = stream_context_get_params($s)['options']['ssl']['peer_certificate'] ?? null;
    fclose($s);
    $info = $cert ? openssl_x509_parse($cert) : null;
    return $info ? (int) floor(((int) $info['validTo_time_t'] - time()) / 86400) : null;
}

/** До окончания регистрации домена .kz (whois KazNIC). Другие зоны пока не проверяем. */
function pult_domain_days(string $host): ?int
{
    if (!preg_match('/\.(kz|қаз)$/u', $host)) return null;
    $s = @fsockopen('whois.nic.kz', 43, $errno, $err, 6);
    if (!$s) return null;
    stream_set_timeout($s, 6);
    fwrite($s, $host . "\r\n");
    $txt = '';
    while (!feof($s) && strlen($txt) < 20000) $txt .= (string) fgets($s, 1024);
    fclose($s);
    if (!preg_match('/Expiration date\.*:\s*(\d{4}-\d{2}-\d{2})/', $txt, $m)) return null;
    return (int) floor((strtotime($m[1] . ' 00:00:00 UTC') - time()) / 86400);
}

/** Домены под наблюдением: сайты хостинга + добавленные вручную (сайты заказчиков). */
function pult_watch(): array
{
    $extra = pult_read('domains')['extra'] ?? [];
    $list = array_merge(array_keys(pult_sites()), (array) $extra);
    return array_values(array_unique(array_filter($list)));
}

function pult_monitor(bool $force = false): array
{
    $m = pult_read('monitor');
    $fresh = !$force && (int) ($m['checked'] ?? 0) > time() - PULT_MONITOR_TTL;
    if ($fresh && array_keys($m['domains'] ?? []) == pult_watch() && array_key_exists('http', (array) (array_values($m['domains'] ?? [])[0] ?? []))) return $m;
    $domains = [];
    foreach (pult_watch() as $d) $domains[$d] = ['ssl' => pult_ssl_days($d), 'domain' => pult_domain_days($d), 'http' => pult_http($d)];
    $alerts = (array) ($m['alerts'] ?? []);
    $lines = [];
    foreach ($domains as $d => $x) {
        $http = $x['http'] ?? 0;
        $key = "$d:http";
        if ($http === null || $http === -1 || $http >= 400) {
            if ((int) ($alerts[$key] ?? 0) <= time() - 86400) {   // о неработающем сайте — раз в сутки
                $lines[] = "• <b>" . pult_h($d) . "</b> — " . pult_http_text($http);
                $alerts[$key] = time();
            }
        } else unset($alerts[$key]);
        foreach (['domain' => 'регистрация домена', 'ssl' => 'SSL-сертификат'] as $k => $what) {
            $days = $x[$k];
            $key = "$d:$k";
            if ($days === null || $days >= PULT_WARN_DAYS) { unset($alerts[$key]); continue; }
            if ((int) ($alerts[$key] ?? 0) > time() - 6 * 86400) continue;   // не чаще раза в неделю
            $lines[] = "• <b>" . pult_h($d) . "</b> — $what: " . ($days < 0 ? 'уже закончился' : "осталось $days дн.");
            $alerts[$key] = time();
        }
    }
    if ($lines) pult_tg_send("⏰ <b>Пульт: проблемы с сайтами</b>\n\n" . implode("\n", $lines) . "\n\nhttps://admin.alfimov.kz/");
    $m = ['checked' => time(), 'domains' => $domains, 'alerts' => $alerts];
    pult_write('monitor', $m);
    return $m;
}

// ---------------------------------------------------------------- админка сайта внутри пульта

/** Полоска пульта над админкой сайта: назад и переключатель сайтов. */
function pult_bar(string $current): string
{
    $opts = '';
    foreach (pult_sites() as $s) {
        $opts .= '<option value="' . pult_h($s['host']) . '"' . ($s['host'] === $current ? ' selected' : '') . '>' . pult_h($s['host']) . '</option>';
    }
    return '<div style="display:flex;gap:12px;align-items:center;padding:8px 16px;background:#0c1011;color:#fff;'
        . 'font:14px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif">'
        . '<a href="/" style="color:#fff;text-decoration:none;font-weight:600;white-space:nowrap">← Пульт</a>'
        . '<span style="opacity:.6">Сайт:</span>'
        . '<select onchange="location.href=\'/s/\'+this.value+\'/admin/\'" style="font:inherit;padding:4px 8px;border-radius:6px;color:#0c1011;background:#fff;border:0">' . $opts . '</select>'
        . '</div>';
}

function pult_site_admin(array $site, string $part): void
{
    define('HUB_AUTHED', true);
    define('HUB_ADMIN_BASE', '/s/' . $site['host'] . '/admin');
    if ($part === 'api') {
        $r = trim((string) ($_GET['r'] ?? ''), '/');
        if ($r === 'api/logout') {   // «Выйти» в админке сайта — выход из пульта
            pult_end_session();
            header('Content-Type: application/json');
            echo '{"ok":true}';
            exit;
        }
        if (str_starts_with($r, 'preview/')) {   // предпросмотр статьи: стили и картинки — с самого сайта
            $url = $site['url'];
            ob_start(fn($html) => preg_replace('/<head>/i', '<head><base href="' . pult_h($url) . '/">', $html, 1));
        }
        require $site['root'] . '/admin/api.php';
        return;
    }
    $bar = pult_bar($site['host']);
    ob_start(fn($html) => preg_replace('/<body([^>]*)>/i', '<body$1>' . $bar, $html, 1));
    require $site['root'] . '/admin/index.php';
}

// ---------------------------------------------------------------- страницы

function pult_page(string $title, string $body): void
{
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        . '<meta name="robots" content="noindex, nofollow"><title>' . pult_h($title) . '</title>'
        . '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect width=%2732%27 height=%2732%27 rx=%277%27 fill=%27%230c1011%27/%3E%3Ctext x=%2716%27 y=%2722%27 text-anchor=%27middle%27 font-family=%27Arial%27 font-weight=%27700%27 font-size=%2716%27 fill=%27%23fff%27%3EA%3C/text%3E%3C/svg%3E">'
        . '<style>' . PULT_CSS . '</style></head><body>' . $body . '</body></html>';
    exit;
}

const PULT_CSS = <<<'CSS'
* { box-sizing: border-box; }
body { margin: 0; background: #f5f6f7; color: #0c1011; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
a { color: #1769ff; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 24px 16px 48px; }
.top { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }
.top h1 { font-size: 22px; margin: 0; }
h2 { font-size: 17px; margin: 28px 0 12px; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.card { background: #fff; border: 1px solid #e3e5e8; border-radius: 10px; padding: 16px; }
.card h3 { margin: 0 0 2px; font-size: 17px; }
.muted { color: #6b7178; font-size: 14px; }
.row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.btn { display: inline-block; padding: 9px 14px; border-radius: 6px; border: 1px solid #cfd3d8; background: #fff; color: #0c1011;
  text-decoration: none; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn.main { background: #1769ff; border-color: #1769ff; color: #fff; }
.pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.pill { font-size: 13px; padding: 3px 8px; border-radius: 6px; background: #eef0f2; }
.ok { background: #e6f4ea; color: #1e6b34; } .warn { background: #fff4e0; color: #8a5300; } .bad { background: #fdecec; color: #b3261e; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e3e5e8; border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #eef0f2; font-size: 14px; }
th { color: #6b7178; font-weight: 600; background: #fafbfc; }
form.inline { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
input { padding: 10px 12px; border: 1px solid #cfd3d8; border-radius: 6px; font: inherit; font-size: 16px; }
.login { min-height: 100vh; display: grid; place-items: center; padding: 16px; }
.login form { width: 100%; max-width: 380px; background: #fff; border: 1px solid #e3e5e8; border-radius: 10px; padding: 28px 24px; display: grid; gap: 14px; }
.login h1 { font-size: 20px; margin: 0; }
.login input { width: 100%; letter-spacing: .2em; font-size: 22px; text-align: center; }
.login button { padding: 13px; border: 0; border-radius: 6px; background: #1769ff; color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
.link, .login button.link { background: none; border: 0; color: #1769ff; font: inherit; font-size: 14px; cursor: pointer; padding: 0; }
.err { color: #b3261e; font-size: 14px; margin: 0; }
.scroll { overflow-x: auto; }
CSS;

function pult_login_page(string $error = '', bool $codeSent = false): void
{
    $e = $error ? '<p class="err">' . pult_h($error) . '</p>' : '';
    if (!$codeSent) {
        pult_page('Вход — пульт', '<div class="login"><form method="post"><h1>Пульт ALFIMOV</h1>'
            . '<p class="muted">Код входа придёт в Telegram от бота заявок.</p>' . $e
            . '<input type="hidden" name="do" value="send"><button type="submit">Получить код в Telegram</button></form></div>');
    }
    pult_page('Вход — пульт', '<div class="login"><form method="post"><h1>Введите код</h1>'
        . '<p class="muted">Отправили 6 цифр в Telegram. Код действует 5 минут.</p>'
        . '<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" autofocus>' . $e
        . '<button type="submit" name="do" value="code">Войти</button>'
        . '<button class="link" type="submit" name="do" value="send">Отправить новый код</button></form></div>');
}

function pult_http_text(?int $code): string
{
    if ($code === null) return 'сайт не отвечает';
    if ($code === -1) return 'сайт открывается с ошибкой сертификата';
    if ($code === 402) return 'сайт отключён за неуплату (402)';
    if ($code >= 400) return "сайт отвечает ошибкой $code";
    return 'работает';
}

/** $code: 0 — ещё не проверяли (не показываем). */
function pult_http_pill(?int $code): string
{
    if ($code === 0) return '';
    $bad = $code === null || $code === -1 || $code >= 400;
    $txt = match (true) {
        $code === null => 'не отвечает', $code === -1 => 'ошибка сертификата', $code === 402 => 'отключён за неуплату',
        $code >= 400 => "ошибка $code", default => 'работает' };
    return '<span class="pill ' . ($bad ? 'bad' : 'ok') . '">Сайт: ' . $txt . '</span>';
}

function pult_days_pill(?int $days, string $what): string
{
    if ($days === null) return '<span class="pill">' . $what . ': нет данных</span>';
    $cls = $days < 7 ? 'bad' : ($days < PULT_WARN_DAYS ? 'warn' : 'ok');
    $txt = $days < 0 ? 'закончился' : "$days дн.";
    return '<span class="pill ' . $cls . '">' . $what . ': ' . $txt . '</span>';
}

function pult_dashboard(): void
{
    $mon = pult_monitor(isset($_GET['check']));
    $cards = '';
    foreach (pult_sites() as $s) {
        $ver = is_file($s['root'] . '/version.txt') ? trim((string) file_get_contents($s['root'] . '/version.txt')) : '—';
        $d = $mon['domains'][$s['host']] ?? ['ssl' => null, 'domain' => null];
        $cards .= '<div class="card"><h3>' . pult_h($s['brand']) . '</h3><div class="muted">' . pult_h($s['host']) . ' · сборка ' . pult_h($ver) . '</div>'
            . '<div class="pills">' . pult_http_pill(array_key_exists('http', $d) ? $d['http'] : 0) . pult_days_pill($d['domain'], 'Домен') . (($d['http'] ?? 0) === -1 ? '<span class="pill bad">SSL: недействителен</span>' : pult_days_pill($d['ssl'], 'SSL')) . '</div>'
            . '<div class="row"><a class="btn main" href="/s/' . pult_h($s['host']) . '/admin/">Блог, SEO, заявки</a>'
            . '<a class="btn" href="' . pult_h($s['url']) . '/" target="_blank" rel="noopener">Открыть сайт</a></div></div>';
    }
    if ($cards === '') $cards = '<div class="card muted">Сайтов на движке в этой подписке не найдено.</div>';

    $lp = '';
    foreach (pult_landings() as $c) {
        $links = '';
        foreach ($c['pages'] as [$t, $u]) $links .= '<a class="btn" href="' . pult_h($u) . '" target="_blank" rel="noopener">' . pult_h($t) . '</a>';
        $crm = crm_config($c['slug']);
        $crm_pill = crm_enabled($crm) ? '<span class="pill ok">CRM: ' . pult_h(CRM_TYPES[$crm['type']]) . '</span>' : '<span class="pill">CRM не подключена</span>';
        $lp .= '<div class="card"><h3>' . pult_h($c['name']) . '</h3><div class="muted">страницы на ' . pult_h($c['site']) . '</div>'
            . '<div class="pills">' . $crm_pill . '</div><div class="row"><a class="btn main" href="/?p=client&amp;c=' . pult_h($c['slug']) . '">Настройки и CRM</a>' . $links . '</div></div>';
    }
    $lp = $lp ? '<h2>Рекламные страницы заказчиков</h2><div class="grid">' . $lp . '</div>' : '';

    $rows = '';
    $sites = pult_sites();
    foreach ($mon['domains'] ?? [] as $dom => $x) {
        $del = isset($sites[$dom]) ? '<span class="muted">сайт хостинга</span>'
            : '<form method="post" style="margin:0"><input type="hidden" name="do" value="unwatch"><input type="hidden" name="d" value="' . pult_h($dom) . '">'
              . '<button class="link" type="submit">убрать</button></form>';
        $rows .= '<tr><td>' . pult_h($dom) . '</td><td>' . pult_http_pill(array_key_exists('http', $x) ? $x['http'] : 0) . '</td><td>' . pult_days_pill($x['domain'], 'Домен') . '</td><td>' . (($x['http'] ?? 0) === -1 ? '<span class="pill bad">SSL: недействителен</span>' : pult_days_pill($x['ssl'], 'SSL')) . '</td><td>' . $del . '</td></tr>';
    }
    $checked = (int) ($mon['checked'] ?? 0);
    $mon_html = '<h2>Домены и SSL</h2><div class="scroll"><table><tr><th>Домен</th><th>Сайт</th><th>Регистрация</th><th>Сертификат</th><th></th></tr>' . $rows . '</table></div>'
        . '<p class="muted">Проверено ' . ($checked ? date('d.m.Y H:i', $checked) : '—') . ' (Алматы). Проверка — раз в 12 часов при открытии пульта; '
        . 'если до конца меньше ' . PULT_WARN_DAYS . ' дней — бот пришлёт предупреждение. <a href="/?check=1">Проверить сейчас</a></p>'
        . '<form class="inline" method="post"><input type="hidden" name="do" value="watch">'
        . '<input name="d" placeholder="домен для слежения, например example.kz" required style="flex:1;min-width:220px">'
        . '<button class="btn" type="submit">Следить за доменом</button></form>';

    pult_page('Пульт ALFIMOV', '<div class="wrap"><div class="top"><h1>Пульт ALFIMOV</h1>'
        . '<form method="post" style="margin:0"><input type="hidden" name="do" value="logout"><button class="btn" type="submit">Выйти</button></form></div>'
        . '<h2>Сайты</h2><div class="grid">' . $cards . '</div>' . $lp . $mon_html . '</div>');
}

