"""Картинки для блога через OpenAI Images: обложка статьи и иллюстрации в текст.

Модель gpt-image-2, при сбое — gpt-image-1.5 (gpt-image-1 и dall-e-3 OpenAI выводит из работы).
Ключ: переменная OPENAI_API_KEY или Связка ключей macOS (один раз):

    security add-generic-password -U -a openai -s alfimov-site-openai -w "$(pbpaste | tr -d '[:space:]')"

Только stdlib: сборке сайта и админке не нужен пакет openai.
"""
import base64
import json
import os
import random
import ssl
import subprocess
import urllib.error
import urllib.request

KEYCHAIN_SERVICE = "alfimov-site-openai"
MODEL = os.environ.get("BLOG_IMAGE_MODEL", "gpt-image-2")
FALLBACK_MODEL = os.environ.get("BLOG_IMAGE_FALLBACK", "gpt-image-1.5")
QUALITY = os.environ.get("BLOG_IMAGE_QUALITY", "medium")  # low | medium | high
API_URL = "https://api.openai.com/v1/images/generations"
TIMEOUT = 180

# Визуальный язык сайта (design brief): спокойно, технологично, без штампов маркетинга.
# Промпт собирается из слоёв (подход agency-os): постоянные слои держат стиль и качество,
# переменные (сюжет, приём съёмки) дают разнообразие. Цвета — ТОЛЬКО словами: hex-код в промпте
# модель норовит напечатать в кадре (в agency-os так на вывеске появилось «88E75»).
STYLE = (
    "Editorial image for a data-driven digital marketing agency website. "
    "Minimalist, calm, rational, premium but not luxurious. Palette: white, light grey and near-black, "
    "with one saturated cobalt-blue accent. "
    "SIGNATURE ELEMENT: every image contains exactly one bold cobalt-blue geometric element — a cube, "
    "slab, sphere, ribbon, panel or beam of blue light — placed with intent; everything else stays "
    "white, grey and near-black. Clean geometric composition, generous negative space, subtle depth."
)
BANS = (
    "No text, no letters, no numbers, no logos or app icons of any brands (no Instagram, Facebook, TikTok, "
    "Google marks), no watermarks, no UI screenshots, no fake dashboards or charts. "
    "Avoid clichés: no rockets, no targets or bullseyes, no megaphones, no mouse cursors, no handshakes, "
    "no floating gradient blobs, no glowing neon, no glassmorphism, no arrows pointing up. "
    "Commercial-grade finish, crisp composition, natural hands and faces, no extra limbs, no distortions."
)

# Сюжеты. people — живые, но редакционные и чуть абстрактные кадры, не сток.
PEOPLE_RULE = (
    "PEOPLE: authentic Central Asian (Kazakh) professionals and small-business owners in a modern "
    "Almaty or Astana setting, candid and mid-action, not posing, not looking at the camera, no stock smiles. "
    "Editorial, slightly abstract treatment: people partly in shadow or silhouette, cropped by geometry, "
    "scale contrast between people and space; the scene explains the idea, faces are secondary."
)
NO_PEOPLE_RULE = (
    "NO PEOPLE: no humans, faces, hands or silhouettes — abstract still life of objects, materials and "
    "architecture only."
)
PEOPLE_SCENES = [
    "a business owner and a marketer reviewing results together at a long table",
    "a café owner behind the counter checking incoming orders on a phone",
    "a small team at a whiteboard mapping the customer journey with sticky shapes",
    "a founder alone in a bright empty office thinking over the next decision",
    "two colleagues walking through a minimalist corridor mid-conversation",
    "a shop owner welcoming a customer in a clean modern boutique",
    "a person seen from behind at a large window overlooking the city",
    "a meeting seen from above, people around a table covered with printed materials",
]
# Приёмы съёмки из словаря agency-os (shared/visual_techniques), отобраны под спокойный стиль сайта.
TECHNIQUES = [
    "shot perfectly top-down, objects and people arranged on a plane",
    "low camera angle looking up, heroic monumental perspective",
    "wide shot, the subject small inside a large architectural space",
    "subject rendered as a backlit silhouette against a luminous wall",
    "hard direct light with crisp graphic shadow shapes",
    "composition built on reflections in glass and polished surfaces",
    "graphic cast shadows used as the main compositional element",
    "deliberate play of scale, an ordinary object made giant",
    "vast negative space, the subject small and isolated",
    "perfectly symmetrical centred framing, balanced geometry",
    "shallow depth of field, one subject tack-sharp, the rest melting into soft bokeh",
    "soft atmospheric haze and volumetric window light",
]
MODES = ("auto", "people", "abstract")

