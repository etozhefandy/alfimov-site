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

  // Форма заявки → /api/send.php → Telegram
  document.querySelectorAll("form.form").forEach(function (form) {
    var ts = form.querySelector('input[name="ts"]');
    if (ts) ts.value = String(Date.now());
    var status = form.querySelector(".form-status");
    var btn = form.querySelector('button[type="submit"]');
    var btnHtml = btn.innerHTML;

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
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
