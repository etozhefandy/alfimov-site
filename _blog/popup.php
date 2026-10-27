<?php
// Сгенерировано сборкой сайта (build.py: blog_popup_php) — не править руками.
// Попап под статьёй блога: по теме статьи (category, keywords, заголовок) подбирает ближайшую услугу
// агентства и предлагает бесплатную консультацию в WhatsApp. Показывается один раз за визит, после того
// как человек прочитал часть статьи (main.js: .art-popup), закрывается крестиком.
declare(strict_types=1);

const BLOG_POPUP_WA = 'https://wa.me/77769026669';
const BLOG_POPUP_DEFAULT = 'kompleksnyj-marketing';
const BLOG_POPUP_RULES = [
    [['tiktok', 'тикток', 'тик ток'], 'target-tiktok'],
    [['таргет', 'instagram', 'инстаграм', 'facebook', 'фейсбук', ' meta ', 'meta ads'], 'target-facebook-instagram'],
    [['контекст', 'google ads', 'гугл рекл', 'яндекс директ', 'директ', 'поисковая реклама'], 'kontekstnaya-reklama'],
    [['seo', 'сео', 'продвижение сайта', 'поисковое продвижение', 'поисковой выдач'], 'seo-prodvizhenie'],
    [['smm', 'смм', 'ведение инстаграм', 'ведение соцсет', 'контент-план', 'контент план'], 'smm'],
    [['исследован', 'анализ рынка', 'аналитика рынка', 'анализ конкурент'], 'marketingovye-issledovaniya'],
];
const BLOG_POPUP_SERVICES = [
    'marketingovye-issledovaniya' => ['name' => 'Маркетинговые исследования', 'short' => 'Анализ рынка, конкурентов и аудитории перед запуском и ростом.', 'url' => '/marketingovye-issledovaniya/'],
    'target-facebook-instagram' => ['name' => 'Таргет в Facebook и Instagram', 'short' => 'Реклама в Meta: заявки, продажи и сообщения в директ и WhatsApp.', 'url' => '/target-facebook-instagram/'],
    'kompleksnyj-marketing' => ['name' => 'Комплексный маркетинг', 'short' => 'Маркетинг под ключ: стратегия и все каналы в одной команде.', 'url' => '/kompleksnyj-marketing/'],
    'kontekstnaya-reklama' => ['name' => 'Контекстная реклама', 'short' => 'Google Ads и Яндекс Директ: заявки от тех, кто уже ищет ваш продукт.', 'url' => '/kontekstnaya-reklama/'],
    'seo-prodvizhenie' => ['name' => 'SEO-продвижение', 'short' => 'Вывод сайта в топ Google и Яндекса по запросам вашего бизнеса.', 'url' => '/seo-prodvizhenie/'],
    'smm' => ['name' => 'SMM-продвижение', 'short' => 'Ведение Instagram и TikTok: стратегия, контент, рост аудитории.', 'url' => '/smm/'],
    'target-tiktok' => ['name' => 'Таргет в TikTok', 'short' => 'Реклама в TikTok Ads: охват молодой аудитории, заявки и продажи.', 'url' => '/target-tiktok/'],
];

function site_article_popup(array $a): string
{
    $text = mb_strtolower($a['category'] . ' ' . implode(' ', $a['keywords']) . ' ' . $a['title']);
    $slug = BLOG_POPUP_DEFAULT;
    foreach (BLOG_POPUP_RULES as [$needles, $target]) {
        foreach ($needles as $n) {
            if (str_contains($text, $n)) { $slug = $target; break 2; }
        }
    }
    $s = BLOG_POPUP_SERVICES[$slug] ?? BLOG_POPUP_SERVICES[BLOG_POPUP_DEFAULT];
    $e = fn($v) => htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $wa = BLOG_POPUP_WA . '?text=' . rawurlencode(sprintf('Здравствуйте! Прочитал(а) статью «%s» — хочу консультацию по теме «%s».', $a['title'], $s['name']));
    return '
<aside class="art-popup" id="art-popup" data-popup-slug="' . $e($slug) . '" hidden>
  <button class="art-popup-close" type="button" aria-label="Закрыть">&times;</button>
  <p class="art-popup-eyebrow">Читаете про «' . $e($s['name']) . '»?</p>
  <p class="art-popup-text">' . $e($s['short']) . ' Бесплатная консультация — обсудим именно вашу задачу.</p>
  <div class="art-popup-row">
    <a class="btn btn-sm" href="' . $e($wa) . '" target="_blank" rel="noopener" data-popup-cta><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20l1.2-4A8 8 0 1 1 8 18.8Z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-2-1-1 .8c-1-.5-2-1.5-2.3-2.3l.8-1-1-2-1 .5Z"/></svg>Написать в WhatsApp</a>
    <a class="art-popup-more" href="' . $e($s['url']) . '">Подробнее об услуге →</a>
  </div>
</aside>';
}
