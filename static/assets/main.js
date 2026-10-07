(function () {
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

  // Появление блоков при прокрутке (CSS-переходы, без тяжёлых библиотек)
  var items = document.querySelectorAll(".rv");
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
  document.querySelectorAll("input[data-phone]").forEach(function (inp) {
    inp.addEventListener("focus", function () { if (!inp.value) inp.value = "+7 ("; });
    inp.addEventListener("blur", function () { if (phoneDigits(inp.value).length <= 1) inp.value = ""; });
    inp.addEventListener("input", function () {
      var raw = inp.value.replace(/\D/g, "");
      // вставили 10 цифр без кода страны (7012345678) — код 7 дописываем, а не принимаем первую 7 за него
      var d = inp.value.indexOf("+") < 0 && raw.length === 10 ? "7" + raw : phoneDigits(inp.value);
      inp.value = d.length > 1 ? phoneFormat(d) : (inp.value ? "+7 (" : "");
      inp.setCustomValidity("");
    });
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
      if (phone && phoneDigits(phone.value).length !== 11) {
        status.className = "form-status err";
        status.textContent = phone.dataset.err;
        phone.focus();
        return;
      }
      btn.disabled = true;
      btn.textContent = form.dataset.sending;
      status.className = "form-status";
      status.textContent = "";

      fetch(form.action, { method: "POST", body: new FormData(form), headers: { Accept: "application/json" } })
        .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
        .then(function (res) {
          if (!res.ok) throw new Error("send failed");
          form.reset();
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
