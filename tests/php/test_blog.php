<?php
// Тесты PHP-блога и админки (без сети):  php tests/php/test_blog.php
// Нужна свежая сборка: python3 build.py (берём dist/_blog/parts.json).
declare(strict_types=1);
$root = dirname(__DIR__, 2);
$data = sys_get_temp_dir() . '/alfimov-test-' . bin2hex(random_bytes(4));
mkdir($data);
putenv("ALFIMOV_SITE=$root/dist");
putenv("ALFIMOV_DATA=$data");
putenv('ALFIMOV_NOW=2026-10-01T12:00:00+05:00');
require "$root/dist/_blog/auth.php";

$fails = 0;
function check(bool $ok, string $name): void
{
    global $fails;
    echo ($ok ? '  ok   ' : '  FAIL ') . $name . "\n";
    if (!$ok) $fails++;
}
function throws(callable $fn, string $needle): bool
{
    try { $fn(); } catch (Throwable $e) { return str_contains($e->getMessage(), $needle); }
    return false;
}
$art = fn(string $slug, array $kw = []) => $kw + ['slug' => $slug, 'title' => "Статья $slug", 'description' => 'Описание', 'body_md' => "## Раздел\n\nТекст.\n"];

echo "хранилище и расписание\n";
check(count(load_all()) >= 3, 'стартовые статьи перенесены из репозитория');
foreach (glob(articles_dir() . '/*.json') as $f) unlink($f);
save_article($art('draft'));
save_article($art('later', ['status' => 'scheduled', 'publish_at' => '2026-10-02T10:00']));
save_article($art('due', ['status' => 'scheduled', 'publish_at' => '2026-10-01T11:59', 'faq' => [['В?', 'О.']]]));
$states = [];
foreach (load_all() as $a) $states[$a['slug']] = state($a);
check($states == ['later' => 'scheduled', 'due' => 'live', 'draft' => 'draft'], 'черновик / запланирована / вышла');
check(array_column(live_articles(), 'slug') === ['due'], 'на сайте только вышедшие');
check(throws(fn() => save_article($art('Плохой адрес')), 'Адрес'), 'плохой адрес отклонён');
check(throws(fn() => save_article($art('bez-daty', ['status' => 'scheduled'])), 'дата выхода'), 'без даты не запланировать');
check(throws(fn() => save_article($art('cover', ['cover_path' => 'https://evil.example/x.png'])), 'Обложка'), 'чужая обложка отклонена');
check(throws(fn() => save_article($art('cover2', ['cover_path' => '/blog/media/../../settings.json'])), 'Обложка'), 'обход пути в обложке отклонён');
$a = get_article('draft');
save_article(['slug' => 'draft-new'] + $a, 'draft');
check(get_article('draft') === null && get_article('draft-new')['created_at'] === $a['created_at'], 'переименование сохраняет дату создания');
check(throws(fn() => save_article($art('due'), 'later'), 'занят'), 'занятый адрес отклонён');
check(slugify('Таргет в Алматы: цены 2026') === 'target-v-almaty-tseny-2026' && slugify('Қазақша жарнама') === 'kazaksha-zharnama', 'транслит RU/KZ');

echo "markdown\n";
[$html, $toc] = markdown("Вступление с **жирным** и [ссылкой](/smm/).\n\n## Раздел\n\n- один\n- два\n\n## Раздел\n\n| A | B |\n|---|---|\n| 1 | 2 |\n");
check(str_contains($html, '<strong>жирным</strong>') && str_contains($html, '<a href="/smm/">ссылкой</a>'), 'жирный и ссылка');
check(str_contains($html, '<ul><li>один</li><li>два</li></ul>') && str_contains($html, '<td>1</td>'), 'список и таблица');
check(count($toc) === 2 && $toc[0][0] !== $toc[1][0], 'уникальные якоря в оглавлении');
[$html] = markdown("# Заголовок\n\n<script>alert(1)</script> [x](javascript:alert(1))");
check(!str_contains($html, '<h1') && !str_contains($html, '<script>') && str_contains($html, 'href="#"'), 'h1→h2, HTML и javascript: экранированы');
[$html] = markdown("![подпись](/blog/media/x.webp)\n\n![чужая](https://evil.example/x.png)");
check(str_contains($html, '<img src="/blog/media/x.webp"') && !str_contains($html, 'evil.example/x.png" alt'), 'картинки только со своего сайта');

