<?php
// API админки (/admin/api/*, /admin/preview/<slug>/). Только для вошедших.
//
// Долгие операции (статья ИИ 1–3 мин, картинка до минуты, идеи тем) — задачи: браузер создаёт
// задачу, отдельным запросом запускает её (/run) и опрашивает статус (/job). Если связь
// с телефона оборвётся, задача доработает на хостинге, а результат заберётся при опросе.
declare(strict_types=1);
require dirname(__DIR__) . '/_blog/auth.php';

header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');

const MAX_UPLOAD = 20 * 1024 * 1024;
const MEDIA_MAX_W = 1800;

function reply($data, int $code = 200): void
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function fail(string $msg, int $code = 400): void { reply(['error' => $msg], $code); }

function body(): array
{
    $data = json_decode((string) file_get_contents('php://input'), true);
    return is_array($data) ? $data : [];
}

function article_view(array $a): array
{
    return $a + ['state' => state($a), 'path' => article_path($a), 'read_minutes' => read_minutes($a)];
}

function mask(string $key): string { return $key === '' ? '' : '…' . substr($key, -4); }

// ---------------------------------------------------------------- картинки

function media_dir(): string { return DATA_DIR . '/media'; }

function media_name(string $base, string $ext): string
{
    $base = substr(slugify($base), 0, 60) ?: 'image';
    return $base . '-' . bin2hex(random_bytes(3)) . ".$ext";
}

/** Картинка с телефона: уменьшаем до MEDIA_MAX_W по ширине и сохраняем в webp. */
function store_upload(string $raw, string $stem): string
{
    $img = @imagecreatefromstring($raw);
    if (!$img) throw new InvalidArgumentException('Не удалось прочитать картинку — нужен jpg, png или webp');
    $w = imagesx($img);
    $h = imagesy($img);
    if ($w > MEDIA_MAX_W) {
        $img = imagescale($img, MEDIA_MAX_W, (int) round($h * MEDIA_MAX_W / $w), IMG_BICUBIC);
    }
    $name = media_name($stem, 'webp');
    if (!is_dir(media_dir())) mkdir(media_dir(), 0750, true);
    if (!imagewebp($img, media_dir() . "/$name", 82)) throw new RuntimeException('Не удалось сохранить картинку');
    return "/blog/media/$name";
}

// ---------------------------------------------------------------- задачи

function job_file(string $id): string { return DATA_DIR . "/jobs/$id.json"; }

function new_job(string $type, array $input): array
{
    $id = bin2hex(random_bytes(8));
    $job = ['id' => $id, 'type' => $type, 'input' => $input, 'status' => 'queued', 'created' => time()];
    write_json(job_file($id), $job);
    foreach (glob(DATA_DIR . '/jobs/*.json') ?: [] as $f) {  // старше суток — убрать
        if (filemtime($f) < time() - 86400) @unlink($f);
    }
    return ['job' => $id];
}

function get_job(string $id): ?array
{
    return preg_match('/^[a-f0-9]{16}$/', $id) ? read_json(job_file($id)) : null;
}

function execute(array $job): array
{
    $in = $job['input'];
    switch ($job['type']) {
        case 'generate':
            $existing = array_map(fn($a) => ['slug' => $a['slug'], 'title' => $a['title']], load_all());
            return ['article' => write_article((string) $in['topic'], $in['keywords'], (string) $in['notes'], (int) $in['words'], $existing)];
        case 'image':
            $raw = generate_image($in['kind'], (string) $in['title'], (string) $in['lead'], (string) $in['idea'], (string) $in['mode']);
            $name = media_name(($in['slug'] ?: $in['title'] ?: 'image') . '-' . ($in['kind'] === 'cover' ? 'cover' : 'img'), 'webp');
            if (!is_dir(media_dir())) mkdir(media_dir(), 0750, true);
            write_file(media_dir() . "/$name", $raw);
            return ['path' => "/blog/media/$name"];
        case 'ideas':
            return ideas_with_plan(propose_ideas((string) $in['focus']), (int) $in['per_week']);
    }
    throw new RuntimeException('Неизвестная задача');
}

