<?php
// Дополнение вебхука бота из общего движка (engine/static/api/tg-hook.php): рекламные страницы заказчиков —
// в списке «сайтов» бота, чтобы каждому заказчику можно было привязать свою группу.
declare(strict_types=1);
require_once __DIR__ . '/_lp.php';

function site_tg_hook(): void
{
    lp_register_sites();
}
