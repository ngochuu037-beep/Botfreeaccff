# ============================================================
# APP.PY — Web server wrapper cho Render
# ============================================================

import os
import threading
import logging
from flask import Flask
import bot as bot_module

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")

app = Flask(__name__)


@app.route("/")
def home():
    return "🤖 Bot alive", 200


@app.route("/health")
def health():
    # Endpoint cho UptimeRobot ping
    return "OK", 200


def start_bot():
    try:
        log.info("🚀 Starting bot...")
        bot_module.main()
    except Exception as e:
        log.exception("Bot crashed: %s", e)


def main():
    # Bot chạy trong thread riêng
    threading.Thread(target=start_bot, daemon=True).start()
    # Flask chiếm port chính
    port = int(os.environ.get("PORT", 10000))
    log.info("🌐 Flask on :%s", port)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
