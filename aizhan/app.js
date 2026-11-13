var corners = {
  TR: 'M900,1750 V90 C900,20 1000,-10 1150,-40 L2250,-360',
  TL: 'M100,1750 V90 C100,20 0,-10 -150,-40 L-1250,-360',
  BR: 'M900,-1150 V510 C900,580 1000,610 1150,640 L2250,960',
  BL: 'M100,-1150 V510 C100,580 0,610 -150,640 L-1250,960'
};
var keys = Object.keys(corners);
function pick(){ return keys[Math.floor(Math.random()*keys.length)]; }
var a = pick();
var b = pick();
while (b === a) { b = pick(); }
document.getElementById('flowPathA').setAttribute('d', corners[a]);
document.getElementById('flowPathB').setAttribute('d', corners[b]);

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