SIZES = {"cover": "1536x1024", "inline": "1536x1024"}


def _ssl_context():
    """Python с python.org на macOS не видит системные сертификаты — берём certifi или /etc/ssl/cert.pem."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    ctx = ssl.create_default_context()
    if not ctx.get_ca_certs() and os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


class ImageError(Exception):
    """Ошибка с текстом, который можно показать в админке."""


def api_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def build_prompt(kind, title="", lead="", idea="", mode="auto", rng=None):
    """Промпт = тема (идея пользователя или заголовок) + сюжет (люди/абстракция) + приём съёмки + стиль.

    mode: auto — люди примерно в половине картинок; people — всегда с людьми; abstract — без людей.
    """
    rng = rng or random.Random()
    idea, title, lead = (idea or "").strip(), (title or "").strip(), (lead or "").strip()
    if idea:
        topic = f"Idea to show: {idea}."
    elif title:
        topic = f"A visual metaphor for an article titled «{title}»" + (f" — {lead}" if lead else "") + "."
    else:
        raise ImageError("Опишите картинку или сначала заполните заголовок статьи")
    people = mode == "people" or (mode not in MODES[1:] and rng.random() < 0.5)
    if people:
        scene = f"Scene: {rng.choice(PEOPLE_SCENES)}, connected to the idea above. {PEOPLE_RULE}"
    else:
        scene = f"Scene: an abstract still life of objects and materials expressing the idea. {NO_PEOPLE_RULE}"
    frame = ("Wide 3:2 cover image."
             if kind == "cover" else "Wide 3:2 in-article illustration that explains the idea at a glance.")
    return f"{topic} {scene} Camera: {rng.choice(TECHNIQUES)}. {frame} {STYLE} {BANS}"


def humanize(status, message):
    txt = (message or "").lower()
    if status == 401 or "incorrect api key" in txt or "invalid_api_key" in txt:
        return "OpenAI отклонил ключ — проверьте ключ в Связке ключей (alfimov-site-openai)"
    if "insufficient_quota" in txt or "billing" in txt or "quota" in txt:
        return "На аккаунте OpenAI закончились средства или лимит"
    if status == 429:
        return "OpenAI перегружен запросами — повторите через минуту"
    if "safety" in txt or "moderation" in txt or "content_policy" in txt or "content policy" in txt:
        return "OpenAI отклонил запрос по правилам безопасности — переформулируйте идею картинки"
    if "verif" in txt and "organization" in txt:
        return "Для gpt-image-1 нужна верификация организации в OpenAI"
    return f"OpenAI вернул ошибку ({status}): {message[:200]}" if message else f"OpenAI вернул ошибку ({status})"


def _post(key, payload, opener=urllib.request.urlopen):
    req = urllib.request.Request(
        API_URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        kw = {"context": _ssl_context()} if opener is urllib.request.urlopen else {}
        with opener(req, timeout=TIMEOUT, **kw) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        try:
            msg = json.loads(ex.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            msg = ""
        raise ImageError(humanize(ex.code, msg)) from None
    except (urllib.error.URLError, TimeoutError) as ex:
        raise ImageError(f"Нет связи с OpenAI: {getattr(ex, 'reason', ex)}") from None


def _first_b64(resp):
    try:
        b64 = resp["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError):
        raise ImageError("OpenAI вернул пустой ответ") from None
    return base64.b64decode(b64)


def generate(kind, title="", lead="", idea="", key=None, opener=urllib.request.urlopen, mode="auto"):
    """→ (bytes, расширение файла). Бросает ImageError с понятным текстом."""
    if kind not in SIZES:
        raise ImageError("Неизвестный вид картинки")
    prompt = build_prompt(kind, title, lead, idea, mode)
    key = key or api_key()
    if not key:
        raise ImageError("Нет ключа OpenAI. Скопируйте ключ и выполните: "
                         f"security add-generic-password -U -a openai -s {KEYCHAIN_SERVICE} -w \"$(pbpaste)\"")
    payload = {"model": MODEL, "prompt": prompt, "size": SIZES[kind], "n": 1,
               "output_format": "webp", "output_compression": 82}
    if QUALITY:
        payload["quality"] = QUALITY
    try:
        return _first_b64(_post(key, payload, opener)), ".webp"
    except ImageError as first:
        if "ключ" in str(first) or "средства" in str(first) or not FALLBACK_MODEL:
            raise  # другая модель с тем же ключом не поможет
        try:
            return _first_b64(_post(key, {**payload, "model": FALLBACK_MODEL}, opener)), ".webp"
        except ImageError:
            raise first from None
