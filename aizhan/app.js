var corners = {
  TR: 'M900,1750 V90 C900,20 1000,-10 1150,-40 L2250,-360',
  TL: 'M100,1750 V90 C100,20 0,-10 -150,-40 L-1250,-360',
  BR: 'M900,-1150 V510 C900,580 1000,610 1150,640 L2250,960',
  BL: 'M100,-1150 V510 C100,580 0,610 -150,640 L-1250,960'
};
var keys = Object.keys(corners);
function pick(){ return keys[Math.floor(Math.random()*keys.length)]; }
function pickOtherThan(prev){
  var next = pick();
  while (next === prev) { next = pick(); }
  return next;
}
var a = pick();
var b = pickOtherThan(a);
document.getElementById('flowPathA').setAttribute('d', corners[a]);
document.getElementById('flowPathB').setAttribute('d', corners[b]);

function scheduleReroll(durSeconds, beginOffsetSeconds, rerollFn) {
  var firstDelay = (durSeconds - beginOffsetSeconds) * 1000;
  setTimeout(function loop() {
    rerollFn();
    setTimeout(loop, durSeconds * 1000);
  }, firstDelay);
}
scheduleReroll(22, 8, function () {
  a = pickOtherThan(a);
  document.getElementById('flowPathA').setAttribute('d', corners[a]);
});
scheduleReroll(20, 7, function () {
  b = pickOtherThan(b);
  document.getElementById('flowPathB').setAttribute('d', corners[b]);
});

function fitWordmark() {
  var h1 = document.getElementById('wordmark');
  var container = document.querySelector('.hero-title');
  if (!h1 || !container) return;
  var cs = window.getComputedStyle(h1);
  var containerCs = window.getComputedStyle(container);
  var fontSize = parseFloat(cs.fontSize);
  var fontWeight = cs.fontWeight;
  var fontFamily = cs.fontFamily;
  var letterSpacing = parseFloat(cs.letterSpacing) || 0;
  var padLeft = parseFloat(containerCs.paddingLeft) || 0;
  var padRight = parseFloat(containerCs.paddingRight) || 0;
  var availWidth = container.clientWidth - padLeft - padRight;
  var canvas = fitWordmark._canvas || (fitWordmark._canvas = document.createElement('canvas'));
  var ctx = canvas.getContext('2d');
  ctx.font = fontWeight + ' ' + fontSize + 'px ' + fontFamily;
  function measure(text) {
    return ctx.measureText(text).width + letterSpacing * (text.length - 1);
  }
  var n = 1;
  var text = 'АЙЖ' + 'А'.repeat(n) + 'Н';
  while (measure(text) < availWidth && n < 60) {
    n++;
    text = 'АЙЖ' + 'А'.repeat(n) + 'Н';
  }
  if (measure(text) > availWidth && n > 1) {
    n--;
    text = 'АЙЖ' + 'А'.repeat(n) + 'Н';
  }
  h1.textContent = text;
}
fitWordmark();
if (document.fonts && document.fonts.ready) { document.fonts.ready.then(fitWordmark); }
var resizeTimer;
window.addEventListener('resize', function () {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(fitWordmark, 100);
});

var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

var revealEls = document.querySelectorAll('.reveal');
if (!reduceMotion && 'IntersectionObserver' in window && revealEls.length) {
  var revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  revealEls.forEach(function (el) { revealObserver.observe(el); });
} else {
  revealEls.forEach(function (el) { el.classList.add('is-visible'); });
}

function formatThousands(n) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}
function animateCount(el) {
  var text = el.textContent;
  var match = text.match(/[\d\s]+/);
  if (!match) return;
  var raw = match[0];
  var target = parseInt(raw.replace(/\s/g, ''), 10);
  if (isNaN(target)) return;
  var prefix = text.slice(0, match.index);
  var suffix = text.slice(match.index + raw.length);
  var duration = 1200;
  var startTime = null;
  function step(ts) {
    if (!startTime) startTime = ts;
    var p = Math.min((ts - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + formatThousands(Math.round(eased * target)) + suffix;
    if (p < 1) { requestAnimationFrame(step); } else { el.textContent = text; }
  }
  requestAnimationFrame(step);
}
var statNums = document.querySelectorAll('.stat-num');
if (!reduceMotion && 'IntersectionObserver' in window && statNums.length) {
  var statObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        statObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });
  statNums.forEach(function (el) { statObserver.observe(el); });
}

var marqueeParallaxEls = document.querySelectorAll('.marquee-parallax');
if (!reduceMotion && marqueeParallaxEls.length) {
  var parallaxTicking = false;
  function updateMarqueeParallax() {
    var vh = window.innerHeight;
    marqueeParallaxEls.forEach(function (el) {
      var rect = el.parentElement.getBoundingClientRect();
      var center = rect.top + rect.height / 2;
      var offset = (center - vh / 2) * -0.06;
      el.style.transform = 'translateX(' + offset.toFixed(1) + 'px)';
    });
    parallaxTicking = false;
  }
  window.addEventListener('scroll', function () {
    if (!parallaxTicking) {
      parallaxTicking = true;
      requestAnimationFrame(updateMarqueeParallax);
    }
  }, { passive: true });
  updateMarqueeParallax();
}