/** Запускает задачу один раз (повторный /run того же id ничего не делает). */
function run_job(string $id): array
{
    $job = with_lock('jobs', function () use ($id) {
        $job = get_job($id);
        if (!$job || $job['status'] !== 'queued') return $job;
        $job['status'] = 'running';
        $job['started'] = time();
        write_json(job_file($id), $job);
        $job['_mine'] = true;
        return $job;
    });
    if (!$job) fail('Задача не найдена', 404);
    if (empty($job['_mine'])) return $job;
    unset($job['_mine']);
    ignore_user_abort(true);
    @set_time_limit(600);
    try {
        $job['result'] = execute($job);
        $job['status'] = 'done';
    } catch (AiError | InvalidArgumentException $ex) {
        $job['status'] = 'error';
        $job['error'] = $ex->getMessage();
    } catch (Throwable $ex) {
        error_log('admin job: ' . $ex);
        $job['status'] = 'error';
        $job['error'] = 'Ошибка на сервере: ' . $ex->getMessage();
    }
    $job['finished'] = time();
    write_json(job_file($id), $job);
    return $job;
}

function job_view(?array $job): array
{
    if (!$job) fail('Задача не найдена', 404);
    // Запуск оборвался (хостинг убил процесс) — честно сказать, а не крутить вечно.
    if ($job['status'] === 'running' && time() - ($job['started'] ?? time()) > 660) {
        $job['status'] = 'error';
        $job['error'] = 'Задача прервалась на сервере — попробуйте ещё раз';
    }
    return ['status' => $job['status'], 'result' => $job['result'] ?? null, 'error' => $job['error'] ?? null];
}

// ---------------------------------------------------------------- маршруты

if (!is_configured() || !current_session()) fail('Нужно войти в админку', 401);

$method = $_SERVER['REQUEST_METHOD'];
$route = trim((string) ($_GET['r'] ?? ''), '/');

