#!/usr/bin/env python3
"""Локальная админка блога alfimov.kz: статьи, ИИ-генерация, расписание, публикация.

    python3 admin.py            # http://127.0.0.1:8001/admin/ (откроется в браузере)

Работает только на этом компьютере (слушает 127.0.0.1), поэтому без логина. Статьи лежат
в content/articles/*.json; «Опубликовать на сайт» коммитит их в main, пушит и запускает
./deploy-git.sh — дальше Plesk забирает ветку deploy, как и при обычном деплое.
"""
import base64
import http.server
import json
import mimetypes
import re
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import blog  # noqa: E402
import build  # noqa: E402

HOST, PORT = "127.0.0.1", 8001
ADMIN_HTML = ROOT / "admin" / "index.html"
UPLOAD_DIR = ROOT / "static" / "assets" / "blog"
UPLOAD_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD = 5 * 1024 * 1024
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
_lock = threading.Lock()  # сборка и публикация не должны идти параллельно


def article_view(a):
    return {**a, "state": blog.state(a), "path": build.article_path(a), "read_minutes": blog.read_minutes(a)}


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {out or 'код ' + str(r.returncode)}")
    return out


def publish():
    """Коммит статей → push main → ./deploy-git.sh. Возвращает лог для экрана."""
    log = []
    run(["git", "add", "--", "content/articles", "static/assets/blog"])
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0
    if staged:
        live = len(blog.live())
        run(["git", "commit", "-q", "-m", f"blog: обновление статей (на сайте: {live})",
             "--", "content/articles", "static/assets/blog"])
        log.append("Статьи закоммичены")
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "main":
        run(["git", "push", "-q", "origin", "main"])
        log.append("main отправлен на GitHub")
    else:
        log.append(f"Ветка {branch} — не main, на GitHub не отправляю (деплой всё равно из рабочей копии)")
    log.append(run(["./deploy-git.sh"]).splitlines()[-1])
    log.append("Осталось в Plesk: «Получить сейчас» → «Развернуть сейчас»")
    return log


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "alfimov-admin"

    def log_message(self, fmt, *args):
        sys.stderr.write("  " + fmt % args + "\n")

    # --- ответы
    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def error(self, code, msg):
        self.send(code, {"error": msg})

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD * 2:
            raise ValueError("Слишком большой запрос")
        return json.loads(self.rfile.read(n) or b"{}")

    # Защита от DNS-rebinding и чужих страниц: только наш хост и наш origin.
    def trusted(self):
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            return False
        origin = self.headers.get("Origin")
        return origin is None or urlparse(origin).netloc in ALLOWED_HOSTS

    def route(self, method):
        if not self.trusted():
            return self.error(403, "forbidden")
        path = unquote(urlparse(self.path).path)
        try:
            if method == "GET":
                return self.get(path)
            return self.mutate(method, path)
        except ValueError as ex:
            return self.error(400, str(ex))
        except Exception as ex:  # noqa: BLE001 — показать ошибку на экране, а не уронить сервер
            traceback.print_exc()
            return self.error(500, str(ex))

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_DELETE(self):
        self.route("DELETE")

    # --- чтение
    def get(self, path):
        if path in ("/", "/admin"):
            self.send_response(302)
            self.send_header("Location", "/admin/")
            self.end_headers()
            return
        if path == "/admin/":
            return self.send(200, ADMIN_HTML.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if path == "/admin/api/articles":
            return self.send(200, {"articles": [article_view(a) for a in blog.load_all()],
                                   "now": blog.now().isoformat(timespec="minutes"),
                                   "writer_model": __import__("seo_writer").MODEL})
        m = re.match(r"^/admin/preview/([a-z0-9-]+)/?$", path)
        if m:
            a = blog.get(m.group(1))
            if not a:
                return self.error(404, "Статья не найдена")
            posts = [p for p in blog.live() if p["slug"] != a["slug"]] + [a]
            return self.send(200, build.build_article(a, posts)[1], "text/html; charset=utf-8")
        return self.static(path)

    def static(self, path):
        """Ассеты для предпросмотра: сначала static/, затем собранный dist/."""
        rel = path.lstrip("/")
        for base in (ROOT / "static", ROOT / "dist"):
            f = (base / rel).resolve()
            if f.is_dir():
                f = f / "index.html"
            if base.resolve() in f.parents and f.is_file():
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                if ctype.startswith("text/") or ctype in ("application/javascript", "image/svg+xml"):
                    ctype += "; charset=utf-8"
                return self.send(200, f.read_bytes(), ctype)
        return self.error(404, "not found")

    # --- изменения
    def mutate(self, method, path):
        if method == "POST" and path == "/admin/api/articles":
            data = self.body()
            a = blog.save(data.get("article") or {}, old_slug=data.get("old_slug") or None)
            return self.send(200, {"article": article_view(a)})
        m = re.match(r"^/admin/api/articles/([a-z0-9-]+)$", path)
        if method == "DELETE" and m:
            if not blog.delete(m.group(1)):
                return self.error(404, "Статья не найдена")
            return self.send(200, {"ok": True})
        if method == "POST" and path == "/admin/api/generate":
            return self.generate(self.body())
        if method == "POST" and path == "/admin/api/upload":
            return self.upload(self.body())
        if method == "POST" and path == "/admin/api/build":
            with _lock:
                build.build()
            return self.send(200, {"ok": True, "live": len(blog.live())})
        if method == "POST" and path == "/admin/api/publish":
            with _lock:
                log = publish()
            return self.send(200, {"ok": True, "log": log})
        return self.error(404, "not found")

    def generate(self, data):
        import seo_writer
        keywords = [k for k in re.split(r"[\n,;]+", data.get("keywords") or "") if k.strip()]
        try:
            words = max(500, min(4000, int(data.get("words") or 1500)))
        except ValueError:
            words = 1500
        existing = [{"slug": a["slug"], "title": a["title"]} for a in blog.load_all()
                    if a["slug"] != data.get("current_slug")]
        try:
            out = seo_writer.generate(data.get("topic") or "", keywords, data.get("notes") or "", words, existing)
        except seo_writer.WriterError as ex:
            return self.error(400, str(ex))
        if not blog.SLUG_RE.match(out.get("slug") or ""):
            out["slug"] = blog.slugify(out.get("slug") or out.get("title") or "")
        return self.send(200, {"article": out})

    def upload(self, data):
        name = Path(str(data.get("filename") or "")).name
        stem, ext = Path(name).stem, Path(name).suffix.lower()
        if ext not in UPLOAD_EXT:
            raise ValueError("Обложка: jpg, png или webp")
        raw = base64.b64decode(data.get("data") or "", validate=True)
        if not raw or len(raw) > MAX_UPLOAD:
            raise ValueError("Файл пустой или больше 5 МБ")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        base = blog.slugify(stem)
        target, n = UPLOAD_DIR / f"{base}{ext}", 2
        while target.exists():
            target, n = UPLOAD_DIR / f"{base}-{n}{ext}", n + 1
        target.write_bytes(raw)
        return self.send(200, {"path": f"/assets/blog/{target.name}"})


def main():
    srv = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    link = f"http://{HOST}:{PORT}/admin/"
    print(f"Админка блога: {link}  (Ctrl+C — остановить)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(link)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