echo "страницы\n";
$due = get_article('due');
$page = render_article($due, live_articles());
check(str_contains($page, '<link rel="canonical" href="https://alfimov.kz/blog/due/">'), 'canonical статьи');
check(str_contains($page, '"@type":"BlogPosting"') && str_contains($page, '"@type":"FAQPage"'), 'разметка BlogPosting и FAQ');
check(substr_count($page, '<h1') === 1 && !str_contains($page, '%%'), 'один h1, все метки подставлены');
$home = render_home((string) file_get_contents("$root/dist/index.html"), live_articles());
check(str_contains($home, 'id="blog"') && str_contains($home, '/blog/due/') && !str_contains($home, 'BLOG-HOME'), 'свежие статьи на главной');
$sm = render_sitemap((string) file_get_contents("$root/dist/_blog/sitemap.tpl"), live_articles());
check(str_contains($sm, 'https://alfimov.kz/blog/due/') && !str_contains($sm, '/blog/later/'), 'sitemap: вышедшие есть, будущих нет');
check(str_contains(render_article(get_article('later'), [], true), 'content="noindex"'), 'предпросмотр закрыт от индекса');

echo "ИИ (без сети)\n";
$sse = "event: message_start\ndata: {\"type\":\"message_start\"}\n\n"
    . "data: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"thinking_delta\",\"thinking\":\"...\"}}\n"
    . "data: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"{\\\"slug\\\":\\\"Плохой\\\",\\\"title\\\":\\\"Т\\\",\"}}\n"
    . "data: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"\\\"faq\\\":[{\\\"q\\\":\\\"В\\\",\\\"a\\\":\\\"О\\\"}],\\\"related\\\":[\\\"due\\\",\\\"net\\\"],\\\"keywords\\\":[]}\"}}\n"
    . "data: {\"type\":\"message_delta\",\"delta\":{\"stop_reason\":\"end_turn\"}}\n";
$sent = null;
$out = write_article('Тема', ['таргет'], '', 1500, [['slug' => 'due', 'title' => 'x']], function ($body) use ($sse, &$sent) { $sent = $body; return [200, $sse]; });
check($out['faq'] === [['В', 'О']] && $out['related'] === ['due'] && $out['keywords'] === ['таргет'] && $out['slug'] === 'plohoy', 'ответ Claude из стрима разобран и почищен');
check($sent['stream'] === true && $sent['model'] === CLAUDE_MODEL && $sent['output_config']['format']['type'] === 'json_schema', 'запрос: стрим, модель, json-схема');
check(throws(fn() => write_article('Т', [], '', 1500, [], fn() => [401, '{"error":{"message":"bad"}}']), 'ключ'), 'неверный ключ — понятная ошибка');
check(throws(fn() => write_article('Т', [], '', 1500, [], fn() => [200, "data: {\"type\":\"message_delta\",\"delta\":{\"stop_reason\":\"refusal\"}}\n"]), 'отказался'), 'отказ Claude — понятная ошибка');
$prompt = image_prompt('cover', 'Заголовок', 'лид', '', 'people');
check(!preg_match('/#[0-9a-f]{3,6}\b/i', $prompt) && str_contains($prompt, 'PEOPLE:') && str_contains($prompt, 'cobalt-blue'), 'картинка: люди, синий элемент, без hex-кодов');
check(str_contains(image_prompt('cover', 'З', '', '', 'abstract'), 'NO PEOPLE'), 'картинка: абстракция без людей');
$plan = ideas_with_plan(['ideas' => [['topic' => 'A', 'main_keyword' => 'x'], ['topic' => 'B', 'main_keyword' => 'y'], ['topic' => 'C', 'main_keyword' => 'z']]], 2,
    new DateTimeImmutable('2026-10-01T09:00', tz()));
check(array_column($plan['ideas'], 'suggested_date') === ['2026-10-06T10:00', '2026-10-08T10:00', '2026-10-13T10:00'], 'план: вт и чт в 10:00, занятые дни пропущены');

echo "вход\n";
check(!is_configured() && try_setup('неверный', 'andrey', 'supersecret1', 'supersecret1') === 'Неверный код настройки', 'без кода настройки не войти');
check(password_problem('short') !== '' && password_problem('long-enough-pass') === '', 'пароль от 10 символов');

array_map('unlink', glob("$data/*/*") ?: []);
echo $fails ? "\nПРОВАЛЕНО: $fails\n" : "\nВсе проверки пройдены\n";
exit($fails ? 1 : 0);
