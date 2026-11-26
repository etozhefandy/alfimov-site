document.addEventListener("DOMContentLoaded", function () {
  var burger = document.querySelector(".burger");
  var nav = document.querySelector(".nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }

  var form = document.querySelector("#contact-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = form.querySelector("#f-name").value.trim();
      var phone = form.querySelector("#f-phone").value.trim();
      var msg = form.querySelector("#f-msg").value.trim();
      var text = "Заявка с сайта kalymbekov.kz%0AИмя: " + encodeURIComponent(name) +
        "%0AТелефон: " + encodeURIComponent(phone) +
        "%0AВопрос: " + encodeURIComponent(msg || "-");
      var waNumber = "77072345680"; // WhatsApp Данияра
      window.open("https://wa.me/" + waNumber + "?text=" + text, "_blank");
    });
  }

  // Тень у шапки при прокрутке страницы вниз
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      if (window.scrollY > 10) header.classList.add("scrolled");
      else header.classList.remove("scrolled");
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Плавное появление блоков при прокрутке (не включаем для тех,
  // кто попросил в системе свести анимации к минимуму)
  var prefersReduced = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!prefersReduced && "IntersectionObserver" in window) {
    var targets = document.querySelectorAll(
      ".card, .fact, .steps li, .price-box, .hero-card, .faq-item, h2.sec-title, .cta-band .wrap > *"
    );

    // Лёгкая задержка по очереди для элементов внутри одного блока —
    // карточки/факты "выезжают" друг за другом, а не все разом.
    var parents = [];
    targets.forEach(function (el) {
      el.classList.add("reveal");
      if (parents.indexOf(el.parentElement) === -1) parents.push(el.parentElement);
    });
    parents.forEach(function (parent) {
      var siblings = Array.prototype.filter.call(parent.children, function (c) {
        return c.classList.contains("reveal");
      });
      siblings.forEach(function (child, i) {
        child.style.transitionDelay = Math.min(i * 0.08, 0.4) + "s";
      });
    });

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    targets.forEach(function (el) {
      io.observe(el);
    });
  }
});
