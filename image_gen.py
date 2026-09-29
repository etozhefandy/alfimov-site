"""Картинки для блога через OpenAI Images: обложка статьи и иллюстрации в текст.

Модель gpt-image-1 (как у генератора креативов в боте), при сбое — dall-e-3.
Ключ: переменная OPENAI_API_KEY или Связка ключей macOS (один раз):

    security add-generic-password -a openai -s alfimov-site-openai -w

Только stdlib: сборке сайта и админке не нужен пакет openai.
"""
import base64
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

KEYCHAIN_SERVICE = "alfimov-site-openai"
MODEL = os.environ.get("BLOG_IMAGE_MODEL", "gpt-image-1")
QUALITY = os.environ.get("BLOG_IMAGE_QUALITY", "medium")  # low | medium | high
API_URL = "https://api.openai.com/v1/images/generations"
TIMEOUT = 180

# Визуальный язык сайта (design brief): спокойно, технологично, без штампов маркетинга.
STYLE = (
    "Editorial illustration for a data-driven digital marketing agency website. "
    "Minimalist, calm, rational, premium but not luxurious. Palette: white and light grey background, "
    "near-black #0C1011 shapes, a single saturated blue accent #1769FF used sparingly. "
    "Clean geometric composition, generous empty space, soft natural light, subtle depth. "
    "No text, no letters, no numbers, no logos, no watermarks, no UI screenshots, no fake dashboards. "
    "Avoid clichés: no rockets, no targets or bullseyes, no megaphones, no mouse cursors, no handshakes, "
    "no smiling stock people, no floating gradient blobs, no glowing neon, no glassmorphism, "
    "no charts with an upward arrow."
)

SIZES = {
    # вид: (gpt-image-1, dall-e-3)
    "cover": ("1536x1024", "1792x1024"),
    "inline": ("1536x1024", "1792x1024"),
}


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


def build_prompt(kind, title="", lead="", idea=""):
    """Промпт: идея пользователя (если есть) или тема статьи + общий стиль сайта."""
    idea, title, lead = (idea or "").strip(), (title or "").strip(), (lead or "").strip()
    if idea:
        subject = f"Scene: {idea}."
    elif title:
        subject = f"A conceptual visual metaphor for an article titled «{title}»" + (f" — {lead}" if lead else "") + "."
    else:
        raise ImageError("Опишите картинку или сначала заполните заголовок статьи")
    frame = ("Wide 3:2 cover image, the main subject slightly off-centre."
             if kind == "cover" else "Wide 3:2 in-article illustration that explains the idea at a glance.")
    return f"{subject} {frame} {STYLE}"


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
        with opener(req, timeout=TIMEOUT) as r:
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


def _png_to_jpeg(png):
    """dall-e-3 отдаёт PNG на ~3 МБ — перегоняем в JPEG встроенной утилитой macOS (sips)."""
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in.png", Path(tmp) / "out.jpg"
        src.write_bytes(png)
        r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", str(src), "--out", str(dst)],
                           capture_output=True, timeout=60)
        if r.returncode == 0 and dst.is_file():
            return dst.read_bytes(), ".jpg"
    return png, ".png"


def generate(kind, title="", lead="", idea="", key=None, opener=urllib.request.urlopen):
    """→ (bytes, расширение файла). Бросает ImageError с понятным текстом."""
    if kind not in SIZES:
        raise ImageError("Неизвестный вид картинки")
    prompt = build_prompt(kind, title, lead, idea)
    key = key or api_key()
    if not key:
        raise ImageError("Нет ключа OpenAI. Сохраните его командой: "
                         f"security add-generic-password -a openai -s {KEYCHAIN_SERVICE} -w")
    size_new, size_old = SIZES[kind]
    try:
        payload = {"model": MODEL, "prompt": prompt, "size": size_new, "n": 1,
                   "output_format": "webp", "output_compression": 82}
        if QUALITY:
            payload["quality"] = QUALITY
        return _first_b64(_post(key, payload, opener)), ".webp"
    except ImageError as first:
        if "ключ" in str(first) or "средства" in str(first):
            raise  # dall-e-3 с тем же ключом не поможет
        try:
            png = _first_b64(_post(key, {"model": "dall-e-3", "prompt": prompt, "size": size_old, "n": 1,
                                         "response_format": "b64_json"}, opener))
        except ImageError:
            raise first from None
        return _png_to_jpeg(png)
