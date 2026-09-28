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

  // Форма заявки → /api/send.php → Telegram
  document.querySelectorAll("form.form").forEach(function (form) {
    var ts = form.querySelector('input[name="ts"]');
    if (ts) ts.value = String(Date.now());
    var status = form.querySelector(".form-status");
    var btn = form.querySelector('button[type="submit"]');
    var btnText = btn.textContent;

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
          if (typeof window.ym === "function") try { window.ym(window.YM_ID, "reachGoal", "lead"); } catch (e) {}
          if (typeof window.gtag === "function") try { window.gtag("event", "generate_lead"); } catch (e) {}
        })
        .catch(function () {
          status.className = "form-status err";
          status.textContent = form.dataset.err;
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = btnText;
        });
    });
  });
})();
