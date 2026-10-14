<?php
// Тесты рекламных страниц заказчиков (без сети):  php tests/php/test_lp.php   (после python3 build.py)
declare(strict_types=1);
$root = dirname(__DIR__, 2);
$tmp = sys_get_temp_dir() . '/alfimov-lp-' . bin2hex(random_bytes(4));
mkdir($tmp);
file_put_contents("$tmp/tg-config.php", "<?php return ['tg_token' => 'T', 'tg_chat' => '111'];");
putenv("ALFIMOV_TG_CONFIG=$tmp/tg-config.php");
putenv("ALFIMOV_DATA=$tmp/data");
putenv("ALFIMOV_TG_HUB=$tmp");
require "$root/dist/api/_phone.php";
require "$root/dist/api/_lp.php";

$fails = 0;
function check(bool $ok, string $name): void { global $fails; echo ($ok ? '  ok   ' : '  FAIL ') . "$name\n"; if (!$ok) $fails++; }

check(lead_phone('8 708 888 45 21') === ['+7 (708) 888-45-21', '77088884521'], 'телефон 8… → +7 и цифры для WhatsApp');
check(lead_phone('+7 666 123 45 67') === null, 'несуществующий код +7 666 не проходит');
check(lead_phone('12345') === null, 'короткий номер не проходит');

$post = ['name' => 'Айгерим <b>', 'type' => 'Отель / гостиница', 'rooms' => '15–50', 'need' => ['Текстиль', 'взлом'],
    'stage' => 'Реновация', 'equip' => ['Сушильные машины'], 'city' => 'Астана', 'utm_campaign' => 'osn_test', 'utm_content' => 'video1'];
$t = lp_lead_text('guestory', 'osnashenie', $post, ['+7 (701) 234-56-78', '77012345678']);
check(str_contains($t, 'Заявка Guestory</b> · Оснащение под ключ'), 'заголовок: заказчик и страница');
check(str_contains($t, 'Айгерим &lt;b&gt;'), 'имя экранируется');
check(str_contains($t, 'Нужно: Текстиль') && !str_contains($t, 'взлом'), 'в ответы попадают только варианты из опроса');
check(!str_contains($t, 'Сушильные'), 'вопрос с другой страницы в заявку не попадает');
check(str_contains($t, 'Номеров: 15–50') && str_contains($t, 'Город Астана'), 'номера и город');
$t2 = lp_lead_text('guestory', 'prachechnaya', ['name' => 'А', 'equip' => ['Сушильные машины'], 'laundry_now' => 'Сдаём в городскую прачечную'], ['+7', '7']);
check(str_contains($t2, 'Прачечное оборудование') && str_contains($t2, 'Оборудование: Сушильные машины') && str_contains($t2, 'Сейчас: Сдаём'), 'страница прачечной — свои вопросы');
check(str_contains($t, 'osn_test / video1'), 'метки кампании и объявления видны в заявке');
check(str_contains($t, 'wa.me/77012345678'), 'ссылка на WhatsApp заявителя');

$t3 = lp_lead_text('guestory', 'osnashenie', ['name' => 'Б', 'type' => 'Медцентр / клиника', 'med_type' => 'Стоматология',
    'beds' => '10–30', 'need' => ['Стерилизаторы', 'Другое'], 'comment' => 'Бахилы'], ['+7', '7']);
check(str_contains($t3, 'Объект: Медцентр / клиника') && str_contains($t3, 'Медцентр: Стоматология')
    && str_contains($t3, 'Коек / кабинетов: 10–30') && str_contains($t3, 'Нужно: Стерилизаторы, Другое') && str_contains($t3, '💬 Бахилы'), 'ветка медцентра: свои вопросы и «Другое» с пояснением');

lp_register_sites();
$hosts = array_column(tg_sites(), 'host');
check(in_array('lp-guestory', $hosts, true) && $hosts[0] === 'alfimov.kz', 'Guestory в списке сайтов бота — можно привязать свою группу');

// заявка Guestory уходит в группу Guestory, а не в группу alfimov.kz
tg_link_group('-900', 'Заявки alfimov');
tg_on_site(lp_tg_site('guestory'), fn() => tg_link_group('-777', 'Guestory лиды'));
$sent = [];
$tg = function ($m, $p) use (&$sent) { $sent[] = $p['chat_id']; return ['ok' => true]; };
tg_on_site(lp_tg_site('guestory'), function () use ($tg) { tg_send_lead('x', $tg); });
check($sent === ['111', '-777'], 'заявка с рекламной страницы — владельцу и в группу Guestory');

exec('rm -rf ' . escapeshellarg($tmp));
echo $fails ? "FAILED: $fails\n" : "all ok\n";
exit($fails ? 1 : 0);