// Предпросмотр — обычная ссылка (новая вкладка), без заголовка X-Admin.
if ($method === 'GET' && preg_match('#^preview/([a-z0-9-]+)$#', $route, $m)) {
    $a = get_article($m[1]);
    if (!$a) fail('Статья не найдена', 404);
    $posts = array_merge(array_values(array_filter(live_articles(), fn($p) => $p['slug'] !== $a['slug'])), [$a]);
    header('Content-Type: text/html; charset=utf-8');
    echo render_article($a, $posts, true);
    exit;
}
if ($method === 'GET' && $route === 'api/export') {
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="alfimov-blog-' . now()->format('Y-m-d') . '.json"');
    echo json_encode(['exported' => now()->format('c'), 'articles' => load_all()], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    exit;
}

// Остальное — только fetch из самой админки: свой заголовок с чужого сайта без CORS не отправить.
if (($_SERVER['HTTP_X_ADMIN'] ?? '') !== '1') fail('forbidden', 403);

try {
    if ($method === 'GET' && $route === 'api/articles') {
        reply(['articles' => array_map('article_view', load_all()), 'now' => now()->format('Y-m-d\TH:i'),
            'writer_model' => CLAUDE_MODEL]);
    }
    if ($method === 'POST' && $route === 'api/articles') {
        $d = body();
        $a = save_article(is_array($d['article'] ?? null) ? $d['article'] : [], ($d['old_slug'] ?? null) ?: null);
        reply(['article' => article_view($a)]);
    }
    if ($method === 'DELETE' && preg_match('#^api/articles/([a-z0-9-]+)$#', $route, $m)) {
        if (!delete_article($m[1])) fail('Статья не найдена', 404);
        reply(['ok' => true]);
    }
    if ($method === 'POST' && $route === 'api/generate') {
        $d = body();
        if (trim((string) ($d['topic'] ?? '')) === '') fail('Впишите тему статьи');
        reply(new_job('generate', [
            'topic' => (string) $d['topic'],
            'keywords' => preg_split('/[\n,;]+/u', (string) ($d['keywords'] ?? ''), -1, PREG_SPLIT_NO_EMPTY),
            'notes' => (string) ($d['notes'] ?? ''),
            'words' => max(500, min(4000, (int) ($d['words'] ?? 1500) ?: 1500)),
        ]));
    }
    if ($method === 'POST' && $route === 'api/image') {
        $d = body();
        reply(new_job('image', [
            'kind' => ($d['kind'] ?? '') === 'inline' ? 'inline' : 'cover',
            'title' => (string) ($d['title'] ?? ''), 'lead' => (string) ($d['lead'] ?? ''), 'idea' => (string) ($d['idea'] ?? ''),
            'slug' => (string) ($d['slug'] ?? ''), 'mode' => in_array($d['mode'] ?? '', IMG_MODES, true) ? $d['mode'] : 'auto',
        ]));
    }
    if ($method === 'POST' && $route === 'api/ideas') {
        $d = body();
        reply(new_job('ideas', ['focus' => trim((string) ($d['focus'] ?? '')), 'per_week' => (int) ($_GET['per_week'] ?? 2)]));
    }
    if ($method === 'GET' && $route === 'api/ideas') {
        reply(ideas_with_plan(read_json(DATA_DIR . '/ideas.json'), (int) ($_GET['per_week'] ?? 2)));
    }
    if ($method === 'POST' && $route === 'api/run') {
        reply(job_view(run_job((string) (body()['job'] ?? ''))));
    }
    if ($method === 'GET' && $route === 'api/job') {
        reply(job_view(get_job((string) ($_GET['id'] ?? ''))));
    }
    if ($method === 'POST' && $route === 'api/upload') {
        $d = body();
        $raw = base64_decode((string) ($d['data'] ?? ''), true);
        if (!$raw || strlen($raw) > MAX_UPLOAD) fail('Файл пустой или больше 20 МБ');
        reply(['path' => store_upload($raw, pathinfo((string) ($d['filename'] ?? 'image'), PATHINFO_FILENAME))]);
    }
    if ($method === 'GET' && $route === 'api/settings') {
        $s = settings();
        reply(['login' => $s['login'] ?? '', 'anthropic_key' => mask((string) ($s['anthropic_key'] ?? '')),
            'openai_key' => mask((string) ($s['openai_key'] ?? '')), 'writer_model' => CLAUDE_MODEL, 'image_model' => IMAGE_MODEL]);
    }
    if ($method === 'POST' && $route === 'api/settings') {
        $d = body();
        $s = settings();
        $changed = [];
        foreach (['anthropic_key' => 'sk-ant-', 'openai_key' => 'sk-'] as $field => $prefix) {
            $v = preg_replace('/\s+/', '', (string) ($d[$field] ?? ''));
            if ($v === '') continue;
            if (!str_starts_with($v, $prefix) || strlen($v) < 20) fail($field === 'anthropic_key' ? 'Ключ Claude начинается с sk-ant-' : 'Ключ OpenAI начинается с sk-');
            $s[$field] = $v;
            $changed[] = $field === 'anthropic_key' ? 'ключ Claude' : 'ключ OpenAI';
        }
        if (($d['password_new'] ?? '') !== '') {
            if (!password_verify((string) ($d['password_current'] ?? ''), (string) $s['password_hash'])) fail('Текущий пароль неверный');
            if ($p = password_problem((string) $d['password_new'])) fail($p);
            $s['password_hash'] = password_hash((string) $d['password_new'], PASSWORD_DEFAULT);
            $changed[] = 'пароль';
        }
        save_settings($s);
        if (in_array('пароль', $changed, true)) {
            drop_all_sessions();
            start_session();
        }
        reply(['ok' => true, 'changed' => $changed]);
    }
    if ($method === 'POST' && $route === 'api/logout') {
        end_session();
        reply(['ok' => true]);
    }
    fail('not found', 404);
} catch (InvalidArgumentException $ex) {
    fail($ex->getMessage());
} catch (Throwable $ex) {
    error_log('admin api: ' . $ex);
    fail('Ошибка на сервере: ' . $ex->getMessage(), 500);
}
