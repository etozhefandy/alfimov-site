/*
  Geo-персонализация на стороне браузера.
  ВАЖНО: это НЕ дорвей. Исходный HTML, который видит поисковый робот, уже содержит
  честный общий текст ("работаем по всему Казахстану") — он одинаков для всех.
  Этот скрипт только ДОПОЛНЯЕТ текст именем города ПОСЛЕ загрузки страницы,
  и делает это одинаково для любого посетителя (бот тоже может это увидеть,
  если выполняет JS) — контент не подменяется избирательно по user-agent или IP.
*/
(function () {
  "use strict";

  var CITY_NAMES = {
    "almaty": "Алматы",
    "astana": "Астане",
    "nur-sultan": "Астане",
    "shymkent": "Шымкенте",
    "karaganda": "Караганде",
    "qaraghandy": "Караганде",
    "aktobe": "Актобе",
    "taraz": "Таразе",
    "pavlodar": "Павлодаре",
    "ust-kamenogorsk": "Усть-Каменогорске",
    "oskemen": "Усть-Каменогорске",
    "semey": "Семее",
    "semipalatinsk": "Семее",
    "atyrau": "Атырау",
    "kostanay": "Костанае",
    "kyzylorda": "Кызылорде",
    "uralsk": "Уральске",
    "oral": "Уральске",
    "petropavl": "Петропавловске",
    "petropavlovsk": "Петропавловске",
    "aktau": "Актау",
    "turkistan": "Туркестане",
    "kokshetau": "Кокшетау",
    "taldykorgan": "Талдыкоргане",
    "zhezkazgan": "Жезказгане"
  };

  function setCityText(cityPhrase) {
    var nodes = document.querySelectorAll("[data-geo-city]");
    for (var i = 0; i < nodes.length; i++) {
      var tpl = nodes[i].getAttribute("data-geo-template");
      if (tpl) {
        nodes[i].textContent = tpl.replace("{city}", cityPhrase);
      } else {
        nodes[i].textContent = cityPhrase;
      }
      nodes[i].classList.add("geo-filled");
    }
  }

  function normalize(str) {
    return (str || "").toLowerCase().trim().replace(/\s+/g, "-");
  }

  // Бесплатный сервис определения города по IP, без ключа, с CORS.
  var GEO_ENDPOINT = "https://get.geojs.io/v1/ip/geo.json";
  var TIMEOUT_MS = 2500;

  function run() {
    if (!window.fetch) return;

    var controller = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) controller.abort();
    }, TIMEOUT_MS);

    fetch(GEO_ENDPOINT, { signal: controller ? controller.signal : undefined })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        clearTimeout(timer);
        if (!data || !data.country_code) return;
        if (data.country_code !== "KZ") return; // за пределами Казахстана — оставляем общий текст

        var key = normalize(data.city);
        var ru = CITY_NAMES[key];
        if (ru) {
          setCityText(ru);
        }
      })
      .catch(function () {
        clearTimeout(timer);
        // тихо оставляем общий (дефолтный) текст — ничего не ломаем
      });
  }

  if (document.readyState === "complete" || document.readyState === "interactive") {
    run();
  } else {
    document.addEventListener("DOMContentLoaded", run);
  }
})();
