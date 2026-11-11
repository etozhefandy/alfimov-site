(function () {
  // Шрифты грузятся как media="print" (не блокируют рендер), здесь включаем media="all" — раньше это было
  // inline onload="" на самом <link>, но CSP script-src-attr без unsafe-inline/unsafe-hashes такое блокирует.
  document.querySelectorAll(".js-async-css").forEach(function (l) {
    if (l.sheet) { l.media = "all"; return; }   // уже загружен (из кэша) — JS мог стартовать позже загрузки
    l.addEventListener("load", function () { l.media = "all"; });
  });

  // Мобильное меню
  var burger = document.querySelector(".burger");
  var nav = document.getElementById("nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (ev) {
      if (ev.target.closest("a")) {
        nav.classList.remove("open");
        burger.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Появление блоков при прокрутке (CSS-переходы, без тяжёлых библиотек) — .type тот же механизм, своя анимация в CSS
  var items = document.querySelectorAll(".rv, .type");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add("in"); });
  }


  // Живые детали (style.css «живые детали»). Всё выключается при «уменьшить движение».
  var calm = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia && matchMedia("(hover: hover) and (pointer: fine)").matches;

  // Шапка: полоска прочитанного + прячется при прокрутке вниз, возвращается при прокрутке вверх.
  var hdr = document.querySelector(".hdr");
  var sprog = document.querySelector(".sprog");
  var mcta = document.querySelector(".mcta");
  var leadForm = document.getElementById("lead-form");
  var heroForm = document.getElementById("hero-form");
  var lastY = window.scrollY, ticking = false, formsVisible = {};
  if (mcta && leadForm) {
    mcta.hidden = false;
    mcta.addEventListener("click", function () { if (window.clarity) clarity("event", "mcta_click"); });
    if ("IntersectionObserver" in window) {
      var fio = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { formsVisible[en.target.id] = en.isIntersecting; });
        onScrollFrame();
      });
      [leadForm, heroForm].forEach(function (f) { if (f) fio.observe(f); });
    }
  }
  function onScrollFrame() {
    ticking = false;
    var y = window.scrollY, doc = document.documentElement;
    var max = doc.scrollHeight - window.innerHeight;
    if (sprog) sprog.style.setProperty("--sp", max > 0 ? Math.min(1, y / max).toFixed(4) : 0);
    if (hdr && !calm) {
      var menuOpen = nav && nav.classList.contains("open");
      if (y > lastY + 6 && y > 200 && !menuOpen) hdr.classList.add("hide");
      else if (y < lastY - 6 || y < 200) hdr.classList.remove("hide");
    }
    if (mcta && !mcta.hidden) {
      var anyForm = formsVisible["lead-form"] || formsVisible["hero-form"];
      var pop = document.querySelector(".art-popup.on");
      mcta.classList.toggle("on", y > 500 && !anyForm && !pop);
    }
    lastY = y;
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; requestAnimationFrame(onScrollFrame); }
  }, { passive: true });
  onScrollFrame();
  // Переход по ссылке-якорю (#lead-form и т.п.) не должен прятать шапку поверх формы — это нормально, шапка вернётся при прокрутке вверх.


  // Сменяющееся слово заголовка: data-rot="слово~секунды|…" (build.py type_words). Стартует, когда заголовок допечатался.
  var rot = document.querySelector(".rot[data-rot]");
  if (rot && !calm) {
    var rlist = rot.getAttribute("data-rot").split("|").map(function (x) {
      var p = x.split("~"); return { w: p[0], t: parseFloat(p[1]) || 2.5 };
    });
    if (rlist.length > 1) {
      var rw = document.createElement("span");
      rw.className = "rw"; rw.textContent = rlist[0].w;
      rot.textContent = ""; rot.appendChild(rw);
      var rk = 0;
      var rnext = function () {
        rw.className = "rw out";
        setTimeout(function () {
          rk = (rk + 1) % rlist.length;
          rw.textContent = rlist[rk].w;
          rw.className = "rw"; void rw.offsetWidth; rw.className = "rw new";
          setTimeout(rnext, rlist[rk].t * 1000);
        }, 260);
      };
      setTimeout(rnext, rlist[0].t * 1000 + 1000);
    }
  }

  if (!calm && fine) {
    // Сетка первого экрана слегка следует за мышью.
    var hx = document.querySelector(".hx"), hxBg = document.querySelector(".hx-bg");
    if (hx && hxBg) {
      hx.addEventListener("mousemove", function (ev) {
        var r = hx.getBoundingClientRect();
        hxBg.style.setProperty("--px", ((ev.clientX - r.left) / r.width - .5) * -24 + "px");
        hxBg.style.setProperty("--py", ((ev.clientY - r.top) / r.height - .5) * -24 + "px");
      });
    }
    // Плитки услуг чуть наклоняются за курсором.
    document.querySelectorAll(".bento .tile").forEach(function (t) {
      t.addEventListener("mousemove", function (ev) {
        var r = t.getBoundingClientRect();
        var x = (ev.clientX - r.left) / r.width - .5, y = (ev.clientY - r.top) / r.height - .5;
        t.style.setProperty("--rx", (y * -5).toFixed(2) + "deg");
        t.style.setProperty("--ry", (x * 6).toFixed(2) + "deg");
      });
      t.addEventListener("mouseleave", function () { t.style.removeProperty("--rx"); t.style.removeProperty("--ry"); });
    });
  }

  // Попап под статьёй блога (_blog/popup.php сайта кладёт разметку, здесь — когда её показать).
  // Один раз за вкладку: не чаще, чем за визит, и не раньше, чем человек начал читать.
  (function () {
    var popup = document.querySelector(".art-popup");
    if (!popup) return;
    var mark = function (ev) { if (window.clarity) clarity("event", ev); };
    var shown = false;
    function show() {
      if (shown) return;
      shown = true;
      try { sessionStorage.setItem("popup_seen", "1"); } catch (e) {}
      popup.hidden = false;
      requestAnimationFrame(function () { popup.classList.add("on"); });
      mark("popup_shown");
      window.removeEventListener("scroll", onScroll);
    }
    function onScroll() {
      var doc = document.documentElement;
      var past = (window.scrollY + window.innerHeight) / doc.scrollHeight;
      if (past > 0.5) show();
    }
    var seen = false;
    try { seen = sessionStorage.getItem("popup_seen") === "1"; } catch (e) {}
    if (!seen) {
      window.addEventListener("scroll", onScroll, { passive: true });
      setTimeout(show, 20000);
    }
    popup.querySelector(".art-popup-close").addEventListener("click", function () {
      popup.classList.remove("on");
      mark("popup_close");
    });
    var cta = popup.querySelector("[data-popup-cta]");
    if (cta) cta.addEventListener("click", function () { mark("popup_click"); });
  })();

  // Маска телефона: +7 (7XX) XXX-XX-XX. 8 в начале → 7, вставка «+7 701…» и «8701…» тоже работает.
  function phoneDigits(v) {
    var d = String(v).replace(/\D/g, "");
    if (d.charAt(0) === "8") d = "7" + d.slice(1);
    if (d && d.charAt(0) !== "7") d = "7" + d;
    return d.slice(0, 11);
  }
  // Скобка и дефисы ставятся только когда за ними уже есть цифры — иначе Backspace «упирается» в них.
  function phoneFormat(d) {
    if (!d) return "";
    var r = "+7";
    if (d.length > 1) r += " (" + d.slice(1, 4);
    if (d.length > 4) r += ") " + d.slice(4, 7);
    if (d.length > 7) r += "-" + d.slice(7, 9);
    if (d.length > 9) r += "-" + d.slice(9, 11);
    return r;
  }
  // Простая маска — запасной вариант, пока грузится (или если не загрузилась) intl-tel-input.
  document.querySelectorAll("input[data-phone]").forEach(function (inp) {
    inp.addEventListener("focus", function () { if (!inp._iti && !inp.value) inp.value = "+7 ("; });
    inp.addEventListener("blur", function () { if (!inp._iti && phoneDigits(inp.value).length <= 1) inp.value = ""; });
    inp.addEventListener("input", function () {
      if (inp._iti) return;
      var raw = inp.value.replace(/\D/g, "");
      // вставили 10 цифр без кода страны (7012345678) — код 7 дописываем, а не принимаем первую 7 за него
      var d = inp.value.indexOf("+") < 0 && raw.length === 10 ? "7" + raw : phoneDigits(inp.value);
      inp.value = d.length > 1 ? phoneFormat(d) : (inp.value ? "+7 (" : "");
      inp.setCustomValidity("");
    });
  });

  // +7 — Казахстан и Россия. База Google пропускает зарезервированные, но пустые диапазоны (+7 666…),
  // поэтому сверяем с реальными кодами: KZ мобильные 700–708, 747, 771–778, городские 71x/72x; RU 3xx/4xx/8xx/9xx.
  // Та же проверка — на сервере (api/send.php).
  function kzRuOk(e164) {
    var d = String(e164 || "").replace(/\D/g, "");
    if (d.charAt(0) !== "7") return true;
    return d.length === 11 && /^7(?:70[0-8]|747|77[1-8]|7[12]\d|[3489]\d\d)/.test(d);
  }

  // Телефон: intl-tel-input (github.com/jackocnr/intl-tel-input) — флаг и выбор страны, по умолчанию Казахстан;
  // формат и проверка по базе Google libphonenumber (коды операторов: +7 707, +7 747… — да, +7 666 — нет).
  // Грузим после загрузки страницы, чтобы не тормозить первый показ.
  var ITI = "https://cdn.jsdelivr.net/npm/intl-tel-input@29.5.3/dist/";
  var phones = document.querySelectorAll("input[data-phone]");
  if (phones.length) window.addEventListener("load", function () {
    var css = document.createElement("link");
    css.rel = "stylesheet"; css.href = ITI + "css/intlTelInput.min.css";
    document.head.appendChild(css);
    var js = document.createElement("script");
    js.src = ITI + "js/intlTelInput.min.js";
    js.onload = function () {
      var kk = document.documentElement.lang === "kk";
      phones.forEach(function (inp) {
        var digits = phoneDigits(inp.value);
        inp.value = digits.length > 1 ? "+" + digits : "";
        inp.placeholder = "";
        inp.removeAttribute("maxlength");
        inp._iti = window.intlTelInput(inp, {
          initialCountry: "kz",
          countryOrder: ["kz", "ru", "uz", "kg"],
          separateDialCode: true,
          strictMode: true,
          countryNameLocale: kk ? "kk" : "ru",
          allowedNumberTypes: ["MOBILE", "FIXED_LINE"],
          uiTranslations: { searchPlaceholder: kk ? "Іздеу" : "Поиск", searchEmptyState: kk ? "Ештеңе табылмады" : "Ничего не найдено" },
          loadUtils: function () { return import(ITI + "js/utils.js"); }
        });
      });
    };
    document.head.appendChild(js);
  });

  // Форма заявки → /api/send.php → Telegram
  document.querySelectorAll("form.form").forEach(function (form) {
    var ts = form.querySelector('input[name="ts"]');
    if (ts) ts.value = String(Date.now());
    var status = form.querySelector(".form-status");
    var btn = form.querySelector('button[type="submit"]');
    var btnHtml = btn.innerHTML;

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var phone = form.querySelector("input[data-phone]");
      var iti = phone && phone._iti;
      // isValidNumber() = null, пока не догрузилась база номеров, — тогда проверит сервер
      var bad = phone && (iti ? iti.isValidNumber() === false || !phone.value.trim() || !kzRuOk(iti.getNumber())
                              : phoneDigits(phone.value).length !== 11 || !kzRuOk("+" + phoneDigits(phone.value)));
      if (bad) {
        status.className = "form-status err";
        status.textContent = phone.dataset.err;
        phone.focus();
        return;
      }
      var data = new FormData(form);
      if (iti) data.set("contact", iti.getNumber() || phone.value);
      btn.disabled = true;
      btn.textContent = form.dataset.sending;
      status.className = "form-status";
      status.textContent = "";

      fetch(form.action, { method: "POST", body: data, headers: { Accept: "application/json" } })
        .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
        .then(function (res) {
          if (!res.ok) throw new Error("send failed");
          if (window.clarity) clarity("event", "lead");   // заявка — отметка в Clarity для фильтра записей
          form.reset();
          if (iti) iti.setNumber("");
          if (ts) ts.value = String(Date.now());
          status.className = "form-status ok";
          status.textContent = form.dataset.ok;
        })
        .catch(function () {
          status.className = "form-status err";
          status.textContent = form.dataset.err;
        })
        .finally(function () {
          btn.disabled = false;
          btn.innerHTML = btnHtml;
        });
    });
  });
})();
