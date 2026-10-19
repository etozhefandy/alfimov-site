// Рекламные страницы Guestory: опрос → /api/lp-send.php (Telegram), кнопки WhatsApp, пиксель Meta.
(function () {
  // ---- настройки заказчика
  var PIXEL_ID = '1460843041888688'; // ID пикселя Guestory из Events Manager; пусто — пиксель не грузится
  var WA_PHONE = '77088884521';      // WhatsApp менеджера Guestory
  var CLIENT = 'guestory';

  var page = document.body.getAttribute('data-page') || '';

  // ---- метки рекламы: запоминаем на время визита (человек мог уйти со страницы и вернуться)
  var utm = {};
  var keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid'];
  var qs = new URLSearchParams(location.search);
  keys.forEach(function (k) {
    var v = qs.get(k);
    try { if (v) sessionStorage.setItem('lp_' + k, v); else v = sessionStorage.getItem('lp_' + k); } catch (e) {}
    if (v) utm[k] = v;
  });

  // ---- пиксель Meta
  if (PIXEL_ID) {
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = []; t = b.createElement(e); t.async = !0;
      t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', PIXEL_ID);
    fbq('track', 'PageView');
  }
  function track(name, params, id) {
    if (window.fbq) fbq('track', name, params || {}, id ? { eventID: id } : undefined);
  }

  // ---- WhatsApp: готовый текст по странице, событие Contact
  document.querySelectorAll('[data-wa]').forEach(function (a) {
    a.href = 'https://wa.me/' + WA_PHONE + '?text=' + encodeURIComponent(a.getAttribute('data-wa'));
    a.target = '_blank';
    a.rel = 'noopener';
    a.addEventListener('click', function () { track('Contact', { content_name: page }); });
  });

  // ---- опрос
  var form = document.getElementById('quiz');
  if (!form) return;
  var steps = Array.prototype.slice.call(form.querySelectorAll('.quiz-step'));
  var bar = form.querySelector('.quiz-bar i');
  var err = form.querySelector('.quiz-err');
  var back = form.querySelector('.back');
  var next = form.querySelector('.next');
  var submit = form.querySelector('.submit');
  var submitText = submit.textContent;
  var cur = 0, started = false, sending = false;
  form.querySelector('[name=ts]').value = Date.now();

  // Ветки: первый вопрос (тип объекта) задаёт ветку, шаги с data-when показываются только своей ветке.
  function branch() {
    var b = form.querySelector('input[data-branch]:checked');
    if (b) return b.getAttribute('data-branch');
    var first = form.querySelector('input[data-branch]');
    return first ? first.getAttribute('data-branch') : '';   // до выбора — считаем шаги по первой ветке
  }
  function path() {
    var b = branch();
    return steps.filter(function (s) {
      var w = s.getAttribute('data-when');
      return !w || w.split(' ').indexOf(b) >= 0;
    });
  }

  function show(step) {
    var p = path(), i = p.indexOf(step);
    cur = step;
    steps.forEach(function (s) { s.classList.toggle('on', s === step); });
    bar.style.width = Math.round(((i + 1) / p.length) * 100) + '%';
    var last = i === p.length - 1, kind = step.getAttribute('data-kind');
    var hint = step.querySelector('.quiz-hint');
    hint.textContent = 'Шаг ' + (i + 1) + ' из ' + p.length
      + (kind === 'multi' ? ' · можно несколько' : '')
      + (hint.getAttribute('data-extra') ? ' · ' + hint.getAttribute('data-extra') : '');
    back.style.visibility = i ? 'visible' : 'hidden';
    next.hidden = last || kind !== 'multi';
    submit.hidden = !last;
    err.textContent = '';
  }
  function go(d) { var p = path(); show(p[p.indexOf(cur) + d]); }
  function answered(step) { return !!step.querySelector('input:checked'); }

  form.addEventListener('change', function (e) {
    if (!started) { started = true; track('InitiateCheckout', { content_name: page }); }
    var t = e.target;
    if (t.type === 'checkbox' && t.value === 'Другое') {   // «Другое» — открыть строку «Что именно?»
      var other = cur.querySelector('.other');
      if (other) { other.hidden = !t.checked; if (t.checked) other.querySelector('input').focus(); }
    }
    if (t.type === 'radio' && cur.contains(t) && path().indexOf(cur) < path().length - 1) {
      setTimeout(function () { go(1); }, 180);
    }
  });
  next.addEventListener('click', function () {
    if (!answered(cur)) { err.textContent = 'Отметьте хотя бы один вариант'; return; }
    go(1);
  });
  back.addEventListener('click', function () { if (path().indexOf(cur) > 0) go(-1); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (sending) return;
    var name = form.elements.name.value.trim();
    var phone = form.elements.phone.value.trim();
    if (!name) { err.textContent = 'Как к вам обращаться?'; return; }
    if (phone.replace(/\D/g, '').length < 10) { err.textContent = 'Проверьте номер телефона'; return; }
    // ответы из чужих веток (человек сменил тип объекта) и скрытое «Что именно?» не отправляем
    var p = path();
    steps.forEach(function (s) {
      var off = p.indexOf(s) < 0;
      s.querySelectorAll('input').forEach(function (inp) { inp.disabled = off || (inp.name === 'comment' && inp.closest('.other').hidden); });
    });
    var fd = new FormData(form);
    form.querySelectorAll('.quiz-step input').forEach(function (inp) { inp.disabled = false; });
    // один id заявки для пикселя в браузере и для сервера (Conversions API) — Meta склеит их в одно событие
    var leadId = 'lead-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    fd.append('event_id', leadId);
    fd.append('client', CLIENT);
    fd.append('page', page);
    Object.keys(utm).forEach(function (k) { fd.append(k, utm[k]); });
    sending = true;
    submit.disabled = true;
    submit.textContent = 'Отправляем…';
    fetch('/api/lp-send.php', { method: 'POST', body: fd })
      .then(function (r) { return r.json().then(function (j) { return [r.status, j]; }); })
      .then(function (res) {
        if (res[1].ok) {
          track('Lead', { content_name: page }, leadId);
          form.innerHTML = document.getElementById('quiz-done').innerHTML;
          form.scrollIntoView({ behavior: 'smooth', block: 'center' });
          document.querySelectorAll('#quiz [data-wa]').forEach(function (a) {
            a.href = 'https://wa.me/' + WA_PHONE + '?text=' + encodeURIComponent(a.getAttribute('data-wa'));
            a.target = '_blank';
          });
          return;
        }
        throw new Error(res[0] === 422 ? 'phone' : 'send');
      })
      .catch(function (ex) {
        sending = false;
        submit.disabled = false;
        submit.textContent = submitText;
        err.textContent = ex.message === 'phone'
          ? 'Проверьте номер телефона — например, 8 701 234 56 78'
          : 'Не получилось отправить. Напишите нам в WhatsApp — кнопка ниже.';
      });
  });

  show(steps[0]);
})();
