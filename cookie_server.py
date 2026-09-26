"""
Cookie Fetcher Service
Deploy on: Render.com / Railway.app / Fly.io (free tier works)
"""

import os
import time
import threading
from flask import Flask, jsonify

app = Flask(__name__)

TURTLEMINT_URL = (
    "https://app.turtlemintinsurance.com/car-insurance/"
    "car-profile/car-registration-info"
)

COOKIE_TTL = 120  # 2 minutes — bahut short, kyunki Turtlemint jaldi expire karta hai

_cache = {"cookies": {}, "ts": 0}
_lock = threading.Lock()


def fetch_cookies_playwright():
    """Playwright se fresh cookies nikaalo."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(TURTLEMINT_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(6000)  # JS ko settle hone do

            cookies = context.cookies()
            browser.close()

            return {c["name"]: c["value"] for c in cookies}
    except Exception as e:
        print(f"[fetch_cookies] Error: {e}")
        return {}


def get_fresh_cookies(force=False):
    with _lock:
        now = time.time()
        if force or (now - _cache["ts"]) > COOKIE_TTL or not _cache["cookies"]:
            print("[CookieServer] Fetching fresh cookies...")
            cookies = fetch_cookies_playwright()
            if cookies:
                _cache["cookies"] = cookies
                _cache["ts"] = now
                print(f"[CookieServer] Got {len(cookies)} cookies")
            else:
                print("[CookieServer] Fetch failed, keeping old")
        return dict(_cache["cookies"])


@app.route("/cookies", methods=["GET"])
def cookies_endpoint():
    force = request.args.get("force") == "1"
    c = get_fresh_cookies(force=force)
    return jsonify({
        "cookies": c,
        "count": len(c),
        "fetched_at": _cache["ts"],
        "age_seconds": int(time.time() - _cache["ts"]) if _cache["ts"] else None,
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({"service": "cookie-fetcher", "status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
