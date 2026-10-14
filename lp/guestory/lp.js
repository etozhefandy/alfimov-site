// Рекламные страницы Guestory: опрос → /api/lp-send.php (Telegram), кнопки WhatsApp, пиксель Meta.
(function () {
  // ---- настройки заказчика
  var PIXEL_ID = '';                 // ID пикселя Guestory из Events Manager; пусто — пиксель не грузится
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
  var cur = 0, started = false, sending = false;
  form.querySelector('[name=ts]').value = Date.now();

  function show(i) {
    cur = i;
    steps.forEach(function (s, j) { s.classList.toggle('on', j === i); });
    bar.style.width = Math.round(((i + 1) / steps.length) * 100) + '%';
    var last = i === steps.length - 1, multi = steps[i].getAttribute('data-kind') === 'multi';
    back.style.visibility = i ? 'visible' : 'hidden';
    next.hidden = last || !multi;
    submit.hidden = !last;
    err.textContent = '';
  }
  function answered(i) { return !!steps[i].querySelector('input:checked'); }

  form.addEventListener('change', function (e) {
    if (!started) { started = true; track('InitiateCheckout', { content_name: page }); }
    var step = steps[cur];
    if (e.target.type === 'radio' && step.contains(e.target) && cur < steps.length - 1) {
      setTimeout(function () { show(cur + 1); }, 180);
    }
  });
  next.addEventListener('click', function () {
    if (!answered(cur)) { err.textContent = 'Отметьте хотя бы один вариант'; return; }
    show(cur + 1);
  });
  back.addEventListener('click', function () { if (cur) show(cur - 1); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (sending) return;
    var name = form.elements.name.value.trim();
    var phone = form.elements.phone.value.trim();
    if (!name) { err.textContent = 'Как к вам обращаться?'; return; }
    if (phone.replace(/\D/g, '').length < 10) { err.textContent = 'Проверьте номер телефона'; return; }
    var fd = new FormData(form);
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
          track('Lead', { content_name: page }, 'lead-' + Date.now());
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
        submit.textContent = 'Получить предложение';
        err.textContent = ex.message === 'phone'
          ? 'Проверьте номер телефона — например, 8 701 234 56 78'
          : 'Не получилось отправить. Напишите нам в WhatsApp — кнопка ниже.';
      });
  });

  show(0);
})();
