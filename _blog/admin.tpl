<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Блог — админка alfimov.kz</title>
<meta name="robots" content="noindex">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>
:root {
  --bg: #fff; --soft: #f5f6f7; --ink: #0c1011; --ink-2: #3d434a; --muted: #6b7178;
  --line: #e3e5e8; --line-2: #cfd3d8; --blue: #1769ff; --blue-h: #0f57e0;
  --ok: #0f8a4f; --warn: #b26a00; --bad: #c62828; --r: 6px;
  --font: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.5 var(--font); color: var(--ink); background: var(--soft); }
button, input, select, textarea { font: inherit; color: inherit; }
.top { position: sticky; top: 0; z-index: 5; display: flex; align-items: center; gap: 12px; padding: 12px 20px; background: #fff; border-bottom: 1px solid var(--line); }
.top h1 { font-size: 16px; margin: 0 auto 0 0; font-weight: 600; }
.top h1 span { font-family: var(--mono); font-size: 12px; color: var(--muted); font-weight: 400; margin-left: 8px; }
@media (max-width: 700px) { .top { flex-wrap: wrap; } .top h1 { width: 100%; } .top h1 span { display: none; } }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border: 1px solid var(--line-2); border-radius: var(--r); background: #fff; color: var(--ink); cursor: pointer; font-weight: 500; font-size: 14px; white-space: nowrap; text-decoration: none; }
.btn:hover { border-color: var(--ink); }
.btn-p { background: var(--blue); border-color: var(--blue); color: #fff; }
.btn-p:hover { background: var(--blue-h); border-color: var(--blue-h); }
.btn-d { color: var(--bad); }
.btn-d:hover { border-color: var(--bad); }
.btn[disabled] { opacity: .55; cursor: wait; }
.layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); min-height: calc(100vh - 57px); }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
.side { background: #fff; border-right: 1px solid var(--line); padding: 16px; }
.side .btn { width: 100%; justify-content: center; margin-bottom: 12px; }
.filters { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
.filters button { border: 1px solid var(--line); background: #fff; border-radius: 99px; padding: 3px 10px; font-size: 13px; cursor: pointer; color: var(--ink-2); }
.filters button.on { border-color: var(--ink); color: var(--ink); }
.list { list-style: none; margin: 0; padding: 0; }
.list li { padding: 10px 12px; border-radius: var(--r); cursor: pointer; border: 1px solid transparent; }
.list li:hover { background: var(--soft); }
.list li.on { border-color: var(--blue); background: #f2f6ff; }
.list .t { font-weight: 500; line-height: 1.35; }
.list .m { display: flex; gap: 8px; align-items: center; margin-top: 4px; font-size: 12px; color: var(--muted); font-family: var(--mono); }
.empty { color: var(--muted); font-size: 14px; padding: 12px; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 4px; font-size: 11px; font-family: var(--mono); text-transform: uppercase; letter-spacing: .03em; }
.b-draft { background: var(--soft); color: var(--muted); }
.b-scheduled { background: #fff4e0; color: var(--warn); }
.b-live { background: #e5f6ed; color: var(--ok); }
.main { padding: 20px; display: grid; gap: 16px; align-content: start; max-width: 1180px; }
.card { background: #fff; border: 1px solid var(--line); border-radius: var(--r); padding: 20px; }
.card h2 { font-size: 15px; margin: 0 0 14px; display: flex; align-items: center; gap: 8px; }
.card h2 small { font-weight: 400; color: var(--muted); font-size: 13px; }
.grid { display: grid; gap: 14px; }
.g2 { grid-template-columns: 1fr 1fr; }
.g3 { grid-template-columns: 2fr 1fr 1fr; }
@media (max-width: 700px) { .g2, .g3 { grid-template-columns: 1fr; } }
label.f { display: grid; gap: 5px; font-size: 13px; color: var(--ink-2); font-weight: 500; }
label.f .hint { font-weight: 400; color: var(--muted); }
.cnt { font-family: var(--mono); font-size: 11px; color: var(--muted); float: right; font-weight: 400; }
.cnt.bad { color: var(--bad); } .cnt.ok { color: var(--ok); }
input[type=text], input[type=password], input[type=number], input[type=datetime-local], select, textarea {
  width: 100%; padding: 9px 11px; border: 1px solid var(--line-2); border-radius: var(--r); background: #fff; font-size: 14px;
}
input:focus, select:focus, textarea:focus { outline: 2px solid var(--blue); outline-offset: -1px; border-color: var(--blue); }
textarea { resize: vertical; line-height: 1.55; }
textarea.body { min-height: 520px; font-family: var(--mono); font-size: 13px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ai { border-color: #c9d9ff; background: #f7faff; }
.ai-status { font-size: 13px; color: var(--muted); }
.faq-item { display: grid; grid-template-columns: 1fr 2fr auto; gap: 8px; margin-bottom: 8px; }
@media (max-width: 700px) { .faq-item { grid-template-columns: 1fr; } }
.x { border: 0; background: none; color: var(--muted); cursor: pointer; font-size: 18px; padding: 0 6px; }
.x:hover { color: var(--bad); }
.rel { display: grid; gap: 4px; max-height: 180px; overflow: auto; }
.rel label { display: flex; gap: 8px; font-size: 14px; align-items: center; }
.checks { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; font-size: 14px; }
.checks li::before { display: inline-block; width: 20px; font-weight: 700; }
.checks li.ok::before { content: "✓"; color: var(--ok); }
.checks li.warn::before { content: "!"; color: var(--warn); }
.checks li.bad::before { content: "✕"; color: var(--bad); }
.ideas { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 8px; }
.idea { display: flex; gap: 16px; align-items: flex-start; justify-content: space-between; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--r); }
.idea b { display: block; margin-bottom: 4px; }
.idea.used { opacity: .55; }
.idea.used .btn { display: none; }
.idea .btn { flex: none; }
.btn-go { background: #178a4c; border-color: #178a4c; color: #fff; }
.btn-go:hover { background: #12723e; }
.cover-prev { max-width: 220px; border-radius: var(--r); border: 1px solid var(--line); display: block; margin-top: 8px; }
.toast { position: fixed; right: 20px; bottom: 20px; max-width: 460px; padding: 12px 16px; border-radius: var(--r); background: var(--ink); color: #fff; font-size: 14px; white-space: pre-line; box-shadow: 0 8px 30px rgba(0,0,0,.2); z-index: 10; }
.toast.err { background: var(--bad); }
.hidden { display: none !important; }
/* два экрана: главный (статьи, идеи, ИИ) и редактор */
.page { max-width: 1280px; margin: 0 auto; padding: 20px; }
.home, .editor { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-content: start; }
.settings { display: none; gap: 16px; align-content: start; }
body.view-edit .home, body:not(.view-edit) .editor, body.view-settings .home { display: none; }
body.view-settings .settings { display: grid; }
.warn-card { background: #fff8e6; border-color: #f0d9a8; font-size: 14px; }
.acards { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.acard { border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; cursor: pointer; background: #fff; display: flex; flex-direction: column; transition: border-color .15s; }
.acard:hover { border-color: var(--blue); }
.acard .th { aspect-ratio: 3 / 2; background: var(--soft); object-fit: cover; width: 100%; display: block; }
.acard .th.none { display: grid; place-items: center; color: var(--muted); font-size: 13px; }
.acard .b { padding: 12px 14px 14px; display: grid; gap: 8px; }
.acard .t { font-weight: 600; line-height: 1.35; }
.acard .m { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 12px; color: var(--muted); font-family: var(--mono); }
.acard .edit { color: var(--blue); font-weight: 500; font-size: 13px; }
.acards .empty { grid-column: 1 / -1; }
.ebar { position: sticky; top: 57px; z-index: 4; display: flex; gap: 8px; align-items: center; padding: 10px 14px; background: #fff; border: 1px solid var(--line); border-radius: var(--r); box-shadow: 0 4px 16px rgba(0,0,0,.05); }
.ebar-t { display: flex; gap: 10px; align-items: center; min-width: 0; }
.ebar-t { flex: 1; }
.ebar-t b { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ecols { display: grid; gap: 16px; grid-template-columns: minmax(0, 1fr) 360px; align-items: start; }
@media (max-width: 1000px) { .ecols { grid-template-columns: 1fr; } .ebar { flex-wrap: wrap; } }
.ecol-main, .ecol-side { display: grid; gap: 16px; align-content: start; }
input.big { font-size: 20px; font-weight: 600; padding: 12px 14px; }
.cover-box { border: 1px dashed var(--line-2); border-radius: var(--r); overflow: hidden; background: var(--soft); }
.cover-box .cover-prev { max-width: none; width: 100%; margin: 0; border: 0; border-radius: 0; aspect-ratio: 3 / 2; object-fit: cover; }
.cover-empty { aspect-ratio: 3 / 2; display: grid; place-items: center; color: var(--muted); font-size: 14px; }
details.more summary { cursor: pointer; font-size: 13px; color: var(--ink-2); }
details.more input { margin-top: 8px; }

.spacer { flex: 1; }

/* ---------- телефон: одна колонка, крупные поля, кнопки действий внизу под большим пальцем */
@media (max-width: 700px) {
  body { font-size: 16px; }
  input[type=text], input[type=password], input[type=number], input[type=datetime-local], select, textarea { font-size: 16px; }
  .top { padding: 10px 12px; gap: 8px; }
  .top h1 { font-size: 15px; }
  .top .btn { flex: 1; justify-content: center; padding: 8px 10px; }
  .page { padding: 12px; }
  .card { padding: 16px 14px; }
  .acards { grid-template-columns: 1fr; }
  .idea { flex-direction: column; gap: 10px; }
  .idea .btn { width: 100%; justify-content: center; }
  .row > .btn, .row > label.btn { flex: 1; justify-content: center; }
  textarea.body { min-height: 60vh; }
  .ebar { top: 0; position: static; flex-wrap: wrap; box-shadow: none; }
  .ebar-t { order: -1; width: 100%; flex-basis: 100%; }
  .ebar #b-back { flex: 1; justify-content: center; }
  .ebar .spacer, .ebar #b-save, .ebar #b-now { display: none; }
  .ebar #b-preview { flex: 1; justify-content: center; }
  .mbar { display: flex !important; }
  body.view-edit .page { padding-bottom: 88px; }
  .toast { left: 12px; right: 12px; bottom: 84px; max-width: none; }
}
.mbar { display: none; position: fixed; left: 0; right: 0; bottom: 0; z-index: 6; gap: 8px; padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
  background: #fff; border-top: 1px solid var(--line); box-shadow: 0 -4px 16px rgba(0,0,0,.06); }
.mbar .btn { flex: 1; justify-content: center; padding: 12px; font-size: 15px; }
body:not(.view-edit) .mbar { display: none !important; }
</style>
</head>
<body>
<header class="top">
  <h1>Блог alfimov.kz <span id="now"></span></h1>
  <a class="btn" href="/blog/" target="_blank">Открыть блог</a>
  <button class="btn" id="b-settings">Настройки</button>
  <button class="btn" id="b-logout">Выйти</button>
</header>
<div class="page">

  <!-- ===== ГЛАВНЫЙ ЭКРАН: статьи, идеи, ИИ ===== -->
  <div class="home">
    <section class="card warn-card hidden" id="keys-warn">
      ИИ пока выключен: вставьте ключи Claude и OpenAI в <a href="#" id="keys-link">Настройках</a>. Писать и публиковать статьи вручную можно и без них.
    </section>
    <section class="card">
      <div class="row" style="margin-bottom:14px">
        <h2 style="margin:0">Статьи</h2>
        <div class="filters" id="filters">
          <button data-f="all" class="on">Все</button>
          <button data-f="draft">Черновики</button>
          <button data-f="scheduled">Запланированы</button>
          <button data-f="live">На сайте</button>
        </div>
        <span class="spacer"></span>
        <button class="btn" id="b-new">+ Новая статья вручную</button>
      </div>
      <ul class="acards" id="list"></ul>
    </section>

    <section class="card ai" id="ideas-card">
      <h2>Идеи тем <small>живые запросы из подсказок Google и Яндекса по Казахстану → Claude</small></h2>
      <div class="row" style="gap:8px">
        <input type="text" id="i-focus" placeholder="На чём сфокусироваться (необязательно): например, TikTok или клиники" style="flex:1">
        <span class="ai-status" id="i-status"></span>
        <button class="btn btn-p" id="b-ideas">Предложить темы</button>
      </div>
      <div class="row hint" style="gap:8px;margin-top:10px;align-items:center">
        <span>Ритм публикаций:</span>
        <select id="i-week" style="width:auto"><option value="1">1 статья в неделю (вт)</option><option value="2" selected>2 статьи в неделю (вт, чт)</option><option value="3">3 статьи в неделю (пн, ср, пт)</option></select>
        <span>Выход в 10:00. Поисковикам важна регулярность, а не залп статей в один день; для нового сайта 2 в неделю — хороший темп.</span>
      </div>
      <ul class="ideas" id="ideas"></ul>
    </section>

    <section class="card ai" id="ai-card">
      <h2>Написать статью с ИИ <small id="model"></small></h2>
      <div class="grid">
        <label class="f">Тема статьи
          <input type="text" id="g-topic" placeholder="Сколько стоит таргетированная реклама в Instagram в Казахстане">
        </label>
        <div class="grid g2">
          <label class="f">Поисковые запросы <span class="hint">— через запятую или с новой строки, первый — главный</span>
            <textarea id="g-keys" rows="3" placeholder="таргетированная реклама алматы, стоимость таргета, таргетолог цена"></textarea>
          </label>
          <label class="f">Пожелания <span class="hint">— аудитория, акценты, что обязательно упомянуть</span>
            <textarea id="g-notes" rows="3" placeholder="Для владельцев кофеен и салонов. Показать пример расчёта бюджета."></textarea>
          </label>
        </div>
        <div class="row">
          <label class="f" style="width:140px">Объём, слов<input type="number" id="g-words" value="1500" min="500" max="4000" step="100"></label>
          <span class="spacer"></span>
          <span class="ai-status" id="g-status"></span>
          <button class="btn btn-p" id="b-gen">Сгенерировать черновик</button>
        </div>
      </div>
    </section>
  </div>

  <!-- ===== НАСТРОЙКИ ===== -->
  <div class="settings">
    <div class="ebar"><button class="btn" id="s-back">← Назад</button><div class="ebar-t"><b>Настройки</b></div></div>
    <section class="card">
      <h2>Ключи ИИ <small>хранятся на хостинге вне сайта, в браузер не возвращаются</small></h2>
      <div class="grid">
        <label class="f">Ключ Claude (статьи и идеи тем) <span class="hint" id="s-ant-cur"></span>
          <input type="password" id="s-ant" placeholder="sk-ant-…" autocomplete="off" spellcheck="false"></label>
        <label class="f">Ключ OpenAI (картинки) <span class="hint" id="s-oai-cur"></span>
          <input type="password" id="s-oai" placeholder="sk-…" autocomplete="off" spellcheck="false"></label>
        <p class="hint">Пустое поле — ключ не меняется. Ключи берутся на console.anthropic.com и platform.openai.com → API keys.</p>
      </div>
    </section>
    <section class="card">
      <h2>Пароль <small id="s-login"></small></h2>
      <div class="grid g2">
        <label class="f">Текущий пароль<input type="password" id="s-pass-cur" autocomplete="current-password"></label>
        <label class="f">Новый пароль (от 10 символов)<input type="password" id="s-pass-new" autocomplete="new-password"></label>
      </div>
    </section>
    <div class="row"><button class="btn btn-p" id="s-save">Сохранить настройки</button><span class="spacer"></span>
      <a class="btn" href="/admin/api/export">Скачать копию всех статей</a></div>
  </div>

  <!-- ===== РЕДАКТОР СТАТЬИ ===== -->
  <div class="editor">
    <div class="ebar">
      <button class="btn" id="b-back">← Все статьи</button>
      <div class="ebar-t"><span class="badge" id="ed-badge"></span><b id="ed-title">Новая статья</b></div>
      <span class="spacer"></span>
      <button class="btn" id="b-preview">Предпросмотр</button>
      <button class="btn btn-p" id="b-save">Сохранить</button>
      <button class="btn btn-go" id="b-now">Опубликовать сейчас</button>
    </div>

    <div class="ecols">
      <div class="ecol-main">
        <section class="card">
          <label class="f">Заголовок статьи (h1) <span class="cnt" id="c-title"></span><input type="text" id="f-title" class="big"></label>
          <label class="f" style="margin-top:14px">Лид — подзаголовок под заголовком<textarea id="f-lead" rows="2"></textarea></label>
          <label class="f" style="margin-top:14px">«Коротко» — суть статьи для читателя<textarea id="f-summary" rows="3"></textarea></label>
        </section>

        <section class="card">
          <h2>Текст статьи <small>## раздел · ### подраздел · - список · | таблица | · **жирный** · [ссылка](/smm/)</small></h2>
          <textarea class="body" id="f-body_md"></textarea>
          <div class="row" style="margin-top:10px;gap:8px;align-items:center">
            <button class="btn" type="button" id="b-inline-img">🖼 Иллюстрация в текст (ИИ)</button>
            <span class="hint">Картинка вставится туда, где стоит курсор. ~30–60 с.</span>
          </div>
        </section>

        <section class="card">
          <h2>Вопросы и ответы (FAQ) <small>попадут на страницу и в разметку для Google</small></h2>
          <div id="faq"></div>
          <button class="btn" id="b-faq" type="button">+ Вопрос</button>
        </section>

        <section class="card">
          <h2>Перелинковка <small>блок «Читайте также»</small></h2>
          <div class="rel" id="related"></div>
        </section>

        <div class="row" style="padding:4px 0 24px"><span class="spacer"></span><button class="btn btn-d" id="b-del">Удалить статью</button></div>
      </div>

      <aside class="ecol-side">
        <section class="card">
          <h2>Публикация</h2>
          <div class="grid">
            <label class="f">Статус
              <select id="f-status"><option value="draft">Черновик</option><option value="scheduled">Запланировано</option></select>
            </label>
            <label class="f">Дата выхода <span class="hint">(Алматы)</span><input type="datetime-local" id="f-publish_at"></label>
          </div>
          <p class="ai-status" id="pub-note" style="margin:12px 0 0"></p>
        </section>

        <section class="card">
          <h2>Обложка</h2>
          <div class="cover-box" id="cover-box">
            <img class="cover-prev hidden" id="cover-prev" alt="">
            <div class="cover-empty" id="cover-empty">Обложки нет</div>
          </div>
          <input type="text" id="img-idea" placeholder="Идея картинки (необязательно)" style="margin-top:10px">
          <select id="img-mode" style="margin-top:8px" title="Сюжет картинки"><option value="auto">Сюжет: авто (иногда с людьми)</option><option value="people">Сюжет: с людьми</option><option value="abstract">Сюжет: абстракция, без людей</option></select>
          <div class="row" style="margin-top:8px">
            <button class="btn btn-p" type="button" id="b-cover-ai">Сгенерировать (ИИ)</button>
            <label class="btn">Загрузить свою<input type="file" id="f-file" accept="image/jpeg,image/png,image/webp" hidden></label>
          </div>
          <details class="more"><summary>Путь к файлу</summary><input type="text" id="f-cover_path" placeholder="/blog/media/…"></details>
        </section>

        <section class="card">
          <h2>SEO-проверка</h2>
          <ul class="checks" id="checks"></ul>
        </section>

        <section class="card">
          <details class="more" open>
            <summary><b>SEO и адрес страницы</b></summary>
            <div class="grid" style="margin-top:12px">
              <label class="f">Адрес: /blog/…/ <span class="hint">— латиница и дефис</span>
                <div class="row"><input type="text" id="f-slug" style="flex:1"><button class="btn" id="b-slug" type="button" title="Из заголовка">↻</button></div>
              </label>
              <label class="f">SEO title (&lt;title&gt;) <span class="cnt" id="c-seo"></span><input type="text" id="f-seo_title" placeholder="пусто — возьмём заголовок"></label>
              <label class="f">Описание для поиска <span class="cnt" id="c-desc"></span><textarea id="f-description" rows="3"></textarea></label>
              <label class="f">Поисковые запросы<input type="text" id="f-keywords" placeholder="через запятую"></label>
              <label class="f">Раздел<input type="text" id="f-category" list="cats" placeholder="Таргет, SEO, Аналитика…"><datalist id="cats"></datalist></label>
              <div class="grid g2">
                <label class="f">Автор<input type="text" id="f-author" placeholder="от агентства"></label>
                <label class="f">Минут чтения<input type="number" id="f-read_min" min="1" placeholder="авто"></label>
              </div>
            </div>
          </details>
        </section>
      </aside>
    </div>
  </div>
</div>
<div class="mbar"><button class="btn btn-p" id="m-save">Сохранить</button><button class="btn btn-go" id="m-now">Опубликовать сейчас</button></div>
<div class="toast hidden" id="toast"></div>

<script>
const $ = id => document.getElementById(id);
const FIELDS = ["title", "slug", "seo_title", "description", "lead", "summary", "category", "body_md", "cover_path", "author", "read_min", "status", "publish_at"];
let articles = [], current = null, filter = "all", dirty = false, pendingIdea = null;

const TR = {а:"a",б:"b",в:"v",г:"g",д:"d",е:"e",ё:"e",ж:"zh",з:"z",и:"i",й:"y",к:"k",л:"l",м:"m",н:"n",о:"o",п:"p",р:"r",с:"s",т:"t",у:"u",ф:"f",х:"h",ц:"ts",ч:"ch",ш:"sh",щ:"sch",ъ:"",ы:"y",ь:"",э:"e",ю:"yu",я:"ya",ә:"a",ғ:"g",қ:"k",ң:"n",ө:"o",ұ:"u",ү:"u",һ:"h",і:"i"};
const slugify = s => [...String(s).toLowerCase()].map(ch => TR[ch] ?? ch).join("").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80).replace(/-$/, "");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const STATE = {draft: ["Черновик", "b-draft"], scheduled: ["Запланирована", "b-scheduled"], live: ["На сайте", "b-live"]};

function toast(msg, err) {
  const t = $("toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : "");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), err ? 9000 : 4000);
}
async function api(path, opts = {}) {
  const r = await fetch(path, {headers: {"Content-Type": "application/json", "X-Admin": "1"}, credentials: "same-origin", ...opts});
  if (r.status === 401) { dirty = false; location.reload(); throw new Error("Сессия закончилась — войдите снова"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ("Ошибка " + r.status));
  return data;
}
// Долгие операции ИИ: создать задачу → запустить → опрашивать, пока не готово.
// Если запуск оборвётся по сети (телефон, туннель), задача всё равно доработает на хостинге.
async function runJob(path, body) {
  const {job} = await api(path, {method: "POST", body: JSON.stringify(body)});
  let done = null;
  api("/admin/api/run", {method: "POST", body: JSON.stringify({job})}).then(d => { done = d; }).catch(() => {});
  const t0 = Date.now();
  while (Date.now() - t0 < 11 * 60 * 1000) {
    await new Promise(r => setTimeout(r, 3000));
    const d = done || await api("/admin/api/job?id=" + job).catch(() => null);
    if (d && d.status === "done") return d.result;
    if (d && d.status === "error") throw new Error(d.error);
  }
  throw new Error("Нет ответа больше 10 минут — попробуйте ещё раз");
}
function busy(btn, on, label) {
  if (on) { btn._t = btn.textContent; btn.disabled = true; if (label) btn.textContent = label; }
  else { btn.disabled = false; btn.textContent = btn._t || btn.textContent; }
}
const fmtDate = iso => iso ? new Date(iso.length === 16 ? iso + ":00+05:00" : iso).toLocaleString("ru-RU", {day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Almaty"}) : "";

// ---------- список
async function load(selectSlug) {
  const d = await api("/admin/api/articles");
  articles = d.articles;
  $("now").textContent = "сейчас в Алматы: " + fmtDate(d.now);
  $("model").textContent = "· " + d.writer_model;
  $("cats").innerHTML = [...new Set(articles.map(a => a.category).filter(Boolean))].map(c => `<option value="${esc(c)}">`).join("");
  renderList();
  if (selectSlug) open(articles.find(a => a.slug === selectSlug) || null);
  else if (selectSlug === null) showHome();
}
function renderList() {
  const items = articles.filter(a => filter === "all" || a.state === filter);
  $("list").innerHTML = items.length ? items.map(a => {
    const [label, cls] = STATE[a.state];
    const th = a.cover_path ? `<img class="th" src="${esc(a.cover_path)}" alt="" loading="lazy">` : `<div class="th none">без обложки</div>`;
    return `<li class="acard" data-slug="${esc(a.slug)}">${th}<div class="b">
      <div class="m"><span class="badge ${cls}">${label}</span>${a.publish_at ? esc(fmtDate(a.publish_at)) : ""}</div>
      <div class="t">${esc(a.title)}</div><span class="edit">Редактировать →</span></div></li>`;
  }).join("") : `<li class="empty">Статей пока нет — предложите темы или напишите статью с ИИ ниже.</li>`;
}
function showHome() {
  current = null; dirty = false;
  document.body.classList.remove("view-edit", "view-settings"); renderList(); window.scrollTo(0, 0);
}
function showEditor() { document.body.classList.remove("view-settings"); document.body.classList.add("view-edit"); window.scrollTo(0, 0); }
$("list").onclick = e => {
  const li = e.target.closest("li[data-slug]"); if (!li) return;
  open(articles.find(a => a.slug === li.dataset.slug));
};
$("filters").onclick = e => {
  const b = e.target.closest("button"); if (!b) return;
  filter = b.dataset.f; [...$("filters").children].forEach(x => x.classList.toggle("on", x === b)); renderList();
};

// ---------- редактор
function open(a) {
  current = a;
  const v = a || {status: "draft"};
  FIELDS.forEach(f => { $("f-" + f).value = v[f] ?? ""; });
  $("f-publish_at").value = (v.publish_at || "").slice(0, 16);
  $("f-keywords").value = (v.keywords || []).join(", ");
  renderFaq(v.faq || []);
  renderRelated(v.related || []);
  $("ed-title").textContent = a ? a.title : "Новая статья";
  const [label, cls] = STATE[a ? a.state : "draft"];
  $("ed-badge").textContent = label; $("ed-badge").className = "badge " + cls;
  $("b-now").textContent = $("m-now").textContent = a && a.state === "live" ? "Сохранить на сайте" : "Опубликовать сейчас";
  $("b-del").classList.toggle("hidden", !a);
  showEditor();
  if (!a) { $("g-topic").value = ""; $("g-keys").value = ""; $("g-notes").value = ""; }
  dirty = false; renderList(); refresh();
}
function collect() {
  const a = {};
  FIELDS.forEach(f => { a[f] = $("f-" + f).value; });
  a.read_min = a.read_min ? Number(a.read_min) : null;
  a.keywords = $("f-keywords").value.split(/[,\n;]+/).map(s => s.trim()).filter(Boolean);
  a.faq = [...$("faq").children].map(r => [r.querySelector(".q").value.trim(), r.querySelector(".a").value.trim()]).filter(([q, x]) => q && x);
  a.related = [...$("related").querySelectorAll("input:checked")].map(i => i.value);
  return a;
}
function fill(a) {
  ["title", "slug", "seo_title", "description", "lead", "summary", "category", "body_md"].forEach(f => { if (a[f] != null) $("f-" + f).value = a[f]; });
  $("f-keywords").value = (a.keywords || []).join(", ");
  renderFaq(a.faq || []);
  renderRelated(a.related || []);
  dirty = true; refresh();
}
function renderFaq(items) {
  $("faq").innerHTML = "";
  items.forEach(([q, a]) => addFaq(q, a));
}
function addFaq(q = "", a = "") {
  const row = document.createElement("div"); row.className = "faq-item";
  row.innerHTML = `<input type="text" class="q" placeholder="Вопрос"><textarea class="a" rows="2" placeholder="Ответ"></textarea><button class="x" type="button" title="Убрать">×</button>`;
  row.querySelector(".q").value = q; row.querySelector(".a").value = a;
  row.querySelector(".x").onclick = () => { row.remove(); dirty = true; refresh(); };
  $("faq").appendChild(row);
}
function renderRelated(sel) {
  const own = current ? current.slug : $("f-slug").value;
  const others = articles.filter(a => a.slug !== own);
  $("related").innerHTML = others.length ? others.map(a => `<label><input type="checkbox" value="${esc(a.slug)}" ${sel.includes(a.slug) ? "checked" : ""}>${esc(a.title)} <span class="badge ${STATE[a.state][1]}">${STATE[a.state][0]}</span></label>`).join("")
    : `<span class="empty" style="padding:0">Других статей пока нет. Если ничего не отметить, на странице покажутся свежие статьи.</span>`;
}

// ---------- счётчики и SEO-проверка
function counter(el, text, min, max) {
  const n = text.length; el.textContent = n + (max ? ` / ${min}–${max}` : "");
  el.className = "cnt" + (max ? (n >= min && n <= max ? " ok" : n ? " bad" : "") : "");
}
function refresh() {
  const a = collect();
  counter($("c-title"), a.title, 0, 0);
  counter($("c-seo"), a.seo_title || a.title, 30, 60);
  counter($("c-desc"), a.description, 140, 160);
  const body = a.body_md, lower = (s) => s.toLowerCase();
  const words = (body.match(/[\p{L}\d]+/gu) || []).length;
  const h2 = (body.match(/^##\s+/gm) || []).length;
  const links = (body.match(/\]\(\/[^)]*\)/g) || []).length;
  const main = (a.keywords[0] || "").toLowerCase();
  const title = a.seo_title || a.title;
  const firstPara = (body.split(/\n\s*\n/).find(p => p.trim() && !p.trim().startsWith("#")) || "");
  const checks = [
    [title.length >= 30 && title.length <= 60 ? "ok" : "warn", `Title ${title.length} симв. (лучше 30–60)`],
    [a.description.length >= 140 && a.description.length <= 160 ? "ok" : (a.description ? "warn" : "bad"), `Description ${a.description.length} симв. (лучше 140–160)`],
    [main ? "ok" : "warn", main ? `Главный запрос: «${main}»` : "Не указан главный поисковый запрос"],
    ...(main ? [
      [lower(title).includes(main) ? "ok" : "warn", "Главный запрос в title"],
      [lower(firstPara).includes(main) ? "ok" : "warn", "Главный запрос в первом абзаце"],
    ] : []),
    [words >= 800 ? "ok" : words ? "warn" : "bad", `Объём: ${words} слов (лучше от 800)`],
    [h2 >= 4 ? "ok" : "warn", `Разделов ##: ${h2} (лучше от 4)`],
    [links >= 2 ? "ok" : "warn", `Внутренних ссылок: ${links} (лучше 2–4)`],
    [a.faq.length >= 3 ? "ok" : "warn", `FAQ: ${a.faq.length} вопр.`],
    [a.summary ? "ok" : "warn", "Блок «Коротко» заполнен"],
    [/^[a-z0-9]+(-[a-z0-9]+)*$/.test(a.slug) ? "ok" : "bad", "Адрес корректный"],
  ];
  $("checks").innerHTML = checks.map(([c, t]) => `<li class="${c}">${esc(t)}</li>`).join("");
  const note = $("pub-note");
  if (a.status === "draft") note.textContent = "Черновик на сайт не попадает.";
  else if (!a.publish_at) note.textContent = "Укажите дату выхода — или нажмите «Опубликовать сейчас» внизу.";
  else {
    const due = new Date(a.publish_at + ":00+05:00") <= new Date();
    note.textContent = due ? "Дата наступила — после «Сохранить» статья сразу на сайте; правки опубликованной статьи видны сразу после сохранения."
      : `Появится на сайте сама ${fmtDate(a.publish_at)} — ничего нажимать не нужно, кроме «Сохранить».`;
  }
  const cp = $("f-cover_path").value, img = $("cover-prev");
  img.classList.toggle("hidden", !cp); if (cp) img.src = cp;
  $("cover-empty").classList.toggle("hidden", !!cp);
}
document.querySelector(".editor").addEventListener("input", e => {
  if (e.target.closest(".ai")) return;
  dirty = true;
  if (e.target.id === "f-title" && !current && !$("f-slug").dataset.touched) $("f-slug").value = slugify(e.target.value);
  if (e.target.id === "f-slug") $("f-slug").dataset.touched = "1";
  refresh();
});
document.querySelector(".editor").addEventListener("change", () => refresh());
$("b-slug").onclick = () => { $("f-slug").value = slugify($("f-title").value); dirty = true; refresh(); };
$("b-faq").onclick = () => { addFaq(); dirty = true; };
$("b-new").onclick = () => { if (dirty && !confirm("Есть несохранённые изменения. Начать новую статью?")) return; delete $("f-slug").dataset.touched; open(null); };
window.addEventListener("beforeunload", e => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

// ---------- действия
async function save() {
  const a = collect();
  if (a.status === "scheduled" && a.publish_at) a.publish_at = a.publish_at.slice(0, 16);
  const d = await api("/admin/api/articles", {method: "POST", body: JSON.stringify({article: a, old_slug: current ? current.slug : null})});
  dirty = false;
  await load(d.article.slug);
  return d.article;
}
async function onSave(b) {
  busy(b, true, "Сохраняю…");
  try {
    const a = await save();
    toast(a.state === "scheduled" ? `Сохранено · выйдет сама ${fmtDate(a.publish_at)}`
      : a.state === "live" ? `Сохранено · на сайте: alfimov.kz${a.path}` : "Сохранено · черновик, на сайте не виден");
  } catch (e) { toast(e.message, true); }
  busy(b, false);
}
$("b-save").onclick = () => onSave($("b-save"));
$("m-save").onclick = () => onSave($("m-save"));
// Одной кнопкой: статус «Запланировано» + дата «сейчас» → сохранить (статья сразу на сайте).
const almatyNow = () => new Date(Date.now() - 60000).toLocaleString("sv-SE", {timeZone: "Asia/Almaty"}).slice(0, 16).replace(" ", "T");
async function onNow(b) {
  const title = $("f-title").value.trim() || "без заголовка";
  const isLive = current && current.state === "live";
  if (!confirm(isLive ? `Сохранить правки статьи «${title}» на сайте?` : `Опубликовать статью «${title}» на alfimov.kz прямо сейчас?`)) return;
  busy(b, true, "Публикую…");
  try {
    if (!isLive) { $("f-status").value = "scheduled"; $("f-publish_at").value = almatyNow(); }
    dirty = true;
    const a = await save();
    toast(`Опубликовано: alfimov.kz${a.path}`);
  } catch (e) { toast(e.message, true); }
  busy(b, false);
}
$("b-now").onclick = () => onNow($("b-now"));
$("m-now").onclick = () => onNow($("m-now"));
$("b-back").onclick = () => {
  if (dirty && !confirm("Есть несохранённые изменения. Выйти без сохранения?")) return;
  showHome();
};
$("b-preview").onclick = async () => {
  const w = window.open("about:blank", "_blank");
  try { const a = dirty || !current ? await save() : current; w.location = "/admin/preview/" + a.slug + "/"; }
  catch (e) { w.close(); toast(e.message, true); }
};
$("b-del").onclick = async () => {
  if (!current || !confirm(`Удалить статью «${current.title}»? Если она на сайте — сразу пропадёт оттуда. Отменить нельзя.`)) return;
  try { await api("/admin/api/articles/" + current.slug, {method: "DELETE"}); dirty = false; await load(null); toast("Удалено"); }
  catch (e) { toast(e.message, true); }
};
$("b-gen").onclick = async () => {
  const topic = $("g-topic").value.trim();
  if (!topic) { toast("Впишите тему статьи", true); $("g-topic").focus(); return; }
  // ИИ всегда пишет НОВУЮ статью: сохранённую (тем более опубликованную) он не перезаписывает.
  if (current) {
    if (dirty && !confirm(`В редакторе открыта статья «${current.title}» с несохранёнными правками. Они пропадут, а ИИ напишет новую статью. Продолжить?`)) return;
    const ai = {topic: $("g-topic").value, keys: $("g-keys").value, notes: $("g-notes").value};
    delete $("f-slug").dataset.touched; open(null);  // open(null) очищает поля ИИ — возвращаем их
    $("g-topic").value = ai.topic; $("g-keys").value = ai.keys; $("g-notes").value = ai.notes;
  }
  const b = $("b-gen"); busy(b, true, "Пишу…");
  const t0 = Date.now(), tick = setInterval(() => { $("g-status").textContent = `Claude пишет статью… ${Math.round((Date.now() - t0) / 1000)} с (обычно 1–3 мин)`; }, 1000);
  try {
    const d = await runJob("/admin/api/generate", {topic, keywords: $("g-keys").value, notes: $("g-notes").value, words: $("g-words").value});
    if (!current) open(null);
    fill(d.article);
    showEditor();
    if (pendingIdea && pendingIdea.topic === topic && pendingIdea.date) {
      $("f-status").value = "scheduled"; $("f-publish_at").value = pendingIdea.date; refresh();
      $("g-status").textContent = `Готово — новая статья, запланирована на ${fmtDate(pendingIdea.date)}. Проверьте текст и нажмите «Сохранить» — выйдет сама.`;
    } else $("g-status").textContent = "Готово — это новая статья. Проверьте текст и нажмите «Сохранить»: она сохранится черновиком.";
    pendingIdea = null;
  } catch (e) { $("g-status").textContent = ""; toast(e.message, true); }
  clearInterval(tick); busy(b, false);
};
$("f-file").onchange = async e => {
  const file = e.target.files[0]; if (!file) return;
  const data = await new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result.split(",")[1]); r.readAsDataURL(file); });
  if (file.size > 20 * 1024 * 1024) { toast("Файл больше 20 МБ", true); e.target.value = ""; return; }
  toast("Загружаю…");
  try { const d = await api("/admin/api/upload", {method: "POST", body: JSON.stringify({filename: file.name, data})}); $("f-cover_path").value = d.path; dirty = true; refresh(); toast("Обложка загружена — не забудьте сохранить статью"); }
  catch (err) { toast(err.message, true); }
  e.target.value = "";
};
async function aiImage(kind, idea, btn, label) {
  busy(btn, true, label);
  const t0 = Date.now(), tick = setInterval(() => { btn.textContent = `${label} ${Math.round((Date.now() - t0) / 1000)} с`; }, 1000);
  try {
    return (await runJob("/admin/api/image", {
      kind, idea, mode: $("img-mode").value, title: $("f-title").value, lead: $("f-lead").value, slug: $("f-slug").value})).path;
  } catch (e) { toast(e.message, true); return null; }
  finally { clearInterval(tick); busy(btn, false); }
}
$("b-cover-ai").onclick = async () => {
  const path = await aiImage("cover", $("img-idea").value, $("b-cover-ai"), "Рисую обложку…");
  if (path) { $("f-cover_path").value = path; dirty = true; refresh(); toast("Обложка готова — не забудьте сохранить статью"); }
};
$("b-inline-img").onclick = async () => {
  const ta = $("f-body_md"), pos = ta.selectionStart ?? ta.value.length;
  const idea = prompt("Что должно быть на картинке? Это же станет подписью под ней.");
  if (!idea || !idea.trim()) return;
  const path = await aiImage("inline", idea.trim(), $("b-inline-img"), "Рисую…");
  if (!path) return;
  const md = `\n\n![${idea.trim().replace(/[\[\]]/g, "")}](${path})\n\n`;
  ta.value = ta.value.slice(0, pos) + md + ta.value.slice(pos);
  dirty = true; refresh(); toast("Иллюстрация вставлена в текст");
};
const SERVICE_NAMES = {"target-facebook-instagram": "Таргет Instagram/Facebook", "target-tiktok": "Таргет TikTok", "smm": "SMM",
  "kontekstnaya-reklama": "Контекст", "seo-prodvizhenie": "SEO", "marketingovye-issledovaniya": "Исследования", "kompleksnyj-marketing": "Комплексный"};
function renderIdeas(d) {
  const ideas = (d && d.ideas) || [];
  $("ideas").innerHTML = ideas.map((i, n) => `<li class="idea${i.used ? " used" : ""}">
    <div><b>${esc(i.topic)}</b>
      <div class="hint">${i.used ? "✓ по этой теме уже есть статья" : "📅 рекомендуемая дата выхода: <b style=\"display:inline\">" + esc(fmtDate(i.suggested_date)) + "</b>"}</div>
      <div class="hint">🔑 ${esc(i.main_keyword)} · ${esc(i.intent)}${i.service ? " · → " + esc(SERVICE_NAMES[i.service] || i.service) : ""}</div>
      <div class="hint">${esc(i.why)}</div>
      <div class="hint">Запросы: ${esc(i.keywords.join(", "))}</div></div>
    <button class="btn" data-idea="${n}">Написать статью</button></li>`).join("");
  $("ideas")._data = ideas;
  if (d && d.created) $("i-status").textContent = `${ideas.length} тем из ${d.queries} запросов · ${d.created}`;
}
$("ideas").onclick = e => {
  const b = e.target.closest("[data-idea]"); if (!b) return;
  const i = $("ideas")._data[+b.dataset.idea];
  pendingIdea = {topic: i.topic, date: i.suggested_date};
  $("g-topic").value = i.topic;
  $("g-keys").value = [i.main_keyword, ...i.keywords.filter(k => k !== i.main_keyword)].join("\n");
  $("g-topic").scrollIntoView({behavior: "smooth", block: "center"});
  toast("Тема подставлена — нажмите «Сгенерировать черновик». Дата выхода подставится сама.");
};
$("b-ideas").onclick = async () => {
  const b = $("b-ideas"); busy(b, true, "Собираю запросы…");
  const t0 = Date.now(), tick = setInterval(() => { $("i-status").textContent = `Собираю подсказки и думаю… ${Math.round((Date.now() - t0) / 1000)} с (обычно до минуты)`; }, 1000);
  try { renderIdeas(await runJob(ideasUrl(), {focus: $("i-focus").value})); }
  catch (e) { $("i-status").textContent = ""; toast(e.message, true); }
  clearInterval(tick); busy(b, false);
};
const ideasUrl = () => "/admin/api/ideas?per_week=" + $("i-week").value;
try { $("i-week").value = localStorage.getItem("per_week") || "2"; } catch (e) {}
$("i-week").onchange = () => { try { localStorage.setItem("per_week", $("i-week").value); } catch (e) {} api(ideasUrl()).then(renderIdeas).catch(() => {}); };
api(ideasUrl()).then(renderIdeas).catch(() => {});
// ---------- настройки и выход
async function showSettings() {
  if (dirty && !confirm("Есть несохранённые изменения. Уйти без сохранения?")) return;
  dirty = false;
  document.body.classList.remove("view-edit"); document.body.classList.add("view-settings"); window.scrollTo(0, 0);
  try {
    const s = await api("/admin/api/settings");
    $("s-ant-cur").textContent = s.anthropic_key ? `— сейчас ${s.anthropic_key}` : "— не задан";
    $("s-oai-cur").textContent = s.openai_key ? `— сейчас ${s.openai_key}` : "— не задан";
    $("s-login").textContent = "логин: " + s.login;
  } catch (e) { toast(e.message, true); }
}
$("b-settings").onclick = showSettings;
$("keys-link").onclick = e => { e.preventDefault(); showSettings(); };
$("s-back").onclick = () => { document.body.classList.remove("view-settings"); checkKeys(); };
$("s-save").onclick = async () => {
  const b = $("s-save"); busy(b, true, "Сохраняю…");
  try {
    const d = await api("/admin/api/settings", {method: "POST", body: JSON.stringify({
      anthropic_key: $("s-ant").value, openai_key: $("s-oai").value,
      password_current: $("s-pass-cur").value, password_new: $("s-pass-new").value})});
    ["s-ant", "s-oai", "s-pass-cur", "s-pass-new"].forEach(id => { $(id).value = ""; });
    toast(d.changed.length ? "Сохранено: " + d.changed.join(", ") : "Ничего не изменилось");
    await showSettings();
  } catch (e) { toast(e.message, true); }
  busy(b, false);
};
$("b-logout").onclick = async () => {
  if (dirty && !confirm("Есть несохранённые изменения. Выйти?")) return;
  dirty = false;
  await api("/admin/api/logout", {method: "POST"}).catch(() => {});
  location.reload();
};
async function checkKeys() {
  try { const s = await api("/admin/api/settings"); $("keys-warn").classList.toggle("hidden", !!(s.anthropic_key && s.openai_key)); } catch (e) {}
}
checkKeys();

load(null).catch(e => toast(e.message, true));
</script>
</body>
</html>
